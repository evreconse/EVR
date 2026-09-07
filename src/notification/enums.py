"""
EVRECONSE Notification - Enums.

Enumeration types for notification system.
"""

from __future__ import annotations

from enum import Enum


class DeliveryStatus(str, Enum):
    """Delivery status of a notification."""

    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageFormat(str, Enum):
    """Supported message formats."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    MARKDOWN_V2 = "markdown_v2"
    HTML = "html"


class QueuePolicy(str, Enum):
    """Queue overflow policy."""

    REJECT = "reject"          # Reject new notifications when full
    DROP_OLDEST = "drop_oldest"  # Remove oldest pending notification
    DROP_LOWEST_PRIORITY = "drop_lowest_priority"  # Remove lowest priority
    BLOCK = "block"            # Block until space available