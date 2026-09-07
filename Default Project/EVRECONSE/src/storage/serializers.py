"""
EVRECONSE Storage - Serialization.

Centralized serialization/deserialization for MarketEvent.
Uses the model's built-in to_dict/from_dict methods.
"""

from __future__ import annotations

from uuid import UUID
from models import EventID, MarketEvent


def serialize_event(event: MarketEvent) -> dict:
    """
    Serialize a MarketEvent to a dictionary.

    Uses the model's built-in to_dict() method.

    Args:
        event: The market event to serialize.

    Returns:
        JSON-serializable dictionary.
    """
    return event.to_dict()


def deserialize_event(data: dict) -> MarketEvent:
    """
    Deserialize a MarketEvent from a dictionary.

    Uses the model's built-in from_dict() method.
    Fail-fast on any validation error.

    Args:
        data: The dictionary to deserialize.

    Returns:
        The deserialized MarketEvent.

    Raises:
        ModelValidationError: If data is invalid or corrupted.
    """
    from models import MarketEvent
    return MarketEvent.from_dict(data)


def event_id_to_filename(event_id: EventID) -> str:
    """
    Convert an EventID to a filename.

    The filename is the EventID string with .json extension.
    No other filename format is allowed.

    Args:
        event_id: The event identifier.

    Returns:
        Filename string (e.g., "123e4567-e89b-12d3-a456-426614174000.json").
    """
    return f"{event_id}.json"


def filename_to_event_id(filename: str) -> EventID:
    """
    Extract EventID from a filename.

    Args:
        filename: The filename (e.g., "123e4567-e89b-12d3-a456-426614174000.json").

    Returns:
        The EventID.

    Raises:
        ValueError: If the filename is not a valid EventID filename.
    """
    if not filename.endswith(".json"):
        raise ValueError(f"Invalid event filename: {filename}")
    event_id_str = filename[:-5]  # Remove .json
    from models import EventID
    return EventID.from_string(event_id_str)


def serialize_for_storage(event: MarketEvent) -> bytes:
    """
    Serialize a MarketEvent to JSON bytes for storage.

    Args:
        event: The market event to serialize.

    Returns:
        JSON bytes encoded as UTF-8.
    """
    import json
    return json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def deserialize_from_storage(data: bytes) -> MarketEvent:
    """
    Deserialize a MarketEvent from JSON bytes.

    Args:
        data: JSON bytes from storage.

    Returns:
        The deserialized MarketEvent.

    Raises:
        StorageSerializationError: If deserialization fails.
    """
    import json
    try:
        data = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        from .exceptions import StorageSerializationError
        raise StorageSerializationError(f"Invalid JSON data: {e}") from e

    from models import MarketEvent
    return MarketEvent.from_dict(data)
