"""
EVRECONSE Event Engine - Event Factory.

Factory for creating MarketEvent instances.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from models import MarketEvent
from .exceptions import EventCreationError


@dataclass(frozen=True, slots=True)
class EventCreationRequest:
    """Request to create a new MarketEvent."""
    symbol: str
    exchange: str
    timeframe: str
    event_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    event_type: str = "market"
    
    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")


class EventFactory:
    """
    Factory for creating MarketEvent instances.
    
    Single point of event creation. Uses Model Factory Methods.
    """
    
    def __init__(self) -> None:
        self._lock = None  # placeholder for thread lock if needed
    
    def create_market_event(self, request: EventCreationRequest) -> MarketEvent:
        """
        Create a new MarketEvent from creation request.
        
        Args:
            request: Event creation parameters
            
        Returns:
            New MarketEvent instance
            
        Raises:
            EventCreationError: If creation fails
        """
        try:
            event = MarketEvent.new(
                symbol=request.symbol,
                exchange=request.exchange,
                timeframe=request.timeframe,
                event_time=request.event_time,
                open_price=request.open_price,
                high_price=request.high_price,
                low_price=request.low_price,
                close_price=request.close_price,
                volume=request.volume,
            )
            return event
        except Exception as e:
            raise EventCreationError(f"Failed to create market event: {e}") from e
    
    def create_qualified_event(
        self,
        market_event: MarketEvent,
        strategy_id: str,
        lower_wick: float,
        body: float,
        wick_body_ratio: float,
        lower_wick_pct: float,
        body_pct: float,
        liquidation_volume: float,
        liquidation_reference: float,
    ) -> MarketEvent:
        """Create qualified event from market event."""
        # This would create a qualified event with strategy data
        # Implementation depends on MarketEvent structure
    
    def create_scored_event(
        self,
        qualified_event: MarketEvent,
        confidence_score: float,
        score_breakdown: dict,
    ) -> MarketEvent:
        """Create scored event from qualified event."""
    
    def create_signaled_event(
        self,
        scored_event: MarketEvent,
    ) -> MarketEvent:
        """Create signaled event from scored event."""


# Alias for compatibility
EventFactory = EventFactory
