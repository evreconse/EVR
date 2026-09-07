"""
EVRECONSE Event Engine - Event Registry.

Thread-safe registry for active events.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .exceptions import (
    EventAlreadyExistsError,
    EventNotFoundError,
)


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Immutable event record for registry."""
    event_id: str
    event_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    symbol: str
    exchange: str
    timeframe: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    event_time: datetime
    strategy_id: str | None = None
    lower_wick: float | None = None
    body: float | None = None
    wick_body_ratio: float | None = None
    liquidation_volume: float | None = None
    liquidation_reference: float | None = None
    confidence_score: float | None = None
    score_breakdown: dict | None = None
    schema_version: str = "1.0"
    metadata: dict = None
    
    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})


class EventRegistry:
    """
    Thread-safe registry for active events.
    
    Provides O(1) access, registration, and querying of active events.
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: dict[str, EventRecord] = {}
        self._by_symbol: dict[str, set[str]] = {}
        self._by_status: dict[str, set[str]] = {}
        self._by_exchange: dict[str, set[str]] = {}
    
    def register(self, event_id: str, event_data: dict[str, Any]) -> None:
        """
        Register a new event.
        
        Args:
            event_id: Unique event identifier
            event_data: Event data dictionary
            
        Raises:
            EventAlreadyExistsError: If event ID already exists
        """
        with self._lock:
            if event_id in self._events:
                raise EventAlreadyExistsError(event_id)
            
            now = datetime.now(UTC)
            record = EventRecord(
                event_id=event_id,
                event_type="market",
                status="new",
                created_at=now,
                updated_at=now,
                symbol=event_data.get("symbol", ""),
                exchange=event_data.get("exchange", ""),
                timeframe=event_data.get("timeframe", ""),
                open_price=event_data.get("open_price", 0.0),
                high_price=event_data.get("high_price", 0.0),
                low_price=event_data.get("low_price", 0.0),
                close_price=event_data.get("close_price", 0.0),
                volume=event_data.get("volume", 0.0),
                event_time=event_data.get("event_time", now),
                strategy_id=event_data.get("strategy_id"),
                lower_wick=None,
                body=None,
                wick_body_ratio=None,
                liquidation_volume=None,
                liquidation_reference=None,
                confidence_score=None,
                score_breakdown=None,
                schema_version="1.0",
                metadata={},
            )
            
            self._events[event_id] = record
            
            # Update indexes
            self._add_to_index(event_id, "symbol", record.symbol)
            self._add_to_index(event_id, "status", "new")
            self._add_to_index(event_id, "exchange", record.exchange)
    
    def update(self, event_id: str, updates: dict) -> None:
        """Update event fields."""
        with self._lock:
            if event_id not in self._events:
                raise KeyError(f"Event {event_id} not found")
            
            record = self._events[event_id]
            old_status = record.status
            old_symbol = record.symbol
            old_exchange = record.exchange
            
            # Create new record with updates (immutable)
            new_data = record.__dict__.copy()
            new_data.update(updates)
            new_data["updated_at"] = datetime.now(UTC)
            new_record = EventRecord(**new_data)
            
            self._events[event_id] = new_record
            
            # Update indexes if status or symbol changed
            new_status = new_record.status
            new_symbol = new_record.symbol
            new_exchange = new_record.exchange
            
            if new_status != old_status:
                self._remove_from_index(event_id, "status", old_status)
                self._add_to_index(event_id, "status", new_status)
            
            if new_symbol != old_symbol:
                self._remove_from_index(event_id, "symbol", old_symbol)
                self._add_to_index(event_id, "symbol", new_symbol)
            
            if new_exchange != old_exchange:
                self._remove_from_index(event_id, "exchange", old_exchange)
                self._add_to_index(event_id, "exchange", new_exchange)
    
    def _add_to_index(self, event_id: str, index_name: str, key: str) -> None:
        """Add record to index."""
        index_map = getattr(self, f"_by_{index_name}")
        index_map.setdefault(key, set()).add(event_id)
    
    def _remove_from_index(self, event_id: str, index_name: str, key: str) -> None:
        """Remove record from index."""
        index_map = getattr(self, f"_by_{index_name}")
        if index_map and key in index_map:
            index_map[key].discard(event_id)
            if not index_map[key]:
                del index_map[key]
    
    def get(self, event_id: str) -> EventRecord:
        """Get event by ID."""
        with self._lock:
            if event_id not in self._events:
                raise EventNotFoundError(event_id)
            return self._events[event_id]
    
    def remove(self, event_id: str) -> None:
        """Remove event from registry."""
        with self._lock:
            if event_id not in self._events:
                raise EventNotFoundError(event_id)
            
            record = self._events[event_id]
            
            # Remove from all indexes
            self._remove_from_index(event_id, "status", record.status)
            self._remove_from_index(event_id, "symbol", record.symbol)
            self._remove_from_index(event_id, "exchange", record.exchange)
            
            del self._events[event_id]
    
    def exists(self, event_id: str) -> bool:
        """Check if event exists."""
        with self._lock:
            return event_id in self._events
    
    def get_by_status(self, status: str) -> list[str]:
        """Get event IDs by status."""
        with self._lock:
            return list(self._by_status.get(status, set()))
    
    def get_by_symbol(self, symbol: str) -> list[str]:
        """Get event IDs by symbol."""
        with self._lock:
            return list(self._by_symbol.get(symbol, set()))
    
    def get_by_exchange(self, exchange: str) -> list[str]:
        """Get event IDs by exchange."""
        with self._lock:
            return list(self._by_exchange.get(exchange, set()))
    
    def get_all(self, status: str | None = None) -> list[EventRecord]:
        """Get all events, optionally filtered by status."""
        with self._lock:
            if status:
                return [self._events[eid] for eid in self._by_status.get(status, set())]
            return list(self._events.values())
    
    def count(self, status: str | None = None) -> int:
        """Get event count."""
        with self._lock:
            if status:
                return len(self._by_status.get(status, set()))
            return len(self._events)
    
    def clear(self) -> None:
        """Clear all events (for testing)."""
        with self._lock:
            self._events.clear()
            self._by_symbol.clear()
            self._by_status.clear()
            self._by_exchange.clear()
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            stats = {
                "total_events": len(self._events),
                "by_status": {k: len(v) for k, v in self._by_status.items()},
                "by_exchange": {k: len(v) for k, v in self._by_exchange.items()},
                "unique_symbols": len(self._by_symbol),
            }
            return stats