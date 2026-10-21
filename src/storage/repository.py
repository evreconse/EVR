"""
EVRECONSE Storage - File Storage Repository.

File-based implementation of StorageRepository.
Uses atomic writes, thread-safe operations, and incremental indexing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import EventID, EventStatus, MarketEvent


class StorageRepository(ABC):
    """Abstract storage repository interface."""

    @abstractmethod
    def save_event(self, event: MarketEvent) -> None:
        """Save a market event."""
        ...

    @abstractmethod
    def load_event(self, event_id: EventID) -> MarketEvent:
        """Load a market event by ID."""
        ...

    @abstractmethod
    def update_event(self, event: MarketEvent) -> None:
        """Update an existing market event."""
        ...

    @abstractmethod
    def delete_event(self, event_id: EventID) -> bool:
        """Delete a market event."""
        ...

    @abstractmethod
    def exists(self, event_id: EventID) -> bool:
        """Check if event exists."""
        ...

    @abstractmethod
    def list_events(self, *, limit: int | None = None, offset: int = 0, order_by: str = "created_at", ascending: bool = False) -> list[MarketEvent]:
        """List events with pagination."""
        ...

    @abstractmethod
    def find_by_status(self, status: EventStatus, *, limit: int | None = None) -> list[MarketEvent]:
        """Find events by status."""
        ...

    @abstractmethod
    def find_by_symbol(self, symbol: str, *, limit: int | None = None) -> list[MarketEvent]:
        """Find events by symbol."""
        ...

    @abstractmethod
    def find_by_strategy(self, strategy_id: str, *, limit: int | None = None) -> list[MarketEvent]:
        """Find events by strategy."""
        ...

    @abstractmethod
    def find_active(self, *, limit: int | None = None) -> list[MarketEvent]:
        """Find active events."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Get total event count."""
        ...

    @abstractmethod
    def clear(self) -> int:
        """Clear all events."""
        ...

    def health_check(self) -> bool:
        """Check storage health."""
        return True

    @abstractmethod
    def close(self) -> None:
        """Close the repository."""
        ...
