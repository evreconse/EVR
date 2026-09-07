“‹"""
EVRECONSE Storage - File Storage Repository.

File-based implementation of StorageRepository using JSON files.
Each MarketEvent stored as separate JSON file named by EventID.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from models import EventID, EventStatus, MarketEvent
from models.enums import EventStatus
from .exceptions import (
    RepositoryError,
    StorageCorruptedError,
    StorageNotFoundError,
    StorageReadError,
    StorageWriteError,
)
from .repository import StorageRepository
from .serializers import (
    deserialize_from_storage,
    event_id_to_filename,
    filename_to_event_id,
    serialize_for_storage,
)


class _EventIndex:
    """
    In-memory index for fast event lookups.
    
    Built once at startup, updated incrementally.
    """
    
    def __init__(self) -> None:
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_status: dict[str, set[str]] = {}
        self._by_symbol: dict[str, set[str]] = {}
        self._by_strategy: dict[str, set[str]] = {}
        self._active: set[str] = set()
        self._lock = threading.RLock()
        self._loaded = False
    
    def _extract_status(self, data: dict) -> str | None:
        return data.get("metadata", {}).get("status")
    
    def _extract_symbol(self, data: dict) -> str | None:
        return data.get("market_data", {}).get("symbol")
    
    def _extract_strategy(self, data: dict) -> str | None:
        return data.get("strategy_data", {}).get("strategy_id")
    
    def _is_active(self, status: str | None) -> bool:
        if status is None:
            return False
        terminal = {"DISMISSED", "COMPLETED", "EXPIRED"}
        return status not in terminal
    
    def add(self, event_id: str, data: dict) -> None:
        with self._lock:
            self._by_id[event_id] = {
                "status": self._extract_status(data),
                "symbol": self._extract_symbol(data),
                "strategy_id": self._extract_strategy(data),
            }
            status = self._extract_status(data)
            symbol = self._extract_symbol(data)
            strategy = self._extract_strategy(data)
            
            if status:
                self._by_status.setdefault(status, set()).add(event_id)
            if symbol:
                self._by_symbol.setdefault(symbol, set()).add(event_id)
            if strategy:
                self._by_strategy.setdefault(strategy, set()).add(event_id)
            
            if self._is_active(data.get("metadata", {}).get("status")):
                self._active.add(event_id)
    
    def remove(self, event_id: str) -> None:
        with self._lock:
            info = self._by_id.pop(event_id, None)
            if info:
                status = info.get("status")
                symbol = info.get("symbol")
                strategy = info.get("strategy_id")
                
                if status:
                    self._by_status.get(status, set()).discard(event_id)
                if symbol:
                    self._by_symbol.get(symbol, set()).discard(event_id)
                if strategy:
                    self._by_strategy.get(strategy, set()).discard(event_id)
                self._active.discard(event_id)
    
    def update_status(self, event_id: str, old_status: str, new_status: str) -> None:
        with self._lock:
            if old_status:
                self._by_status.get(old_status, set()).discard(event_id)
            self._by_status.setdefault(new_status, set()).add(event_id)
            
            if self._is_active(old_status):
                self._active.discard(event_id)
            if self._is_active(new_status):
                self._active.add(event_id)
    
    def get_by_status(self, status: str) -> set[str]:
        with self._lock:
            return self._by_status.get(status, set()).copy()
    
    def get_by_symbol(self, symbol: str) -> set[str]:
        with self._lock:
            return self._by_symbol.get(symbol, set()).copy()
    
    def get_by_strategy(self, strategy_id: str) -> set[str]:
        with self._lock:
            return self._by_strategy.get(strategy_id, set()).copy()
    
    def get_active(self) -> set[str]:
        with self._lock:
            return self._active.copy()
    
    def get_all_ids(self) -> list[str]:
        with self._lock:
            return list(self._by_id.keys())
    
    def exists(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._by_id
    
    def count(self) -> int:
        with self._lock:
            return len(self._by_id)
    
    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_status.clear()
            self._by_symbol.clear()
            self._by_strategy.clear()
            self._active.clear()


class FileStorageRepository(StorageRepository):
    """
    File-based storage repository for MarketEvents.
    
    Each event stored as separate JSON file named by EventID.
    Thread-safe with RLock.
    Atomic writes via temp file + rename.
    In-memory index for fast queries.
    """
    
    def __init__(
        self,
        storage_dir: str | Path,
        serializer_name: str = "json",
        *,
        create_dir: bool = True,
    ) -> None:
        """
        Initialize file storage repository.
        
        Args:
            storage_dir: Directory to store event files
            serializer_name: Serializer name ('json', 'pickle', 'msgpack', 'msgspec')
            create_dir: Create directory if not exists
        """
        self._storage_dir = Path(storage_dir).resolve()
        self._lock = threading.RLock()
        self._index = _EventIndex()
        self._initialized = False
        
        if create_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        if not self._storage_dir.is_dir():
            raise RepositoryError(f"Storage path is not a directory: {self._storage_dir}")
    
    def _ensure_initialized(self) -> None:
        """Build index on first use (lazy initialization)."""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._build_index()
            self._initialized = True
    
    def _build_index(self) -> None:
        """Scan directory and build in-memory index."""
        if not self._storage_dir.exists():
            return
        
        for file_path in self._storage_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".json":
                event_id = file_path.stem
                try:
                    with file_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._index.add(event_id, data)
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Corrupted file - log and skip
                    continue
    
    def _event_file_path(self, event_id: str) -> Path:
        """Get file path for event ID with path safety validation."""
        # Validate EventID format (UUID)
        try:
            UUID(event_id)
        except ValueError:
            raise RepositoryError(f"Invalid EventID format: {event_id}")
        
        # Path traversal protection - only UUID filename allowed
        if ".." in event_id or "/" in event_id or "\\" in event_id:
            raise RepositoryError(f"Invalid EventID format: {event_id}")
        
        return self._storage_dir / f"{event_id}.json"
    
    def _atomic_write(self, file_path: Path, data: dict) -> None:
        """
        Atomic write via temp file + rename.
        """
        temp_path = file_path.with_suffix(".tmp")
        try:
            # Serialize using MarketEvent.to_dict() via JSON
            content = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            # Write to temp file
            with temp_path.open("w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # Atomic rename
            temp_path.replace(file_path)
        except Exception as e:
            # Cleanup temp file on error
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise StorageWriteError(f"Failed to write event: {e}", cause=e)
    
    def _read_event(self, event_id: str) -> dict:
        """Read and parse event JSON file."""
        file_path = self._event_file_path(event_id)
        
        if not file_path.exists():
            raise StorageNotFoundError(f"Event not found: {event_id}", event_id=event_id)
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise StorageCorruptedError(
                f"Corrupted JSON in event {event_id}: {e}",
                event_id=event_id,
                cause=e,
            )
        except OSError as e:
            raise StorageReadError(
                f"Failed to read event {event_id}: {e}",
                event_id=event_id,
                cause=e,
            )
    
    # =========================================================================
    # StorageRepository Implementation
    # =========================================================================
    
    def save_event(self, event: MarketEvent) -> None:
        """Save a market event."""
        self._ensure_initialized()
        
        with self._lock:
            event_id = str(event.event_id)
            file_path = self._event_file_path(event.event_id)
            
            # Use MarketEvent.to_dict() for serialization
            data = event.to_dict()
            
            # Write atomically
            self._atomic_write(file_path, data)
            
            # Update index
            self._index.add(event.event_id, event.to_dict())
    
    def load_event(self, event_id: EventID) -> MarketEvent:
        """Load a market event by ID."""
        self._ensure_initialized()
        
        from models import MarketEvent
        
        with self._lock:
            event_id_str = str(event_id)
            
            if not self._index.exists(event_id_str):
                raise StorageNotFoundError(f"Event not found: {event_id}", event_id=str(event_id))
            
            data = self._read_event(event_id_str)
            event = MarketEvent.from_dict(data)
            return event
    
    def update_event(self, event: MarketEvent) -> None:
        """Update an existing market event."""
        self._ensure_initialized()
        
        with self._lock:
            event_id_str = str(event.event_id)
            
            if not self._index.exists(event_id_str):
                raise StorageNotFoundError(f"Event not found: {event_id}", event_id=str(event_id))
            
            old_status = str(self._index._by_id[event_id_str]["status"])
            new_status = str(event.metadata.status)
            
            # Atomic write
            file_path = self._event_file_path(event.event_id)
            data = event.to_dict()
            self._atomic_write(file_path, data)
            
            # Update index
            self._index.update_status(event_id_str, old_status, new_status)
            self._index.add(event_id_str, data)
    
    def delete_event(self, event_id: EventID) -> bool:
        """Delete a market event."""
        self._ensure_initialized()
        
        with self._lock:
            event_id_str = str(event_id)
            
            if not self._index.exists(event_id_str):
                return False
            
            file_path = self._event_file_path(event_id)
            
            try:
                file_path.unlink()
            except OSError as e:
                raise StorageWriteError(f"Failed to delete event {event_id}: {e}", cause=e)
            
            self._index.remove(event_id_str)
            return True
    
    def exists(self, event_id: EventID) -> bool:
        """Check if event exists."""
        self._ensure_initialized()
        
        with self._lock:
            return self._index.exists(str(event_id))
    
    def list_events(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str = "created_at",
        ascending: bool = False,
    ) -> list[MarketEvent]:
        """List events with pagination."""
        self._ensure_initialized()
        
        
        with self._lock:
            all_ids = self._index.get_all_ids()
            
            # Load all events for sorting
            events = []
            for event_id in all_ids:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                except Exception:
                    continue
            
            # Sort
            reverse = not ascending
            if order_by == "created_at":
                events.sort(key=lambda e: e.metadata.created_at, reverse=reverse)
            elif order_by == "updated_at":
                events.sort(key=lambda e: e.metadata.updated_at, reverse=reverse)
            elif order_by == "symbol":
                events.sort(key=lambda e: e.market_data.symbol if e.market_data else "", reverse=reverse)
            elif order_by == "status":
                events.sort(key=lambda e: e.metadata.status.value, reverse=reverse)
            
            # Pagination
            if offset:
                events = events[offset:]
            if limit:
                events = events[:limit]
            
            return events
    
    def find_by_status(
        self,
        status: EventStatus,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by status."""
        self._ensure_initialized()
        
        
        with self._lock:
            ids = self._index.get_by_status(status.value)
            events = []
            for event_id in ids:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                    if limit and len(events) >= limit:
                        break
                except Exception:
                    continue
            return events
    
    def find_by_symbol(
        self,
        symbol: str,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by trading symbol."""
        self._ensure_initialized()
        
        
        with self._lock:
            ids = self._index.get_by_symbol(symbol)
            events = []
            for event_id in ids:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                    if limit and len(events) >= limit:
                        break
                except Exception:
                    continue
            return events
    
    def find_by_strategy(
        self,
        strategy_id: str,
        *,
        limit: int | None = None,
    ) -> list[MarketEvent]:
        """Find events by strategy ID."""
        self._ensure_initialized()
        
        
        with self._lock:
            ids = self._index.get_by_strategy(strategy_id)
            events = []
            for event_id in ids:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                    if limit and len(events) >= limit:
                        break
                except Exception:
                    continue
            return events
    
    def find_active(self, *, limit: int | None = None) -> list[MarketEvent]:
        """Find active (non-terminal) events."""
        self._ensure_initialized()
        
        
        with self._lock:
            ids = self._index.get_active()
            events = []
            for event_id in ids:
                try:
                    event = self.load_event(EventID.from_string(event_id))
                    events.append(event)
                    if limit and len(events) >= limit:
                        break
                except Exception:
                    continue
            return events
    
    def count(self) -> int:
        """Get total number of events."""
        self._ensure_initialized()
        
        with self._lock:
            return self._index.count()
    
    def clear(self) -> int:
        """Remove all events."""
        self._ensure_initialized()
        
        with self._lock:
            count = self._index.count()
            
            for file_path in self._storage_dir.iterdir():
                if file_path.is_file() and file_path.suffix == ".json":
                    try:
                        file_path.unlink()
                    except OSError:
                        pass
            
            self._index.clear()
            return count
    
    def health_check(self) -> bool:
        """Check storage health."""
        try:
            self._ensure_initialized()
            with self._lock:
                # Try to write and read a test event
                test_id = "health-check-test"
                test_path = self._storage_dir / f"{test_id}.json"
                test_path.write_text("{}")
                test_path.unlink()
            return True
        except Exception:
            return False
§ *cascade08§ÑÑä *cascade08äííõ *cascade08õ÷*cascade08÷ø *cascade08øŠŠ‹ *cascade08‹•*cascade08•– *cascade08–Ê*cascade08ÊÌ *cascade08ÌÍ*cascade08ÍÎ *cascade08ÎÔ*cascade08Ô“‹ *cascade082Zfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/storage/file_repository.py