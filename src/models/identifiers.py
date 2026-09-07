"""
EVRECONSE Models - Identifiers.

Type-safe identifier wrappers for domain entities.
External code MUST NOT create EventID directly - use MarketEvent.new().
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=False, slots=False)
class EventID:
    """
    Unique identifier for a Market Event.

    Immutable. Generated automatically at event creation.
    External code MUST NOT create EventID directly.
    Use MarketEvent.new() which generates it automatically.
    """

    value: UUID

    @classmethod
    def _generate(cls) -> EventID:
        """Generate a new random EventID (internal use only)."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> EventID:
        """Create EventID from string (deserialization only)."""
        return cls(UUID(value))

    @classmethod
    def from_uuid(cls, value: UUID) -> EventID:
        """Create EventID from UUID (deserialization only)."""
        return cls(value)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventID):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, slots=True)
class SignalID:
    """
    Unique identifier for a Signal.

    Derived from EventID when event becomes a Signal.
    Same UUID as the originating EventID.
    """

    value: UUID

    @classmethod
    def from_event_id(cls, event_id: EventID) -> SignalID:
        """Create SignalID from EventID (same UUID)."""
        return cls(event_id.value)

    @classmethod
    def from_string(cls, value: str) -> SignalID:
        """Create SignalID from string (deserialization only)."""
        return cls(UUID(value))

    @classmethod
    def from_uuid(cls, value: UUID) -> SignalID:
        """Create SignalID from UUID (deserialization only)."""
        return cls(value)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SignalID):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)