"""
EVRECONSE Models - Transition Guard.

Centralized state machine for MarketEvent lifecycle transitions.
Single Source of Truth for all state transitions.
"""

from __future__ import annotations

from typing import Any

from .enums import EventStatus
from .exceptions import InvalidTransitionError, InvariantViolationError

# =============================================================================
# Immutable Transition Map - Single Source of Truth
# =============================================================================

# Valid state transitions - defined ONCE here
_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.NEW: frozenset({EventStatus.QUALIFIED, EventStatus.DISMISSED}),
    EventStatus.QUALIFIED: frozenset({EventStatus.SCORED, EventStatus.DISMISSED}),
    EventStatus.SCORED: frozenset({EventStatus.SIGNAL, EventStatus.DISMISSED}),
    EventStatus.SIGNAL: frozenset({EventStatus.MONITORING}),
    EventStatus.DISMISSED: frozenset(),
    EventStatus.MONITORING: frozenset({EventStatus.COMPLETED, EventStatus.EXPIRED}),
    EventStatus.COMPLETED: frozenset(),
    EventStatus.EXPIRED: frozenset(),
}

# Terminal states - derived from transitions
_TERMINAL_STATES: frozenset[EventStatus] = frozenset(
    status for status, targets in _ALLOWED_TRANSITIONS.items() if not targets
)

# States that require a score
_SCORED_STATES: frozenset[EventStatus] = frozenset({
    EventStatus.SCORED,
    EventStatus.SIGNAL,
    EventStatus.MONITORING,
    EventStatus.COMPLETED,
    EventStatus.EXPIRED,
})

# States that can receive notifications
_NOTIFIABLE_STATES: frozenset[EventStatus] = frozenset({EventStatus.SIGNAL})

# States that can be monitored
_MONITORING_STATES: frozenset[EventStatus] = frozenset({EventStatus.MONITORING})

# States that can be scored
_SCORABLE_STATES: frozenset[EventStatus] = frozenset({EventStatus.QUALIFIED})


def is_valid_transition(from_state: EventStatus, to_state: EventStatus) -> bool:
    """Check if state transition is valid."""
    return to_state in _ALLOWED_TRANSITIONS.get(from_state, frozenset())


def is_terminal(state: EventStatus) -> bool:
    """Check if state is terminal (no further transitions allowed)."""
    return state in _TERMINAL_STATES


def requires_score(state: EventStatus) -> bool:
    """Check if state requires a score."""
    return state in _SCORED_STATES


def can_notify(state: EventStatus) -> bool:
    """Check if state allows notifications."""
    return state in _NOTIFIABLE_STATES


def can_monitor(state: EventStatus) -> bool:
    """Check if state requires monitoring."""
    return state in _MONITORING_STATES


def can_score(state: EventStatus) -> bool:
    """Check if state can be scored."""
    return state in _SCORABLE_STATES


def get_allowed_next_states(state: EventStatus) -> frozenset[EventStatus]:
    """Get allowed next states from current state."""
    return _ALLOWED_TRANSITIONS.get(state, frozenset())


def get_all_transitions() -> dict[EventStatus, frozenset[EventStatus]]:
    """Get all valid transitions (read-only view)."""
    return _ALLOWED_TRANSITIONS.copy()


def get_terminal_states() -> frozenset[EventStatus]:
    """Get all terminal states."""
    return _TERMINAL_STATES


# =============================================================================
# Transition Guard - Centralized Validation
# =============================================================================

