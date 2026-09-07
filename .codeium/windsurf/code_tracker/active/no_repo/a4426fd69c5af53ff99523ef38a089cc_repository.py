¼š"""
EVRECONSE Storage - File Storage Repository.

File-based implementation of StorageRepository.
Uses atomic writes, thread-safe operations, and incremental indexing.
"""

from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from models import EventID, EventStatus, MarketEvent
from .exceptions import (
    EventAlreadyExistsError,
    EventNotFoundError,
    StorageCorruptedError,
    StorageReadError,
    StorageSerializationError,
    StorageWriteError,
)
from .serializers import (
    deserialize_from_storage,
    event_id_to_filename,
    filename_to_event_id,
    serialize_for_storage,
)


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

    def clear(self) -> int:
        """Clear all events."""
        ...

    def health_check(self) -> bool:
        """Check storage health."""
        return True

    def close(self) -> None:
        """Close the repository."""
        ...


class FileStorageRepository(StorageRepository):
    """
    File-based implementation of StorageRepository.

    Features:
    - Atomic writes using temp file + rename
    - Thread-safe operations with RLock
    - Incremental index for fast queries
    - Path safety (no path traversal)
    - Fail-fast validation on all operations
    """

    def __init__(self, storage_dir: str | Path) -> None:
        """
        Initialize the file storage repository.

        Args:
            storage_dir: Directory to store event JSON files.

        Raises:
            StorageWriteError: If the directory cannot be created.
            IndexCorruptedError: If the existing index is corrupted.
        """
        self._storage_dir = Path(storage_dir).resolve()
        self._lock = threading.RLock()
        self._index: dict[str, dict[str, Any]] = {}
        self._initialized = False

        # Ensure storage directory exists
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageWriteError(f"Failed to create storage directory: {e}") from e

        # Build or rebuild index
        self._build_index()
        self._initialized = True

    def _build_index(self) -> None:
        """
        Build the in-memory index from existing files.

        Scans the storage directory and builds an in-memory index
        for fast querying. Called once at initialization.
        """
        self._index = {}
        for file_path in self._storage_dir.glob("*.json"):
            try:
                event_id = filename_to_event_id(file_path.name)
                # Read only metadata for index
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                self._index[str(meta.get("event_id", ""))] = {
                    "file_path": file_path,
                    "status": meta.get("status"),
                    "symbol": data.get("market_data", {}).get("symbol"),
                    "strategy_id": data.get("strategy_data", {}).get("strategy_id"),
                    "created_at": meta.get("created_at"),
                }
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                # Corrupted file - log and skip, but don't fail initialization
                # In production, this should be logged
                continue

    def _rebuild_index(self) -> None:
        """Rebuild the index from scratch."""
        with self._lock:
            self._build_index()

    def _get_file_path(self, event_id: EventID) -> Path:
        """
        Get the file path for an event ID.

        Args:
            event_id: The event identifier.

        Returns:
            Full path to the event file.

        Raises:
            ValueError: If the event_id is invalid or path traversal is attempted.
        """
        filename = event_id_to_filename(event_id)
        # Path safety: ensure no path traversal
        file_path = (self._storage_dir / filename).resolve()
        if not str(file_path).startswith(str(self._storage_dir)):
            raise ValueError(f"Path traversal attempt detected: {event_id}")
        return file_path

    def _write_atomic(self, file_path: Path, data: bytes) -> None:
        """
        Write data atomically using temp file + rename.

        Args:
            file_path: Target file path.
            data: Data to write.

        Raises:
            StorageWriteError: If the write operation fails.
        """
        temp_path = file_path.with_suffix(".tmp")
        try:
            # Write to temp file
            with open(temp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            # Atomic rename
            os.replace(temp_path, file_path)
        except OSError as e:
            # Clean up temp file on failure
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
            raise StorageWriteError(f"Failed to write event: {e}") from e

    def _read_file(self, file_path: Path) -> bytes:
        """
        Read a file safely.

        Args:
            file_path: Path to the file.

        Returns:
            File contents as bytes.

        Raises:
            StorageReadError: If the read operation fails.
        """
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise StorageReadError(f"Failed to read event file: {e}") from e

    def _update_index(self, event: MarketEvent) -> None:
        """
        Update the in-memory index with event data.

        Args:
            event: The market event to index.
        """
        event_id = str(event.event_id)
        self._index[event_id] = {
            "file_path": self._get_file_path(event.event_id),
            "status": event.metadata.status.value,
            "symbol": event.market_data.symbol if event.market_data else None,
            "strategy_id": event.strategy_data.strategy_id,
            "created_at": event.metadata.created_at.isoformat(),
        }

    def _remove_from_index(self, event_id: EventID) -> None:
        """
        Remove an event from the index.

        Args:
            event_id: The event identifier to remove.
        """
        self._index.pop(str(event_id), None)

    # =========================================================================
    # StorageRepository Implementation
    # =========================================================================

    def save_event(self, event: MarketEvent) -> None:
        """
        Save a market event to storage.

        Uses atomic write (temp file + rename).
        Updates index on success.

        Raises:
            EventAlreadyExistsError: If an event with the same ID already exists.
            StorageWriteError: If the write operation fails.
            StorageSerializationError: If the event cannot be serialized.
        """
        with self._lock:
            event_id = event.event_id
            file_path = self._get_file_path(event_id)

            if file_path.exists():
                raise EventAlreadyExistsError(str(event_id))

            try:
                data = serialize_for_storage(event)
            except Exception as e:
                raise StorageSerializationError(f"Failed to serialize event: {e}") from e

            try:
                self._write_atomic(file_path, data)
            except StorageWriteError:
                raise
            except Exception as e:
                raise StorageWriteError(f"Failed to write event: {e}") from e

            # Update index on success
            self._update_index(event)

    def load_event(self, event_id: EventID) -> MarketEvent:
        """
        Load a market event from storage.

        Args:
            event_id: The unique identifier of the event.

        Returns:
            The deserialized market event.

        Raises:
            EventNotFoundError: If no event with the given ID exists.
            StorageReadError: If the read operation fails.
            StorageSerializationError: If the event cannot be deserialized.
            StorageCorruptedError: If the stored data is corrupted.
        """
        with self._lock:
            file_path = self._get_file_path(event_id)

            if not file_path.exists():
                raise EventNotFoundError(str(event_id))

            try:
                data = self._read_file(file_path)
            except StorageReadError:
                raise

            try:
                event = deserialize_from_storage(data)
            except Exception as e:
                raise StorageSerializationError(f"Failed to deserialize event: {e}") from e

            # Validate event ID matches
            if event.event_id != event_id:
                raise StorageCorruptedError(
                    f"Event ID mismatch: expected {event_id}, got {event.event_id}"
                )

            return event

    def update_event(self, event: MarketEvent) -> None:
        """
        Update an existing market event in storage.

        Args:
            event: The updated market event (must exist in storage).

        Raises:
            EventNotFoundError: If no event with the given ID exists.
            StorageWriteError: If the write operation fails.
            StorageSerializationError: If the event cannot be serialized.
        """
        with self._lock:
            event_id = event.event_id
            file_path = self._get_file_path(event_id)

            if not file_path.exists():
                raise EventNotFoundError(str(event_id))

            try:
                data = serialize_for_storage(event)
            except Exception as e:
                raise StorageSerializationError(f"Failed to serialize event: {e}") from e

            try:
                self._write_atomic(file_path, data)
            except StorageWriteError:
                raise
            except Exception as e:
                raise StorageWriteError(f"Failed to write event: {e}") from e

            # Update index on success
            self._update_index(event)

    def delete_event(self, event_id: EventID) -> None:
        """
        Delete a market event from storage.

        Args:
            event_id: The unique identifier of the event to delete.

        Raises:
            EventNotFoundError: If no event with the given ID exists.
            StorageWriteError: If the delete operation fails.
        """
        with self._lock:
            file_path = self._get_file_path(event_id)

            if not file_path.exists():
                raise EventNotFoundError(str(event_id))

            try:
                file_path.unlink()
            except OSError as e:
                raise StorageWriteError(f"Failed to delete event: {e}") from e

            # Remove from index
            self._remove_from_index(event_id)

    def exists(self, event_id: EventID) -> bool:
        """
        Check if an event exists in storage.

        Args:
            event_id: The unique identifier of the event.

        Returns:
            True if the event exists, False otherwise.
        """
        with self._lock:
            file_path = self._get_file_path(event_id)
            return file_path.exists()

    def list_events(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketEvent]:
        """
        List events with optional pagination.

        Args:
            limit: Maximum number of events to return.
            offset: Number of events to skip.

        Returns:
            List of market events (newest first by created_at).
        """
        with self._lock:
            # Sort by created_at descending (newest first)
            sorted_items = sorted(
                self._index.items(),
                key=lambda x: x[1].get("created_at", ""),
                reverse=True,
            )

            start = offset
            end = offset + limit if limit is not None else None
            selected = sorted_items[start:end]

            events = []
            for event_id, _ in selected:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                except (EventNotFoundError, StorageSerializationError):
                    # Skip corrupted entries
                    continue

            return events

    def find_by_status(self, status: EventStatus) -> list[MarketEvent]:
        """
        Find all events with the given status.

        Args:
            status: The event status to filter by.

        Returns:
            List of matching market events.
        """
        with self._lock:
            matching_ids = [
                event_id
                for event_id, info in self._index.items()
                if info.get("status") == status.value
            ]

            events = []
            for event_id_str in matching_ids:
                try:
                    event = self.load_event(EventID.from_string(event_id_str))
                    events.append(event)
                except (EventNotFoundError, StorageSerializationError):
                    continue

            return events

    def find_by_symbol(self, symbol: str) -> list[MarketEvent]:
        """
        Find all events for the given symbol.

        Args:
            symbol: The trading symbol to filter by.

        Returns:
            List of matching market events.
        """
        with self._lock:
            matching_ids = [
                event_id
                for event_id, info in self._index.items()
                if info.get("symbol") == symbol
            ]

            events = []
            for event_id_str in matching_ids:
                try:
                    event = self.load_event(EventID.from_string(event_id_str))
                    events.append(event)
                except (EventNotFoundError, StorageSerializationError):
                    continue

            return events

    def find_by_strategy(self, strategy_id: str) -> list[MarketEvent]:
        """
        Find all events for the given strategy.

        Args:
            strategy_id: The strategy identifier to filter by.

        Returns:
            List of matching market events.
        """
        with self._lock:
            matching_ids = [
                event_id
                for event_id, info in self._index.items()
                if info.get("strategy_id") == strategy_id
            ]

            events = []
            for event_id_str in matching_ids:
                try:
                    event = self.load_event(EventID.from_string(event_id_str))
                    events.append(event)
                except (EventNotFoundError, StorageSerializationError):
                    continue

            return events

    def find_active(self) -> list[MarketEvent]:
        """
        Find all events that are still active (not terminal).

        Returns:
            List of active market events.
        """
        from models.enums import EventStatus
        active_statuses = {
            EventStatus.NEW,
            EventStatus.QUALIFIED,
            EventStatus.SCORED,
            EventStatus.SIGNAL,
            EventStatus.MONITORING,
        }

        with self._lock:
            matching_ids = [
                event_id
                for event_id, info in self._index.items()
                if info.get("status") in active_statuses
            ]

            events = []
            for event_id_str in matching_ids:
                try:
                    event = self.load_event(EventID.from_string(event_id_str))
                    events.append(event)
                except (EventNotFoundError, StorageSerializationError):
                    continue

            return events

    def count(self) -> int:
        """
        Get the total number of events in storage.

        Returns:
            Total count of stored events.
        """
        with self._lock:
            return len(self._index)

    def clear(self) -> int:
        """
        Remove all events from storage.

        Returns:
            Number of events that were deleted.

        Warning:
            This operation is irreversible.
        """
        with self._lock:
            count = 0
            for file_path in self._storage_dir.glob("*.json"):
                try:
                    file_path.unlink()
                    count += 1
                except OSError:
                    continue
            self._index.clear()
            return count

    def close(self) -> None:
        """Close the repository and release resources."""
        with self._lock:
            self._index.clear()
            self._initialized = False

    def __enter__(self) -> FileStorageRepository:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # =========================================================================
    # Internal helpers for testing/debugging
    # =========================================================================

    def _get_index_size(self) -> int:
        """Get the current index size (for testing)."""
        with self._lock:
            return len(self._index)

    def _verify_integrity(self) -> tuple[int, int]:
        """
        Verify storage integrity.

        Returns:
            Tuple of (total_files, valid_files).
        """
        with self._lock:
            total = 0
            valid = 0
            for file_path in self._storage_dir.glob("*.json"):
                total += 1
                try:
                    self.load_event(filename_to_event_id(file_path.name))
                    valid += 1
                except Exception:
                    pass
            return total, valid
¼š*cascade082Ufile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/storage/repository.py