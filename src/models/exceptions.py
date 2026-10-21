"""
EVRECONSE Models - Exceptions.

Model-specific exceptions for validation and serialization errors.
"""

from __future__ import annotations


class ModelError(Exception):
    """Base exception for model errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ModelValidationError(ValueError):
    """
    Raised when model validation fails.

    Includes transition validation, field constraints, and deserialization errors.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class InvalidTransitionError(ModelValidationError):
    """Raised when a state transition is not allowed."""

    def __init__(
        self,
        event_id: str,
        current_state: str,
        target_state: str,
        reason: str,
    ) -> None:
        message = (
            f"Invalid transition for event {event_id}: "
            f"{current_state} -> {target_state}. {reason}"
        )
        super().__init__(message)
        self.event_id = event_id
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason


class InvariantViolationError(ModelValidationError):
    """Raised when a model invariant is violated."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, field)
