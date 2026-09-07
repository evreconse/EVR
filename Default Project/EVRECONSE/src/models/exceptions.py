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

    def __init__(self, current: str, target: str, allowed: list[str]) -> None:
        message = f"Invalid transition: {current} -> {target}. Allowed: {allowed}"
        super().__init__(message)
        self.current = current
        self.target = target
        self.allowed = allowed


class InvariantViolationError(ModelValidationError):
    """Raised when a model invariant is violated."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, field)