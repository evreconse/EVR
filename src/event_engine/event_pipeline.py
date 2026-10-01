"""
EVRECONSE Event Engine - Event Pipeline.

Pipeline for processing events through stages.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from .context import EventContext


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Stage name."""
        ...

    @property
    @abstractmethod
    def stage_type(self) -> str:
        """Stage type identifier."""
        ...

    @abstractmethod
    async def process(self, context: EventContext) -> EventContext:
        """
        Process context through this stage.

        Args:
            context: Current event context

        Returns:
            Updated context

        Raises:
            PipelineError: If stage fails
        """
        ...


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    final_context: EventContext
    stage_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_stage: str | None = None
    duration_ms: float = 0.0


class PipelineStageBase:
    """Base class for pipeline stages."""

    def __init__(self, name: str, stage_type: str = "custom") -> None:
        self._name = name
        self._stage_type = stage_type

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        """
        Process context through this stage.

        Args:
            context: Event context

        Returns:
            Updated context
        """
        raise NotImplementedError


class PipelineStageValidator:
    """Validation stage - validates event before processing."""

    def __init__(self) -> None:
        self._name = "validator"
        self._stage_type = "validation"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        # Validation happens in context creation
        return context


class PipelineStageStrategy:
    """Strategy evaluation stage."""

    def __init__(self, strategy_engine) -> None:
        self._strategy_engine = strategy_engine
        self._name = "strategy"
        self._stage_type = "strategy"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        """Execute strategy evaluation on the event using canonical LW-001 check."""
        from models import MarketEvent
        from core import get_logger

        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Strategy stage: Processing event for {context.symbol}")

        if not self._strategy_engine:
            logger.warning(f"[PIPELINE] Strategy stage: Strategy engine not available, skipping")
            return context

        # Reconstruct MarketEvent from EventContext
        from models.enums import Exchange, Timeframe
        from models.market_event import MarketEvent as ME
        from datetime import UTC, datetime

        # Create a minimal MarketEvent for strategy evaluation
        event = ME.new(
            symbol=context.symbol,
            exchange=Exchange(context.exchange),
            timeframe=Timeframe(context.timeframe),
            event_time=context.event_time,
            open_price=context.open_price,
            high_price=context.high_price,
            low_price=context.low_price,
            close_price=context.close_price,
            volume=context.volume,
        )

        # Volume Ratio REMOVED - not part of LW-001 strategy
        # Add strategy data to the event - use canonical check for qualification
        from strategy.lw001_canonical import check_lw001_signal
        from models.market_event import StrategyData
        from dataclasses import replace

        canonical_result = check_lw001_signal(
            open_price=context.open_price,
            high_price=context.high_price,
            low_price=context.low_price,
            close_price=context.close_price,
        )

        qualified = canonical_result.qualified
        metrics = canonical_result.metrics

        strategy_data = StrategyData(
            strategy_id="LW-001",
            lower_wick=metrics.lw_body_ratio * abs(context.close_price - context.open_price) if abs(context.close_price - context.open_price) > 0 else 0.0,
            body=context.close_price - context.open_price,
            wick_body_ratio=metrics.lw_body_ratio,
            lower_wick_pct=metrics.lw_range_pct,
            body_pct=metrics.body_pct,
            confirm=True,
        )
        event = replace(event, strategy_data=strategy_data)

        logger.info(f"[PIPELINE] Strategy stage: MarketEvent reconstructed - O:{context.open_price} H:{context.high_price} L:{context.low_price} C:{context.close_price}")
        logger.info(f"[PIPELINE] Strategy stage: LW-001 check - qualified={qualified}, ratio={metrics.lw_body_ratio:.2f}x")

        # Update context with strategy results
        return context.with_updates(
            strategy_id="LW-001",
            lower_wick=strategy_data.lower_wick,
            body=strategy_data.body,
            wick_body_ratio=strategy_data.wick_body_ratio,
            status="qualified" if qualified else "rejected",
            updated_at=datetime.now(UTC),
        )


