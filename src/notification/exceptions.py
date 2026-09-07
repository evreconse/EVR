"""
EVRECONSE Notification - Exceptions.

Notification-specific exceptions for connection, delivery, and processing errors.
"""

from __future__ import annotations


class NotificationError(Exception):
    """Base exception for notification errors."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


class NotificationError(Exception):
    """Base exception for notification errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ConfigurationError(NotificationError):
    """Raised when notification configuration is invalid."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        self.config_key = config_key
        super().__init__(message)


class ValidationError(NotificationError):
    """Raised when notification validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class TemplateError(NotificationError):
    """Raised when template rendering fails."""

    def __init__(self, message: str, template_name: str | None = None) -> None:
        self.template_name = template_name
        super().__init__(message)


class ChannelError(NotificationError):
    """Raised when channel operation fails."""

    def __init__(self, message: str, channel: str | None = None) -> None:
        self.channel = channel
        super().__init__(message)


class ConnectionError(NotificationError):
    """Raised when channel connection fails."""

    def __init__(self, message: str, channel: str | None = None) -> None:
        self.channel = channel
        super().__init__(message)


class AuthenticationError(ConnectionError):
    """Raised when channel authentication fails."""

    def __init__(self, message: str, channel: str | None = None) -> None:
        super().__init__(message, channel)


class RateLimitError(ChannelError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, channel: str | None = None, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message, channel)


class DeliveryError(NotificationError):
    """Raised when notification delivery fails."""

    def __init__(
        self,
        message: str,
        notification_id: str | None = None,
        channel: str | None = None,
        recipient: str | None = None,
        retryable: bool = True,
    ) -> None:
        self.notification_id = notification_id
        self.channel = channel
        self.recipient = recipient
        self.retryable = retryable
        super().__init__(message)


class DeliveryFailedError(DeliveryError):
    """Raised when delivery permanently fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, retryable=False, **kwargs)


class DeliveryTimeoutError(DeliveryError):
    """Raised when delivery times out."""

    def __init__(self, message: str, timeout: float, **kwargs) -> None:
        self.timeout = timeout
        super().__init__(message, retryable=True, **kwargs)


class QueueFullError(NotificationError):
    """Raised when notification queue is full."""

    def __init__(
        self,
        message: str = "Notification queue is full",
        queue_size: int | None = None,
        max_size: int | None = None,
    ) -> None:
        self.queue_size = queue_size
        self.max_size = max_size
        super().__init__(message)


class TemplateError(NotificationError):
    """Raised when template processing fails."""

    def __init__(
        self,
        message: str,
        template_name: str | None = None,
        template_path: str | None = None,
    ) -> None:
        self.template_name = template_name
        self.template_path = template_path
        super().__init__(message)


class RetryPolicyError(NotificationError):
    """Raised when retry policy configuration is invalid."""

    def __init__(self, message: str, policy_name: str | None = None) -> None:
        self.policy_name = policy_name
        super().__init__(message)


class QueueClosedError(NotificationError):
    """Raised when attempting to use a closed queue."""

    def __init__(self, message: str = "Notification queue is closed") -> None:
        super().__init__(message)


class QueueEmptyError(NotificationError):
    """Raised when notification queue is empty."""

    def __init__(self, message: str = "Notification queue is empty") -> None:
        super().__init__(message)


class SubscriptionError(NotificationError):
    """Raised when subscription operation fails."""

    def __init__(self, message: str, channel: str | None = None) -> None:
        self.channel = channel
        super().__init__(message)