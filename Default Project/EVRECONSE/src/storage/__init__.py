"""
EVRECONSE Storage Module.

File-based event storage with atomic writes, indexing, and thread safety.
"""

from .exceptions import (
    EventAlreadyExistsError,
    EventNotFoundError,
    IndexCorruptedError,
    RepositoryError,
    StorageCorruptedError,
    StorageError,
    StorageReadError,
    StorageSerializationError,
    StorageWriteError,
)
from .file_repository import FileStorageRepository
from .repository import StorageRepository
from .serializers import (
    deserialize_event,
    deserialize_from_storage,
    event_id_to_filename,
    filename_to_event_id,
    serialize_event,
    serialize_for_storage,
)
from .storage_engine import StorageEngine

__all__ = [
    # Interface
    "StorageRepository",
    "FileStorageRepository",
    # Engine
    "StorageEngine",
    # Exceptions
    "StorageError",
    "StorageReadError",
    "StorageWriteError",
    "StorageSerializationError",
    "StorageCorruptedError",
    "RepositoryError",
    "EventNotFoundError",
    "EventAlreadyExistsError",
    "IndexCorruptedError",
    # Serializers
    "serialize_event",
    "deserialize_event",
    "event_id_to_filename",
    "filename_to_event_id",
    "serialize_for_storage",
    "deserialize_from_storage",
]