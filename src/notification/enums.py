"""
EVRECONSE Notification - Enums.

Enumeration types for notification system.
"""

from __future__ import annotations

from enum import StrEnum


class DeliveryStatus(StrEnum):
    """Delivery status of a notification."""

    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(StrEnum):
    """Supported notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"


class NotificationPriority(StrEnum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageFormat(StrEnum):
    """Supported message formats."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    MARKDOWN_V2 = "markdown_v2"
    HTML = "html"


class QueuePolicy(StrEnum):
    """Queue overflow policy."""

    REJECT = "reject"          # Reject new notifications when full
    DROP_OLDEST = "drop_oldest"  # Remove oldest pending notification
    DROP_LOWEST_PRIORITY = "drop_lowest_priority"  # Remove lowest priority
    BLOCK = "block"            # Block until space available
