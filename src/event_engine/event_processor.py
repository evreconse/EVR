"""
EVRECONSE Event Engine - Event Processor.

Processes individual events through the pipeline.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .context import EventContext, PipelineResult
from .enums import EventStatus
from .event_factory import EventFactory
from .event_pipeline import EventPipeline
from .event_registry import EventRegistry


@dataclass(frozen=True, slots=True)
class ProcessorConfig:
    """Configuration for EventProcessor."""
    
    max_concurrent_events: int = 10
    execution_timeout: float = 30.0  # seconds
    enable_metrics: bool = True


class EventProcessor:
    """
    Processes individual events through the complete pipeline.
    
    Coordinates:
    - EventFactory for event creation
    - EventPipeline for processing
    - EventRegistry for state management
    - EventScheduler for time-based operations
    - EventDispatcher for internal events
    """
    
    def __init__(
        self,
        config: dict | None = None,
        pipeline: Any | None = None,
        registry: Any | None = None,
        scheduler: Any | None = None,
        dispatcher: Any | None = None,
        factory: Any | None = None,
        config_obj: Any | None = None,
    ) -> None:
        
        self._config = config or {}
        self._pipeline = pipeline or EventPipeline()
        self._registry = registry or EventRegistry()
        self._scheduler = scheduler
        self._dispatcher = dispatcher
        self._factory = factory or EventFactory()
        self._config = config_obj or {}
        
        self._lock = asyncio.Lock()
        self._running = False
        self._active_events: set = set()
        self._stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "rejected": 0,
        }
    
    async def process_market_data(
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
        """
        Process market data through the complete pipeline.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Candle timeframe
            event_time: Event timestamp (UTC)
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Trading volume
            
        Returns:
            PipelineResult with processing outcome
        """
        # Create market event
        event = self._factory.create_market_event(
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
        
        # Process through pipeline
        return await self.process_event(event)
    
    async def process_event(self, event: MarketEvent) -> PipelineResult:
        """
        Process a single market event through the complete pipeline.
        
        Args:
            event: MarketEvent to process
            
        Returns:
            PipelineResult with processing outcome
        """
        # Create context from event
        context = self._create_context(event)
        
        # Run through pipeline
        return await self._pipeline.execute(context)
    
    async def process_context(self, context: EventContext) -> PipelineResult:
        """Process an existing context through the pipeline."""
        # Validate
        if not context.market_event:
            raise ValueError("Context missing market event")
        
        # Check for duplicates
        event_id = str(context.event_id)
        if self._registry.exists(event_id):
            raise Exception(f"Duplicate event: {event_id}")
        
        # Execute pipeline
        return await self._pipeline.execute(context)
    
    async def _create_context(self, event) -> EventContext:
        """Create EventContext from MarketEvent."""
        from datetime import datetime

        from .context import EventContext
        
        # Extract market data
        market_data = event.market_data
        
        return EventContext(
            event_id=event.event_id,
            event_type="market",
            status=EventStatus.NEW.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            symbol=market_data.symbol,
            exchange=market_data.exchange,
            timeframe=market_data.timeframe,
            open_price=market_data.open,
            high_price=market_data.high,
            low_price=market_data.low,
            close_price=market_data.close,
            volume=market_data.volume,
            event_time=market_data.event_time,
        )
    
    async def start(self) -> None:
        """Start the event processor."""
    
    async def shutdown(self) -> None:
        """Graceful shutdown."""
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        return {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
        }