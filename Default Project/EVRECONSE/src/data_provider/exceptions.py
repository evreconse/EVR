"""
EVRECONSE Data Provider - Exceptions.

Data Provider-specific exceptions for connection, subscription, and data errors.
"""

from __future__ import annotations


class DataProviderError(Exception):
    """Base exception for data provider errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ConnectionError(DataProviderError):
    """Raised when connection to the exchange fails."""

    def __init__(self, message: str, exchange: str | None = None) -> None:
        self.exchange = exchange
        super().__init__(message)


class AuthenticationError(DataProviderError):
    """Raised when authentication with the exchange fails."""

    def __init__(self, message: str, exchange: str | None = None) -> None:
        self.exchange = exchange
        super().__init__(message)


class SubscriptionError(DataProviderError):
    """Raised when subscription to market data fails."""

    def __init__(self, message: str, channel: str | None = None) -> None:
        self.channel = channel
        super().__init__(message)


class RateLimitError(DataProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class ReconnectError(DataProviderError):
    """Raised when reconnection fails after max attempts."""

    def __init__(self, message: str, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(message)


class HeartbeatTimeoutError(DataProviderError):
    """Raised when heartbeat timeout is exceeded."""

    def __init__(self, message: str, last_heartbeat: float | None = None) -> None:
        self.last_heartbeat = last_heartbeat
        super().__init__(message)


class InvalidMessageError(DataProviderError):
    """Raised when a received message is invalid or malformed."""

    def __init__(self, message: str, raw_data: str | bytes | None = None) -> None:
        self.raw_data = raw_data
        super().__init__(message)


class SnapshotError(DataProviderError):
    """Raised when snapshot retrieval fails."""

    def __init__(self, message: str, endpoint: str | None = None) -> None:
        self.endpoint = endpoint
        super().__init__(message)


class DataProviderNotInitializedError(DataProviderError):
    """Raised when data provider is accessed before initialization."""

    def __init__(self, message: str = "Data provider not initialized") -> None:
        super().__init__(message)


class DataProviderNotConnectedError(DataProviderError):
    """Raised when data provider is not connected."""

    def __init__(self, message: str = "Data provider not connected") -> None:
        super().__init__(message)