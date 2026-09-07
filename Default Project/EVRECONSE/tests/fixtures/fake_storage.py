"""
Fake Storage for testing.

Provides an in-memory storage implementation that does not touch the filesystem.
"""

from __future__ import annotations

from typing import Any

from models import MarketEvent
from storage import StorageRepository


class FakeStorageRepository(StorageRepository):
    """In-memory fake storage repository for testing."""

    def __init__(self) -> None:
        self._events: dict[str, MarketEvent] = {}
        self._save_count = 0
        self._load_count = 0
        self._update_count = 0
        self._delete_count = 0

    def save_event(self, event: MarketEvent) -> None:
        event_id = str(event.event_id)
        if event_id in self._events:
            from storage.exceptions import EventAlreadyExistsError
            raise EventAlreadyExistsError(event_id)
        self._events[event_id] = event
        self._save_count += 1

    def load_event(self, event_id: Any) -> MarketEvent:
        self._load_count += 1
        eid = str(event_id)
        if eid not in self._events:
            from storage.exceptions import EventNotFoundError
            raise EventNotFoundError(eid)
        return self._events[eid]

    def update_event(self, event: MarketEvent) -> None:
        event_id = str(event.event_id)
        if event_id not in self._events:
            from storage.exceptions import EventNotFoundError
            raise EventNotFoundError(event_id)
        self._events[event_id] = event
        self._update_count += 1

    def delete_event(self, event_id: Any) -> bool:
        eid = str(event_id)
        if eid in self._events:
            del self._events[eid]
            self._delete_count += 1
            return True
        return False

    def exists(self, event_id: Any) -> bool:
        return str(event_id) in self._events

    def list_events(self, *, limit: int | None = None, offset: int = 0, order_by: str = "created_at", ascending: bool = False) -> list[MarketEvent]:
        events = list(self._events.values())
        if limit is not None:
            events = events[offset:offset + limit]
        return events

    def find_by_status(self, status: Any, *, limit: int | None = None) -> list[MarketEvent]:
        result = [e for e in self._events.values() if e.metadata.status == status]
        if limit is not None:
            result = result[:limit]
        return result

    def find_by_symbol(self, symbol: str, *, limit: int | None = None) -> list[MarketEvent]:
        result = [e for e in self._events.values() if e.market_data and e.market_data.symbol == symbol]
        if limit is not None:
            result = result[:limit]
        return result

    def find_by_strategy(self, strategy_id: str, *, limit: int | None = None) -> list[MarketEvent]:
        result = [e for e in self._events.values() if e.strategy_data and e.strategy_data.strategy_id == strategy_id]
        if limit is not None:
            result = result[:limit]
        return result

    def find_active(self, *, limit: int | None = None) -> list[MarketEvent]:
        from models.enums import EventStatus
        active_statuses = {EventStatus.NEW, EventStatus.QUALIFIED, EventStatus.SCORED, EventStatus.SIGNAL, EventStatus.MONITORING}
        result = [e for e in self._events.values() if e.metadata.status in active_statuses]
        if limit is not None:
            result = result[:limit]
        return result

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> int:
        count = len(self._events)
        self._events.clear()
        return count

    def health_check(self) -> bool:
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "save_count": self._save_count,
            "load_count": self._load_count,
            "update_count": self._update_count,
            "delete_count": self._delete_count,
        }

    def close(self) -> None:
        self._events.clear()


class FakeStorageEngine:
    """Fake storage engine for testing."""

    def __init__(self) -> None:
        self._repository = FakeStorageRepository()
        self.repository = self._repository

    def save_event(self, event: MarketEvent) -> None:
        self._repository.save_event(event)

    def load_event(self, event_id: Any) -> MarketEvent:
        return self._repository.load_event(event_id)

    def update_event(self, event: MarketEvent) -> None:
        self._repository.update_event(event)

    def delete_event(self, event_id: Any) -> bool:
        return self._repository.delete_event(event_id)

    def exists(self, event_id: Any) -> bool:
        return self._repository.exists(event_id)

    def list_events(self, **kwargs: Any) -> list[MarketEvent]:
        return self._repository.list_events(**kwargs)

    def find_by_status(self, status: Any, **kwargs: Any) -> list[MarketEvent]:
        return self._repository.find_by_status(status, **kwargs)

    def find_by_symbol(self, symbol: str, **kwargs: Any) -> list[MarketEvent]:
        return self._repository.find_by_symbol(symbol, **kwargs)

    def find_by_strategy(self, strategy_id: str, **kwargs: Any) -> list[MarketEvent]:
        return self._repository.find_by_strategy(strategy_id, **kwargs)

    def find_active(self, **kwargs: Any) -> list[MarketEvent]:
        return self._repository.find_active(**kwargs)

    def count(self) -> int:
        return self._repository.count()

    def clear(self) -> int:
        return self._repository.clear()

    def health_check(self) -> bool:
        return self._repository.health_check()

    def get_stats(self) -> dict[str, Any]:
        return self._repository.get_stats()


def create_fake_storage() -> FakeStorageEngine:
    """Factory function to create a fake storage engine."""
    return FakeStorageEngine()


def create_fake_repository() -> FakeStorageRepository:
    """Factory function to create a fake storage repository."""
    return FakeStorageRepository()