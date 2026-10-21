"""
EVRECONSE Event Engine - Main Orchestrator.

Central coordination engine for event processing pipeline.
Coordinates components but does NOT contain business logic.

Architecture:
- EventEngine: Public facade, coordinates components
- LifecycleManager: Internal component for init/start/stop
- Components: Factory, Registry, Scheduler, Dispatcher, Pipeline, Metrics
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from typing import Any

from models import MarketEvent

from .context import EventContext
from .engine_config import EngineStatsAccumulator
from .enums import EventStatus
from .event_dispatcher import EventDispatcher
from .event_factory import EventFactory
from .event_pipeline import (
    EventPipeline,
    PipelineResult,
    PipelineStageNotifier,
    PipelineStageScorer,
    PipelineStageStorage,
    PipelineStageStrategy,
)
from .event_registry import EventRegistry
from .event_scheduler import EventScheduler
from .exceptions import (
    EventEngineShutdownError,
    EventValidationError,
)
from .lifecycle import EngineConfig, EngineStats, LifecycleManager
from .metrics import MetricsCollector


class EventEngine:
    """
    Event Engine - Central orchestration engine for event processing.

    This is the PUBLIC API. It coordinates internal components but
    does NOT contain business logic.

    Responsibilities:
    - Initialize and manage component lifecycle
    - Process market events through pipeline
    - Provide statistics and monitoring
    - Handle configuration

    Internal components (NOT exposed publicly):
    - LifecycleManager: init/start/stop orchestration
    - EventFactory: Event creation
    - EventRegistry: State management
    - EventScheduler: Time-based operations
    - EventDispatcher: Internal event routing
    - EventPipeline: Processing pipeline
    - MetricsCollector: Observability
    """

    def __init__(self, config: dict | None = None) -> None:
        """Create Event Engine with optional configuration."""
        self._config = EngineConfig(**(config or {}))
        self._lifecycle = LifecycleManager(self._config)
        self._lock = threading.RLock()

        # Public stats (thread-safe)
        self._stats: EngineStatsAccumulator = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "rejected": 0,
            "processing_times": [],
        }

    # =========================================================================
    # Lifecycle Management (Idempotent)
    # =========================================================================

    def initialize(self, config: dict | None = None) -> None:
        """
        Initialize the event engine with all components.

        Idempotent - safe to call multiple times.

        Args:
            config: Optional configuration override

        Raises:
            EventEngineError: If initialization fails
        """
        self._lifecycle.initialize(config)

    def start(
        self,
        strategy_engine=None,
        scoring_engine=None,
        notification_engine=None,
        outcome_tracker=None,
        storage_service=None,
    ) -> None:
        """
        Start the event engine.

        Idempotent - safe to call multiple times.
        Starts scheduler, dispatcher, and pipeline.

        Args:
            strategy_engine: Strategy engine for signal generation
            scoring_engine: Scoring engine for confidence scoring
            notification_engine: Notification engine for alerts
            outcome_tracker: Outcome tracker for signal tracking
            storage_service: Storage service for persistence

        Raises:
            EventEngineError: If not initialized or start fails
        """
        # Store engines on the instance for pipeline stages to access
        self._strategy_engine = strategy_engine
        self._scoring_engine = scoring_engine
        self._notification_engine = notification_engine
        self._outcome_tracker = outcome_tracker
        self._storage_service = storage_service

        # Create pipeline stages with dependencies
        pipeline = self._lifecycle.pipeline
        from event_engine.event_pipeline import create_default_pipeline
        default_pipeline = create_default_pipeline(
            strategy_engine=strategy_engine,
            scoring_engine=scoring_engine,
            notification_engine=notification_engine,
            outcome_tracker=outcome_tracker,
            storage_service=storage_service,
        )
        # Replace pipeline stages with default ones that have dependencies
        pipeline._stages = default_pipeline._stages
        pipeline._stages_dict = default_pipeline._stages_dict

        # Ensure engines are injected into pipeline stages (defense in depth)
        for stage in pipeline._stages:
            if isinstance(stage, PipelineStageStrategy):
                stage._strategy_engine = strategy_engine
            elif isinstance(stage, PipelineStageScorer):
                stage._scoring_engine = scoring_engine
            elif isinstance(stage, PipelineStageNotifier):
                stage._notification_engine = notification_engine
            elif isinstance(stage, PipelineStageStorage):
                stage._storage = storage_service

        self._lifecycle.start()

    async def stop(self) -> None:
        """
        Stop the event engine gracefully.

        Idempotent - safe to call multiple times.
        Waits for active tasks, stops scheduler and dispatcher.

        Raises:
            EventEngineError: If stop fails
        """
        await self._lifecycle.stop()

    async def shutdown(self) -> None:
        """
        Full shutdown - alias for stop().

        Idempotent - safe to call multiple times.
        """
        await self.stop()

    async def reload(self, config: dict | None = None) -> None:
        """
        Reload configuration and restart components.

        Idempotent - safe to call multiple times.

        Args:
            config: New configuration (optional)
        """
        await self.stop()
        if config:
            self._config = EngineConfig(**config)
            self._lifecycle = LifecycleManager(self._config)
        self.initialize(config)
        self.start()

    # =========================================================================
    # Public Properties (Read-only)
    # =========================================================================

    @property
    def is_initialized(self) -> bool:
        """Check if engine is initialized."""
        return self._lifecycle.is_initialized

    @property
    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._lifecycle.is_running

    @property
    def config(self) -> EngineConfig:
        """Get engine configuration."""
        return self._config

    # =========================================================================
    # Event Processing (Main Public API)
    # =========================================================================

    def process_market_data(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        event_time: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> dict:
        """
        Process market data through the complete pipeline.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            exchange: Exchange name (e.g., bybit)
            timeframe: Candle timeframe (e.g., 15m)
            event_time: Event timestamp (UTC, timezone-aware)
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Trading volume

        Returns:
            Processing result dictionary

        Raises:
            EventValidationError: If input validation fails
            EventProcessingError: If processing fails
            EventEngineNotInitializedError: If engine not initialized
            EventEngineShutdownError: If engine is shutting down
        """
        if not self.is_running:
            raise EventEngineShutdownError("Event Engine is not running")

        # Create market event using factory
        request = self._create_creation_request(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            event_time=event_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

        event = self._lifecycle.factory.create_market_event(request)

        # Process through pipeline
        return self.process_event(event)

    def process_event(self, event: MarketEvent) -> dict:
        """
        Process a single market event through the complete pipeline.

        Args:
            event: MarketEvent to process

        Returns:
            Processing result dictionary

        Raises:
            EventNotFoundError: If event not found in registry
            EventProcessingError: If processing fails
            EventEngineNotInitializedError: If engine not initialized
        """
        start_time = time.monotonic()

        # Create processing context
        context = self._create_context(event)

        # Execute pipeline - check if we're already in an event loop
        try:
            asyncio.get_running_loop()
            # We're in an event loop, run the coroutine in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._execute_pipeline(context))
                result = future.result()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run
            result = asyncio.run(self._execute_pipeline(context))


        # Update stats
        duration_ms = (time.monotonic() - start_time) * 1000
        self._update_stats(result.success, duration_ms)

        return {
            "success": result.success,
            "event_id": str(event.event_id),
            "final_status": result.final_context.status,
            "duration_ms": duration_ms,
            "score": result.final_context.confidence_score,
            "qualified": result.final_context.qualified,
            "error": result.error,
        }

    async def _execute_pipeline(self, context: EventContext) -> PipelineResult:
        """Execute pipeline asynchronously."""
        return await self._lifecycle.pipeline.execute(context)

    def _create_creation_request(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        event_time: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> Any:
        """Create event creation request."""
        from .event_factory import EventCreationRequest
        return EventCreationRequest(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            event_time=event_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

    def _create_context(self, event: MarketEvent) -> EventContext:
        """Create processing context from market event."""
        market_data = event.market_data
        if market_data is None:
            raise EventValidationError("Market event has no market data")
        strategy_data = event.strategy_data
        return EventContext(
            event_id=event.metadata.event_id.value,
            event_type="market",
            status=event.metadata.status.value,
            created_at=event.metadata.created_at,
            updated_at=event.metadata.updated_at,
            symbol=market_data.symbol,
            exchange=market_data.exchange.value,
            timeframe=market_data.timeframe.value,
            event_time=market_data.event_time,
            open_price=market_data.open,
            high_price=market_data.high,
            low_price=market_data.low,
            close_price=market_data.close,
            volume=market_data.volume,
            strategy_id=event.strategy_data.strategy_id if strategy_data else None,
            lower_wick=strategy_data.lower_wick if strategy_data else None,
            body=strategy_data.body if strategy_data else None,
            wick_body_ratio=strategy_data.wick_body_ratio if strategy_data else None,
        )

    def _update_stats(self, success: bool, duration_ms: float) -> None:
        """Update processing statistics (thread-safe)."""
        with self._lock:
            self._stats["processed"] += 1
            if success:
                self._stats["succeeded"] += 1
            else:
                self._stats["failed"] += 1

            # Keep rolling window of processing times
            self._stats["processing_times"].append(duration_ms)
            if len(self._stats["processing_times"]) > 1000:
                self._stats["processing_times"] = self._stats["processing_times"][-1000:]

    # =========================================================================
    # Statistics and Monitoring
    # =========================================================================

    def get_stats(self) -> EngineStats:
        """
        Get engine statistics.

        Returns:
            EngineStats snapshot
        """
        with self._lock:
            times = self._stats["processing_times"]
            avg_time = sum(times) / len(times) if times else 0.0

            # Get active/queued from registry
            active = len(self._lifecycle.registry.get_by_status(EventStatus.NEW.value))
            queued = self._lifecycle.scheduler.get_stats().get("pending_tasks", 0)

            return EngineStats(
                processed=self._stats["processed"],
                succeeded=self._stats["succeeded"],
                failed=self._stats["failed"],
                rejected=self._stats["rejected"],
                active_events=active,
                queued_events=queued,
                avg_processing_time_ms=avg_time,
            )

    def get_metrics(self) -> dict:
        """
        Get detailed metrics.

        Returns:
            Metrics dictionary
        """
        if not self._config.enable_metrics:
            return {"metrics_enabled": False}

        metrics = self._lifecycle.metrics.get_all_metrics()
        return {
            "metrics_enabled": True,
            "counters": metrics.get("counters", {}),
            "gauges": metrics.get("gauges", {}),
            "histograms": metrics.get("histograms", {}),
        }

    # =========================================================================
    # Component Access (for advanced use cases)
    # =========================================================================

    @property
    def factory(self) -> EventFactory:
        """Get event factory."""
        return self._lifecycle.factory

    @property
    def registry(self) -> EventRegistry:
        """Get event registry."""
        return self._lifecycle.registry

    @property
    def scheduler(self) -> EventScheduler:
        """Get event scheduler."""
        return self._lifecycle.scheduler

    @property
    def dispatcher(self) -> EventDispatcher:
        """Get event dispatcher."""
        return self._lifecycle.dispatcher

    @property
    def pipeline(self) -> EventPipeline:
        """Get event pipeline."""
        return self._lifecycle.pipeline

    @property
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        return self._lifecycle.metrics


# =============================================================================
# Singleton Access (for backward compatibility)
# =============================================================================

_engine_instance: EventEngine | None = None
_engine_lock = threading.Lock()


def get_event_engine(config: dict | None = None) -> EventEngine:
    """Get global EventEngine singleton."""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = EventEngine(config)
        return _engine_instance


def reset_event_engine() -> None:
    """Reset global event engine (for testing)."""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None:
            # Can't await here - for testing only
            _engine_instance = None


# =============================================================================
# Public Exports
# =============================================================================

__all__ = [
    "EngineConfig",
    "EngineStats",
    "EventEngine",
    "get_event_engine",
    "reset_event_engine",
]
