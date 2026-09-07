"""
EVRECONSE Storage - Exceptions.

Storage-specific exceptions for validation, serialization, and I/O errors.
"""

from __future__ import annotations


class StorageError(Exception):
    """Base exception for storage errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StorageReadError(StorageError):
    """Raised when reading from storage fails."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.path = path
        super().__init__(message)


class StorageWriteError(StorageError):
    """Raised when writing to storage fails."""

    def __init__(self, message: str, path: str | None = None, cause: Exception | None = None) -> None:
        self.path = path
        self.cause = cause
        super().__init__(message)


class StorageSerializationError(StorageError):
    """Raised when serialization/deserialization fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class StorageCorruptedError(StorageError):
    """Raised when storage data is corrupted or inconsistent."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.path = path
        super().__init__(message)


class RepositoryError(StorageError):
    """Raised when repository operation fails."""

    def __init__(self, message: str, operation: str | None = None) -> None:
        self.operation = operation
        super().__init__(message)


class EventNotFoundError(RepositoryError):
    """Raised when an event is not found in storage."""

    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event not found: {event_id}", operation="load_event")


class EventAlreadyExistsError(RepositoryError):
    """Raised when trying to save an event that already exists."""

    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event already exists: {event_id}", operation="save_event")


class IndexCorruptedError(StorageError):
    """Raised when the storage index is corrupted."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StorageNotFoundError(StorageError):
    """Raised when a storage resource is not found."""

    def __init__(self, message: str, path: str | None = None, event_id: str | None = None) -> None:
        self.path = path
        self.event_id = event_id
        super().__init__(message)


class StorageNotFoundError(RepositoryError):
    """Raised when a storage item is not found."""

    def __init__(self, message: str, event_id: str | None = None) -> None:
        self.event_id = event_id
        super().__init__(message, operation="load")