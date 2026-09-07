"""
EVRECONSE Storage - Storage Engine.

High-level storage operations working exclusively through StorageRepository.
No knowledge of filesystem, serialization formats, or concrete implementations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from models import EventID, EventStatus, MarketEvent
from models.enums import EventStatus
from .repository import StorageRepository


class StorageEngine:
    """
    High-level storage engine working through StorageRepository interface.
    
    Provides higher-level operations without knowing about:
    - File system
    - Serialization formats
    - Concrete implementations
    
    Only knows the StorageRepository interface.
    """
    
    def __init__(self, repository: StorageRepository) -> None:
        """
        Initialize storage engine.
        
        Args:
            repository: Storage repository implementation
        """
        self._repository = repository
        self._started = False
    
    async def startup(self) -> None:
        """Startup storage engine."""
        self._started = True
    
    async def shutdown(self) -> None:
        """Shutdown storage engine."""
        self._started = False
    
    @property
    def repository(self) -> StorageRepository:
        """Access underlying repository."""
        return self._repository
    
    # =========================================================================
    # Event Lifecycle Operations
    # =========================================================================
    
    def save_event(self, event: MarketEvent) -> None:
        """
        Save market event.
        
        Args:
            event: MarketEvent to save
            
        Raises:
            StorageWriteError: If write fails
            StorageSerializationError: If serialization fails
        """
        self._repository.save_event(event)
    
    async def store(self, event: MarketEvent) -> None:
        """Alias for save_event for compatibility."""
        self.save_event(event)
    
    def load_event(self, event_id: EventID) -> MarketEvent:
        """
        Load market event by ID.
        
        Args:
            event_id: Event identifier
            
        Returns:
            MarketEvent
            
        Raises:
            StorageNotFoundError: If event not found
            StorageReadError: If read fails
            StorageCorruptedError: If data is corrupted
        """
        return self._repository.load_event(event_id)
    
    def update_event(self, event: MarketEvent) -> None:
        """
        Update existing market event.
        
        Args:
            event: MarketEvent to update
            
        Raises:
            StorageNotFoundError: If event doesn't exist
            StorageWriteError: If write fails
        """
        self._repository.update_event(event)
    
    def delete_event(self, event_id: EventID) -> bool:
        """
        Delete a market event.
        
        Args:
            event_id: Event identifier
            
        Returns:
            True if deleted, False if not found
        """
        return self._repository.delete_event(event_id)
    
    def exists(self, event_id: EventID) -> bool:
        """Check if event exists."""
        return self._repository.exists(event_id)

    def exists_by_symbol_timestamp(self, symbol: str, timestamp_ms: int) -> bool:
        """
        Check if an event exists for the given symbol and candle timestamp.
        
        This is used for deduplication - ensures we don't process/send
        the same signal twice.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USDT")
            timestamp_ms: Candle close timestamp in milliseconds
            
        Returns:
            True if an event with this symbol and timestamp exists, False otherwise.
        """
        # Check if the repository has this method (FileStorageRepository does)
        if hasattr(self._repository, 'exists_by_symbol_timestamp'):
            return self._repository.exists_by_symbol_timestamp(symbol, timestamp_ms)
        return False
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def list_events(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str = "created_at",
        ascending: bool = False,
    ) -> list[MarketEvent]:
        """List events with pagination."""
        return self._repository.list_events(
            limit=limit,
            offset=offset,
            order_by=order_by,
            ascending=ascending,
        )
    
    def find_by_status(
        self,
        status: EventStatus,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by status."""
        return self._repository.find_by_status(status, limit=limit)
    
    def find_by_symbol(
        self,
        symbol: str,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by trading symbol."""
        return self._repository.find_by_symbol(symbol, limit=limit)
    
    def find_by_strategy(
        self,
        strategy_id: str,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by strategy ID."""
        return self._repository.find_by_strategy(strategy_id, limit=limit)
    
    def find_active(self, *, limit: int | None = None) -> list[MarketEvent]:
        """Find active (non-terminal) events."""
        return self._repository.find_active(limit=limit)
    
    def count(self) -> int:
        """Get total number of events."""
        return self._repository.count()
    
    def clear(self) -> int:
        """Remove all events."""
        return self._repository.clear()
    
    # =========================================================================
    # Health & Maintenance
    # =========================================================================
    
    def health_check(self) -> bool:
        """Check storage health."""
        return self._repository.health_check()
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        return {
            "total_events": self.count(),
            "active_events": len(self._repository.find_active()),
            "by_status": {
                status.value: len(self._repository.find_by_status(status))
                for status in EventStatus
            },
        }
    
    def cleanup_expired(self, max_age_hours: int = 168) -> int:
        """
        Remove expired events older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of deleted events
        """
        # This would require additional query capabilities
        # For now, return 0 - implement when needed
        return 0