class TransitionGuard:
    """
    Centralized transition validation.
    
    All state transitions must pass through this guard.
    Uses the single source of truth from _ALLOWED_TRANSITIONS.
    """
    
    @staticmethod
    def validate(
        from_state: EventStatus,
        to_state: EventStatus,
        event_id: str | None = None,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Validate state transition.
        
        Args:
            from_state: Current state
            to_state: Target state
            event_id: Optional event ID for error messages
            event_data: Optional event data for additional validation
            
        Raises:
            InvalidTransitionError: If transition is not allowed
        """
        if not is_valid_transition(from_state, to_state):
            raise InvalidTransitionError(
                event_id=event_id or "unknown",
                current_state=from_state.value,
                target_state=to_state.value,
                reason=f"Transition not allowed by state machine: {from_state.value} -> {to_state.value}",
            )
        
        # Additional guard: cannot transition from terminal state
        if is_terminal(from_state):
            raise InvalidTransitionError(
                event_id=event_id or "unknown",
                current_state=from_state.value,
                target_state=to_state.value,
                reason=f"Cannot transition from terminal state '{from_state.value}'",
            )
    
    @staticmethod
    def validate_score_requirement(
        event_id: str,
        state: EventStatus,
        score: float | None,
    ) -> None:
        """Validate that state requiring score has valid score."""
        if requires_score(state):
            if score is None:
                raise InvariantViolationError(
                    f"Event {event_id}: state {state.value} requires a score, got None"
                )
            if not (0 <= score <= 100):
                raise InvariantViolationError(
                    f"Event {event_id}: score must be 0-100, got {score}"
                )
    
    @staticmethod
    def validate_score_threshold(
        event_id: str,
        score: float,
        threshold: float,
        operation: str = "transition to signal",
    ) -> None:
        """Validate score meets minimum threshold."""
        if score < threshold:
            raise InvariantViolationError(
                f"Event {event_id}: score {score:.2f} below threshold {threshold} for {operation}"
            )
    
    @staticmethod
    def validate_not_terminal(event_id: str, state: EventStatus) -> None:
        """Validate that state is not terminal."""
        if is_terminal(state):
            raise InvariantViolationError(
                f"Event {event_id}: cannot operate on terminal state {state.value}"
            )


# =============================================================================
# Guard Functions for Specific Transitions
# =============================================================================

def guard_new_to_qualified(event_id: str, event_data: dict[str, Any]) -> None:
    """Guard: NEW -> QUALIFIED."""
    TransitionGuard.validate(EventStatus.NEW, EventStatus.QUALIFIED, event_id, event_data)


def guard_qualified_to_scored(event_id: str, event_data: dict[str, Any], score: float) -> None:
    """Guard: QUALIFIED -> SCORED."""
    TransitionGuard.validate(EventStatus.QUALIFIED, EventStatus.SCORED, event_id, event_data)
    TransitionGuard.validate_score_requirement(event_id, EventStatus.SCORED, score)


def guard_scored_to_signal(event_id: str, score: float, threshold: float = 80.0) -> None:
    """Guard: SCORED -> SIGNAL."""
    TransitionGuard.validate(EventStatus.SCORED, EventStatus.SIGNAL, event_id)
    TransitionGuard.validate_score_requirement(event_id, EventStatus.SIGNAL, score)
    TransitionGuard.validate_score_threshold(event_id, score, threshold, "transition to signal")


def guard_scored_to_dismissed(event_id: str) -> None:
    """Guard: SCORED -> DISMISSED."""
    TransitionGuard.validate(EventStatus.SCORED, EventStatus.DISMISSED, event_id)


def guard_signal_to_monitoring(event_id: str) -> None:
    """Guard: SIGNAL -> MONITORING."""
    TransitionGuard.validate(EventStatus.SIGNAL, EventStatus.MONITORING, event_id)


def guard_monitoring_to_completed(event_id: str) -> None:
    """Guard: MONITORING -> COMPLETED."""
    TransitionGuard.validate(EventStatus.MONITORING, EventStatus.COMPLETED, event_id)


def guard_monitoring_to_expired(event_id: str) -> None:
    """Guard: MONITORING -> EXPIRED."""
    TransitionGuard.validate(EventStatus.MONITORING, EventStatus.EXPIRED, event_id)


def guard_any_to_dismissed(event_id: str, from_state: EventStatus) -> None:
    """Guard: ANY -> DISMISSED (from active states only)."""
    active_states = {EventStatus.NEW, EventStatus.QUALIFIED, EventStatus.SCORED, EventStatus.SIGNAL}
    if from_state not in active_states:
        raise InvalidTransitionError(
            event_id=event_id,
            current_state=from_state.value,
            target_state=EventStatus.DISMISSED.value,
            reason=f"Can only dismiss from active states: {[s.value for s in active_states]}",
        )


def guard_any_to_failed(event_id: str, from_state: EventStatus) -> None:
    """Guard: ANY -> FAILED (from active processing states)."""
    # Note: FAILED is not a valid EventStatus in models - using EXPIRED instead
    # This is kept for compatibility with event_engine state machine
    active_states = {EventStatus.NEW, EventStatus.QUALIFIED, EventStatus.SCORED, EventStatus.SIGNAL, EventStatus.MONITORING}
    if from_state not in active_states:
        raise InvalidTransitionError(
            event_id=event_id,
            current_state=from_state.value,
            target_state="FAILED",
            reason="Can only fail from active processing states",
        )