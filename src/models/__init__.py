"""
EVRECONSE Models Layer.

Core domain models for market events and identifiers.
Zero business logic - only data structures and safe state transitions.
"""

from .enums import (
    EventOutcome,
    EventStatus,
    Exchange,
    NotificationChannel,
    ScoreParameter,
    Timeframe,
)
from .exceptions import InvalidTransitionError, InvariantViolationError, ModelValidationError
from .identifiers import EventID, SignalID
from .market_event import (
    MarketData,
    MarketEvent,
    Metadata,
    NotificationData,
    OutcomeData,
    ScoreBreakdownItem,
    ScoreData,
    StrategyData,
)
from .transition_guard import (
    TransitionGuard,
    can_monitor,
    can_notify,
    can_score,
    get_all_transitions,
    get_allowed_next_states,
    get_terminal_states,
    guard_any_to_dismissed,
    guard_any_to_failed,
    guard_monitoring_to_completed,
    guard_monitoring_to_expired,
    guard_new_to_qualified,
    guard_qualified_to_scored,
    guard_scored_to_dismissed,
    guard_scored_to_signal,
    guard_signal_to_monitoring,
    is_terminal,
    is_valid_transition,
    requires_score,
)

__all__ = [
    # Enums
    "EventStatus",
    "EventOutcome",
    "Exchange",
    "Timeframe",
    "NotificationChannel",
    "ScoreParameter",
    # Identifiers
    "EventID",
    "SignalID",
    # Exceptions
    "ModelValidationError",
    "InvalidTransitionError",
    "InvariantViolationError",
    # Transition Guard (Single Source of Truth)
    "TransitionGuard",
    "is_valid_transition",
    "is_terminal",
    "requires_score",
    "can_notify",
    "can_monitor",
    "can_score",
    "get_allowed_next_states",
    "get_all_transitions",
    "get_terminal_states",
    "guard_new_to_qualified",
    "guard_qualified_to_scored",
    "guard_scored_to_signal",
    "guard_scored_to_dismissed",
    "guard_signal_to_monitoring",
    "guard_monitoring_to_completed",
    "guard_monitoring_to_expired",
    "guard_any_to_dismissed",
    "guard_any_to_failed",
    # Nested Data
    "Metadata",
    "MarketData",
    "StrategyData",
    "ScoreBreakdownItem",
    "ScoreData",
    "NotificationData",
    "OutcomeData",
    # Main
    "MarketEvent",
]