class PipelineStageScorer:
    """Scoring stage."""

    def __init__(self, scoring_engine) -> None:
        self._scoring_engine = scoring_engine
        self._name = "scorer"
        self._stage_type = "scoring"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        """Execute scoring on the event."""
        from core import get_logger

        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Scorer stage: Processing event for {context.symbol}")

        if not self._scoring_engine or not self._scoring_engine.is_initialized():
            # Scoring engine not available, skip scoring
            logger.warning(f"[PIPELINE] Scorer stage: Scoring engine not initialized, skipping")
            return context

        try:
            from scoring.context import ScoringContext, ScoringConfig
            from models import MarketEvent
            from models.enums import Exchange, Timeframe
            from models.market_event import MarketEvent as ME, StrategyData
            from datetime import UTC, datetime
            from dataclasses import replace

            # Reconstruct MarketEvent from EventContext
            event = ME.new(
                symbol=context.symbol,
                exchange=Exchange(context.exchange),
                timeframe=Timeframe(context.timeframe),
                event_time=context.event_time,
                open_price=context.open_price,
                high_price=context.high_price,
                low_price=context.low_price,
                close_price=context.close_price,
                volume=context.volume,
            )

            # Add strategy data to the MarketEvent for scoring
            # Use context data which was set by strategy stage
            has_strategy_data = (context.lower_wick is not None or 
                                 context.body is not None or 
                                 context.wick_body_ratio is not None)
            if has_strategy_data:
                strategy_data = StrategyData(
                    strategy_id=context.strategy_id or "LW-001",
                    lower_wick=context.lower_wick or 0.0,
                    body=context.body or 0.0,
                    wick_body_ratio=context.wick_body_ratio or 0.0,
                    lower_wick_pct=0.0,
                    body_pct=0.0,
                    confirm=True,
                )
                event = replace(event, strategy_data=strategy_data)
                logger.info(f"[PIPELINE] Scorer stage: Added strategy data - lower_wick={context.lower_wick}, body={context.body}, wick_body_ratio={context.wick_body_ratio}")
            else:
                logger.warning(f"[PIPELINE] Scorer stage: No strategy data in context, lower_wick={context.lower_wick}, body={context.body}")

            # Create ScoringContext
            scoring_context = ScoringContext(
                market_event=event,
                config=ScoringConfig(
                    scoring_id="lw_001_scoring",
                    version="1.0.0",
                    parameters={},
                    enabled=True,
                    min_confidence_score=80.0,
                ),
                data_provider=None,  # Not needed for basic evaluation
                storage=None,  # Not needed for basic evaluation
            )

            print(f"DEBUG-SCORER: Calling ScoringEngine.evaluate with market_event.strategy_data={scoring_context.market_event.strategy_data}")
            result = await self._scoring_engine.evaluate(scoring_context)
            print(f"DEBUG-SCORER: ScoringEngine returned: success={result.qualified}, score={result.final_score}")

            logger.info(f"[PIPELINE] Scorer stage: Result - score={result.final_score}, qualified={result.qualified}")

            # Update context with scoring results
            return context.with_scoring(
                score=result.final_score,
                breakdown={"explanation": result.explanation, "qualified": result.qualified},
            )
        except Exception as e:
            print(f"DEBUG-SCORER: Exception in Scorer stage: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"[PIPELINE] Scorer stage: Evaluation failed - {e}", exc_info=True)
            return context


class PipelineStageNotifier:
    """Notification stage."""

    def __init__(self, notification_engine) -> None:
        self._notification_engine = notification_engine
        self._name = "notifier"
        self._stage_type = "notification"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        """Send notification if event is qualified."""
        from core import get_logger
        from strategy.lw001_canonical import format_lw001_telegram_message

        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Notifier stage: Processing event for {context.symbol}, status={context.status}")

        if not self._notification_engine:
            logger.warning(f"[PIPELINE] Notifier stage: Notification engine not available")
            return context

        # Send notification if event is qualified (strategy qualified)
        if context.status == "qualified":
            logger.info(f"[PIPELINE] Notifier stage: Event qualified for notification")
            try:
                # Use canonical formatter - UTC only, plain text
                event_time_str = "N/A"
                if context.event_time:
                    event_time_str = context.event_time.strftime("%d.%m.%Y %H:%M UTC")

                body = format_lw001_telegram_message(
                    symbol=context.symbol,
                    event_time_utc=event_time_str,
                    open_price=context.open_price,
                    high_price=context.high_price,
                    low_price=context.low_price,
                    close_price=context.close_price,
                    volume=context.volume,
                    metrics=type('Metrics', (), {
                        'range_pct': (context.high_price - context.low_price) / context.open_price * 100 if context.open_price else 0,
                        'body_pct': abs(context.close_price - context.open_price) / context.open_price * 100 if context.open_price else 0,
                        'lw_body_ratio': context.wick_body_ratio or 0,
                        'lw_range_pct': (min(context.open_price, context.close_price) - context.low_price) / (context.high_price - context.low_price) * 100 if context.high_price != context.low_price else 0,
                        'open_to_low_pct': (context.low_price - context.open_price) / context.open_price * 100 if context.open_price else 0,
                        # Volume Ratio REMOVED - not part of LW-001 strategy
                        'is_red': context.close_price < context.open_price,
                    })(),
                )

                notification_id = str(datetime.now(UTC).timestamp())
                channel = "telegram"
                recipient = channel
                format = "plain"
                priority = 0

                # Deduplication check - don't send duplicate signals
                if self._storage and hasattr(self._storage, 'exists_by_symbol_timestamp'):
                    # Get candle timestamp from context
                    timestamp_ms = int(context.event_time.timestamp() * 1000) if context.event_time else 0
                    if timestamp_ms > 0 and self._storage.exists_by_symbol_timestamp(context.symbol, timestamp_ms):
                        logger.info(f"[PIPELINE] Notifier stage: Duplicate signal for {context.symbol} at {timestamp_ms}, skipping")
                        return context
                
                logger.info(f"[PIPELINE] Notifier stage: Sending notification to Telegram")
                await self._notification_engine.send(
                    channel=channel,
                    recipient=recipient,
                    subject="LW-001 Signal",
                    body=body,
                    format=format,
                    priority=priority,
                )
                logger.info(f"[PIPELINE] Notifier stage: Notification sent successfully")
            except Exception as e:
                logger.error(f"[PIPELINE] Notifier stage: Notification failed - {e}", exc_info=True)
        else:
            logger.info(f"[PIPELINE] Notifier stage: Event not qualified for notification (status={context.status})")

        return context


class PipelineStageOutcomeTracker:
    """Outcome tracking stage."""

    def __init__(self, outcome_tracker) -> None:
        self._outcome_tracker = outcome_tracker
        self._name = "outcome_tracker"
        self._stage_type = "outcome_tracking"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        if context.market_event and context.market_event.status in ["monitoring", "completed", "expired"]:
            # Track outcome
            pass
        return context


class PipelineStageStorage:
    """Persistence stage."""

    def __init__(self, storage_service) -> None:
        self._storage = storage_service
        self._name = "storage"
        self._stage_type = "persistence"

    @property
    def stage_name(self) -> str:
        return self._name

    @property
    def stage_type(self) -> str:
        return self._stage_type

    async def process(self, context: EventContext) -> EventContext:
        """Persist event to storage."""
        from core import get_logger

        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Storage stage: Processing event for {context.symbol}")

        if not self._storage:
            logger.warning(f"[PIPELINE] Storage stage: Storage service not available")
            return context
        try:
            from models import MarketEvent
            from models.enums import Exchange, Timeframe
            from models.market_event import MarketEvent as ME
            from datetime import UTC, datetime

            # Reconstruct MarketEvent from EventContext
            event = ME.new(
                symbol=context.symbol,
                exchange=Exchange(context.exchange),
                timeframe=Timeframe(context.timeframe),
                event_time=context.event_time,
                open_price=context.open_price,
                high_price=context.high_price,
                low_price=context.low_price,
                close_price=context.close_price,
                volume=context.volume,
            )

            logger.info(f"[PIPELINE] Storage stage: MarketEvent reconstructed for storage")

            # Add strategy data if available
            if context.strategy_id:
                from models.market_event import MarketEvent as ME
                event = ME.qualified(
                    event,
                    strategy_id=context.strategy_id,
                    lower_wick=context.lower_wick or 0.0,
                    body=context.body or 0.0,
                    wick_body_ratio=context.wick_body_ratio or 0.0,
                    lower_wick_pct=0.0,
                    body_pct=0.0,
                    confirm=True,
                )

            # Store the event
            await self._storage.store(event)
            logger.info(f"[PIPELINE] Storage stage: Event stored successfully")
        except Exception as e:
            import traceback
            logger.error(f"[PIPELINE] Storage stage: Storage failed - {e}")
            traceback.print_exc()

        return context


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Pipeline configuration."""
    stages: tuple[str, ...] = (
        "validator",
        "strategy",
        "scorer",
        "notifier",
        "outcome_tracker",
        "storage",
    )
    continue_on_error: bool = False
    timeout_seconds: float = 30.0


class EventPipeline:
    """
    Event processing pipeline.

    Executes stages sequentially, passing context through each.
    """

    def __init__(
        self,
        stages: list,
        config: PipelineConfig | None = None,
    ) -> None:
        self._stages = stages
        self._config = config or PipelineConfig()
        self._stages_dict = {s.stage_name: s for s in stages}

    async def execute(self, context: EventContext) -> PipelineResult:
        """
        Execute pipeline on context.

        Args:
            context: Initial event context

        Returns:
            PipelineResult with final context and results
        """
        start_time = time.monotonic()
        current_context = context
        stage_results = {}
        error = None
        error_stage = None

        for stage in self._stages:
            stage_start = time.monotonic()
            try:
                current_context = await stage.process(current_context)
                stage_duration = (time.monotonic() - stage_start) * 1000
                stage_results[stage.stage_name] = {
                    "success": True,
                    "duration_ms": stage_duration,
                }
            except Exception as e:
                stage_duration = (time.monotonic() - stage_start) * 1000
                error = str(e)
                error_stage = stage.stage_name
                stage_results[stage.stage_name] = {
                    "success": False,
                    "duration_ms": stage_duration,
                    "error": str(e),
                }

                if not self._config.continue_on_error:
                    break

        total_duration_ms = (time.monotonic() - start_time) * 1000

        return PipelineResult(
            success=error is None,
            final_context=current_context,
            stage_results=stage_results,
            error=error,
            error_stage=error_stage,
            duration_ms=total_duration_ms,
        )

    def get_stage(self, name: str) -> Any | None:
        """Get stage by name."""
        return self._stages_dict.get(name)

    def add_stage(self, stage: Any) -> None:
        """Add stage to pipeline."""
        self._stages.append(stage)
        self._stages_dict[stage.stage_name] = stage

    def remove_stage(self, name: str) -> bool:
        """Remove stage by name."""
        for i, s in enumerate(self._stages):
            if s.stage_name == name:
                self._stages.pop(i)
                self._stages_dict.pop(name, None)
                return True
        return False


def create_default_pipeline(
    strategy_engine=None,
    scoring_engine=None,
    notification_engine=None,
    outcome_tracker=None,
    storage_service=None,
) -> EventPipeline:
    """Create default event pipeline."""
    stages = [
        PipelineStageValidator(),
        PipelineStageStrategy(strategy_engine),
        PipelineStageScorer(scoring_engine),
        PipelineStageNotifier(notification_engine),
        PipelineStageOutcomeTracker(outcome_tracker),
        PipelineStageStorage(storage_service),
    ]

    return EventPipeline(stages=stages)

# Simple Notification class for compatibility
class Notification:
    """Simple notification class for compatibility with the pipeline."""

    def __init__(self, notification_id=None, channel=None, priority=None,
                 title=None, message=None, metadata=None, format="markdown"):
        self.notification_id = notification_id
        self.channel = channel
        self.priority = priority
        self.title = title
        self.message = message
        self.metadata = metadata or {}
        self.format = format

        # Map Notification to the expected interface
        self.subject = title
        self.body = message or ""
        self.recipient = channel

    @property
    def channel_name(self):
        return self.channel