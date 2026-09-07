"""
EVRECONSE Notification - Delivery Result.

Data classes for notification delivery results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .enums import DeliveryStatus, NotificationChannel


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    """Record of a single delivery attempt."""
    
    attempt_number: int
    channel: str
    recipient: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    error: str | None = None
    error_code: str | None = None
    response_data: dict[str, Any] | None = None
    duration_ms: float = 0.0
    
    @property
    def duration_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """
    Result of a notification delivery attempt.
    
    Immutable result object containing delivery outcome and metadata.
    """
    
    notification_id: UUID
    channel: str
    recipient: str
    status: str  # DeliveryStatus
    sent_at: datetime
    delivered_at: datetime | None = None
    duration_ms: float = 0.0
    attempts: int = 1
    error: str | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if delivery was successful."""
        return self.status == "delivered"
    
    @property
    def is_terminal(self) -> bool:
        """Check if delivery is in a terminal state."""
        return self.status in (
            "delivered",
            "failed",
            "cancelled",
        )
    
    @property
    def duration_ms(self) -> float:
        """Duration from send to delivery in milliseconds."""
        if self.delivered_at:
            return (self.delivered_at - self.sent_at).total_seconds() * 1000
        return 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "notification_id": str(self.notification_id),
            "channel": self.channel,
            "recipient": self.recipient,
            "status": self.status,
            "sent_at": self.sent_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "error": self.error,
            "error_code": self.error_code,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class AggregatedDeliveryResult:
    """
    Complete result of a delivery attempt.
    
    Aggregates all attempts for a single notification.
    """
    
    notification_id: UUID
    channel: str
    recipient: str
    status: str  # DeliveryStatus
    attempts: tuple[Any, ...] = field(default_factory=tuple)  # DeliveryAttempt
    total_duration_ms: float = 0.0
    final_status: str = "pending"  # DeliveryStatus
    final_error: str | None = None
    final_error_code: str | None = None
    
    @property
    def is_success(self) -> bool:
        return self.status == "delivered"
    
    @property
    def total_attempts(self) -> int:
        return len(self.attempts)
    
    @property
    def total_duration_ms(self) -> float:
        return self.total_duration_ms
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "notification_id": str(self.notification_id),
            "channel": self.channel,
            "recipient": self.recipient,
            "status": self.status,
            "attempts": self.total_attempts,
            "total_duration_ms": self.total_duration_ms,
            "final_status": self.final_status,
            "final_error": self.final_error,
            "final_error_code": self.final_error_code,
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "channel": a.channel,
                    "recipient": a.recipient,
                    "started_at": a.started_at.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "success": a.success,
                    "error": a.error,
                    "error_code": a.error_code,
                    "duration_ms": a.duration_ms,
                }
                for a in self.attempts
            ],
        }