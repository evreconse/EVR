"""
EVRECONSE Event Engine - Enums.

Enumeration types for Event Engine.
"""

from __future__ import annotations

from enum import Enum


class EventStatus(str, Enum):
    """Event lifecycle statuses."""

    NEW = "new"
    QUALIFIED = "qualified"
    SCORED = "scored"
    SIGNAL = "signal"
    DISMISSED = "dismissed"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class EventType(str, Enum):
    """Event type classification."""
    MARKET = "market"
    QUALIFIED = "qualified"
    SCORED = "scored"
    SIGNAL = "signal"
    OUTCOME = "outcome"
    SYSTEM = "system"


class ProcessingStage(str, Enum):
    """Event processing pipeline stages."""
    CREATED = "created"
    VALIDATED = "validated"
    QUALIFIED = "qualified"
    SCORED = "scored"
    NOTIFIED = "notified"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class SchedulerTaskType(str, Enum):
    """Scheduler task types."""
    EXPIRE_EVENTS = "expire_events"
    MONITOR_EVENTS = "monitor_events"
    CLEANUP_COMPLETED = "cleanup_completed"
    RECOVER_STUCK = "recover_stuck"
    PERSIST_SNAPSHOT = "persist_snapshot"
    HEARTBEAT = "heartbeat"


class HandlerPriority(int, Enum):
    """Handler priority levels."""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 1000