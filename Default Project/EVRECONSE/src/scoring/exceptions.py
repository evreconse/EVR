"""
EVRECONSE Scoring - Exceptions.

Scoring-specific exceptions for validation, registration, and computation errors.
"""

from __future__ import annotations


class ScoringError(Exception):
    """Base exception for scoring errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ScoringValidationError(ScoringError):
    """Raised when scoring configuration validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ScoringConfigurationError(ScoringError):
    """Raised when scoring configuration is invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ScoringComputationError(ScoringError):
    """Raised when score computation fails."""

    def __init__(self, message: str, parameter_id: str | None = None) -> None:
        self.parameter_id = parameter_id
        super().__init__(message)


class ParameterNotFoundError(ScoringError):
    """Raised when a scoring parameter is not found in registry."""

    def __init__(self, parameter_id: str) -> None:
        self.parameter_id = parameter_id
        super().__init__(f"Scoring parameter not found: {parameter_id}")


class ParameterAlreadyRegisteredError(ScoringError):
    """Raised when attempting to register duplicate parameter."""

    def __init__(self, parameter_id: str) -> None:
        self.parameter_id = parameter_id
        super().__init__(f"Parameter already registered: {parameter_id}")


class ParameterNotRegisteredError(ScoringError):
    """Raised when attempting to use unregistered parameter."""

    def __init__(self, parameter_id: str) -> None:
        self.parameter_id = parameter_id
        super().__init__(f"Parameter not registered: {parameter_id}")


class ScoringConfigurationError(ScoringError):
    """Raised when scoring configuration is invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ScoringContextError(ScoringError):
    """Raised when ScoringContext is invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ScoringNotInitializedError(ScoringError):
    """Raised when scoring engine is used before initialization."""

    def __init__(self, message: str = "ScoringEngine not initialized") -> None:
        super().__init__(message)