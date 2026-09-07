"""
EVRECONSE Strategy - Exceptions.

Strategy-specific exceptions for validation, registration, and execution errors.
"""

from __future__ import annotations


class StrategyError(Exception):
    """Base exception for strategy errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StrategyRegistrationError(StrategyError):
    """Raised when strategy registration fails."""

    def __init__(self, message: str, strategy_id: str | None = None) -> None:
        self.strategy_id = strategy_id
        super().__init__(message)


class StrategyNotFoundError(StrategyError):
    """Raised when strategy is not found in registry."""

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Strategy not found: {strategy_id}")


class StrategyValidationError(StrategyError):
    """Raised when strategy validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class StrategyConfigurationError(StrategyError):
    """Raised when strategy configuration is invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class StrategyExecutionError(StrategyError):
    """Raised when strategy execution fails."""

    def __init__(self, message: str, strategy_id: str | None = None) -> None:
        self.strategy_id = strategy_id
        super().__init__(message)


class StrategyValidationError(StrategyError):
    """Raised when strategy validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class StrategyNotRegisteredError(StrategyError):
    """Raised when attempting to use unregistered strategy."""

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Strategy not registered: {strategy_id}")


class StrategyAlreadyRegisteredError(StrategyError):
    """Raised when attempting to register duplicate strategy."""

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Strategy already registered: {strategy_id}")


class StrategyContextError(StrategyError):
    """Raised when StrategyContext is invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class StrategyInitializationError(StrategyError):
    """Raised when strategy initialization fails."""

    def __init__(self, message: str, strategy_id: str | None = None) -> None:
        self.strategy_id = strategy_id
        super().__init__(message)