"""
EVRECONSE Notification Module.

Comprehensive notification delivery system with multi-channel support.
"""

from .delivery_result import DeliveryAttempt, DeliveryResult, DeliveryStatus
from .enums import (
    DeliveryStatus,
    MessageFormat,
    NotificationChannel,
    NotificationPriority,
    QueuePolicy,
)
from .exceptions import (
    AuthenticationError,
    ChannelError,
    ConfigurationError,
    ConnectionError,
    DeliveryError,
    DeliveryFailedError,
    DeliveryTimeoutError,
    NotificationError,
    QueueClosedError,
    QueueEmptyError,
    QueueFullError,
    RateLimitError,
    RetryPolicyError,
    SubscriptionError,
    TemplateError,
    ValidationError,
)
from .formatter import (
    BaseFormatter,
    FormatOptions,
    Formatter,
    FormatterFactory,
    HTMLFormatter,
    MarkdownV2Formatter,
    PlainTextFormatter,
)
from .heartbeat import HeartbeatConfig, HeartbeatMonitor
from .notification import Notification, NotificationService
from .notification_engine import NotificationEngine, EngineConfig
from .queue import NotificationQueue, QueuedNotification, SyncNotificationQueue
from .rate_limiter import RateLimitConfig, RateLimiter, TokenBucketRateLimiter
from .retry_policy import RetryExecutor, RetryPolicy, RetryPolicyConfig, RetryStrategy
from .telegram_service import TelegramConfig, TelegramService, create_telegram_service
from .templates import DEFAULT_TEMPLATES, TemplateEngine, get_all_template_names, get_default_template

__all__ = [
    # Core
    "Notification",
    "NotificationService",
    "NotificationEngine",
    "NotificationEngineConfig",
    # Queue
    "NotificationQueue",
    "QueuedNotification",
    "SyncNotificationQueue",
    # Delivery Result
    "DeliveryResult",
    "DeliveryAttempt",
    "DeliveryStatus",
    # Enums
    "NotificationChannel",
    "NotificationPriority",
    "MessageFormat",
    "QueuePolicy",
    # Rate Limiter
    "RateLimiter",
    "RateLimitConfig",
    "TokenBucketRateLimiter",
    # Retry Policy
    "RetryPolicy",
    "RetryPolicyConfig",
    "RetryStrategy",
    "RetryExecutor",
    "RetryPolicyError",
    # Heartbeat
    "HeartbeatMonitor",
    "HeartbeatConfig",
    # Formatter
    "Formatter",
    "FormatterFactory",
    "BaseFormatter",
    "MarkdownV2Formatter",
    "HTMLFormatter",
    "PlainTextFormatter",
    "FormatOptions",
    # Templates
    "TemplateEngine",
    "DEFAULT_TEMPLATES",
    "get_default_template",
    "get_all_template_names",
    # Telegram
    "TelegramService",
    "TelegramConfig",
    "create_telegram_service",
    # Exceptions
    "NotificationError",
    "ConfigurationError",
    "ValidationError",
    "TemplateError",
    "ChannelError",
    "ConnectionError",
    "AuthenticationError",
    "SubscriptionError",
    "RateLimitError",
    "DeliveryError",
    "DeliveryFailedError",
    "DeliveryTimeoutError",
    "QueueFullError",
    "QueueClosedError",
    "QueueEmptyError",
]