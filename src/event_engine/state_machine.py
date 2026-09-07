"""
EVRECONSE Event Engine - State Machine.

Thin wrapper around Models layer transition guard.
Models layer is the Single Source of Truth for state transitions.
"""

from __future__ import annotations

from models import (
    EventStatus,
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

# Re-export all functions from models layer
__all__ = [
    "EventStatus",
    "TransitionGuard",
    "can_monitor",
    "can_notify",
    "can_score",
    "get_all_transitions",
    "get_allowed_next_states",
    "get_terminal_states",
    "guard_any_to_dismissed",
    "guard_any_to_failed",
    "guard_monitoring_to_completed",
    "guard_monitoring_to_expired",
    "guard_new_to_qualified",
    "guard_qualified_to_scored",
    "guard_scored_to_dismissed",
    "guard_scored_to_signal",
    "guard_signal_to_monitoring",
    "is_terminal",
    "is_valid_transition",
    "requires_score",
]

# For backward compatibility with string-based state machine
# Convert EventStatus enum to string for internal use
def _status_to_str(status: EventStatus) -> str:
    return status.value


def is_valid_transition_str(from_state: str, to_state: str) -> bool:
    """Check if string-based state transition is valid."""
    try:
        from_enum = EventStatus(from_state)
        to_enum = EventStatus(to_state)
        return is_valid_transition(from_enum, to_enum)
    except ValueError:
        return False


def is_terminal_str(state: str) -> bool:
    """Check if string state is terminal."""
    try:
        return is_terminal(EventStatus(state))
    except ValueError:
        return False


def requires_score_str(state: str) -> bool:
    """Check if string state requires a score."""
    try:
        return requires_score(EventStatus(state))
    except ValueError:
        return False


def can_notify_str(state: str) -> bool:
    """Check if string state allows notifications."""
    try:
        return can_notify(EventStatus(state))
    except ValueError:
        return False


def can_monitor_str(state: str) -> bool:
    """Check if string state requires monitoring."""
    try:
        return can_monitor(EventStatus(state))
    except ValueError:
        return False


def can_score_str(state: str) -> bool:
    """Check if string state can be scored."""
    try:
        return can_score(EventStatus(state))
    except ValueError:
        return False


def get_allowed_next_states_str(state: str) -> set[str]:
    """Get allowed next states from string state."""
    try:
        return {s.value for s in get_allowed_next_states(EventStatus(state))}
    except ValueError:
        return set()