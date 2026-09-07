"""
EVRECONSE Event Engine - Context and Result Models.

Context and result objects for event processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from models import MarketEvent


@dataclass(frozen=False, slots=False)
class EventContext:
    """
    Immutable context passed through event processing pipeline.
    
    Contains all data needed for event processing without
    exposing internal system components.
    """
    event_id: UUID
    event_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Market data
    symbol: str
    exchange: str
    timeframe: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    event_time: datetime
    
    # Strategy data (if qualified)
    strategy_id: str | None = None
    lower_wick: float | None = None
    body: float | None = None
    wick_body_ratio: float | None = None
    liquidation_volume: float | None = None
    liquidation_reference: float | None = None
    
    # Scoring data
    confidence_score: float | None = None
    score_breakdown: dict | None = None
    
    # Metadata
    schema_version: str = "1.0"
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
    
    @property
    def market_event(self) -> MarketEvent | None:
        """Property for pipeline compatibility - returns None as EventContext is a lightweight alternative."""
        return None
    
    @property
    def final_score(self) -> float | None:
        """Alias for confidence_score for pipeline compatibility."""
        return self.confidence_score
    
    @property
    def qualified(self) -> bool:
        """Check if event is qualified (status >= QUALIFIED)."""
        return self.status in {"qualified", "scored", "signal", "monitoring", "completed", "expired"}
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timeframe": self.timeframe,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "close_price": self.close_price,
            "volume": self.volume,
            "event_time": self.event_time.isoformat(),
            "strategy_id": self.strategy_id,
            "lower_wick": self.lower_wick,
            "body": self.body,
            "wick_body_ratio": self.wick_body_ratio,
            "liquidation_volume": self.liquidation_volume,
            "liquidation_reference": self.liquidation_reference,
            "confidence_score": self.confidence_score,
            "score_breakdown": self.score_breakdown,
            "schema_version": self.schema_version,
            "metadata": self.metadata,
}
    
    def with_updates(self, **updates) -> EventContext:
        """Create new instance with updated fields."""
        # Use dataclasses.asdict to handle slots properly
        from dataclasses import asdict
        data = asdict(self)
        data.update(updates)
        return self.__class__(**data)
    
    def with_status(self, status: str, updated_at: datetime | None = None) -> EventContext:
        """Create new instance with updated status."""
        return self.with_updates(
            status=status,
            updated_at=updated_at or datetime.now(UTC),
        )
    
    def with_scoring(self, score: float, breakdown: dict) -> EventContext:
        """Add scoring results."""
        return self.with_updates(
            confidence_score=score,
            score_breakdown=breakdown,
            updated_at=datetime.now(UTC),
        )


# Protocols for external dependencies (avoid circular imports)
from dataclasses import dataclass, field
from typing import Protocol


class DataProviderProtocol(Protocol):
    """Protocol for data provider access."""
    
    async def get_snapshot(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        ...
    
    async def get_liquidations(self, symbol: str, limit: int) -> list[dict]:
        ...


class StorageProtocol(Protocol):
    """Protocol for storage access."""
    
    async def save_event(self, event: Any) -> None:
        ...
    
    async def get_events(self, symbol: str, start: datetime, end: datetime) -> list:
        ...
