"""
EVRECONSE Event Engine - Transition Guard.

Thin wrapper around Models layer TransitionGuard.
Models layer is the Single Source of Truth for state transitions.
"""

from __future__ import annotations

from .exceptions import (
    EventStateError,
    InvalidStateTransitionError,
    TransitionGuardError,
)
from .state_machine import (
    can_monitor_str,
    can_notify_str,
    can_score_str,
    get_allowed_next_states_str,
    is_terminal_str,
    is_valid_transition_str,
    requires_score_str,
)

# Valid transitions and terminal states - delegated to state_machine
VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"qualified", "dismissed"},
    "qualified": {"scored", "dismissed"},
    "scored": {"signal", "dismissed"},
    "signal": {"monitoring"},
    "dismissed": set(),
    "monitoring": {"completed", "expired"},
    "completed": set(),
    "expired": set(),
}

TERMINAL_STATES = {"dismissed", "completed", "expired"}
SCORED_STATES = {"scored", "signal", "monitoring", "completed", "expired"}
NOTIFIABLE_STATES = {"signal"}
MONITORING_STATES = {"monitoring"}
SCORABLE_STATES = {"qualified"}
QUALIFIED_STATES = {"qualified"}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """Check if state transition is valid (string-based for backward compatibility)."""
    return is_valid_transition_str(from_state, to_state)


def is_terminal(state: str) -> bool:
    """Check if state is terminal."""
    return is_terminal_str(state)


def requires_score(state: str) -> bool:
    """Check if state requires a score."""
    return requires_score_str(state)


def can_notify(state: str) -> bool:
    """Check if state allows notifications."""
    return can_notify_str(state)


def can_monitor(state: str) -> bool:
    """Check if state requires monitoring."""
    return can_monitor_str(state)


def can_score(state: str) -> bool:
    """Check if state can be scored."""
    return can_score_str(state)


def get_allowed_next_states(state: str) -> set[str]:
    """Get allowed next states from current state."""
    return get_allowed_next_states_str(state)


class TransitionGuard:
    """
    Event Engine Transition Guard.
    
    Delegates to Models layer TransitionGuard for validation.
    Provides string-based interface for Event Engine internal use.
    """
    
    @staticmethod
    def validate_transition(
        event_id: str,
        from_state: str,
        to_state: str,
        event_data: dict | None = None,
    ) -> None:
        """
        Validate state transition.
        
        Args:
            event_id: Event identifier
            from_state: Current state
            to_state: Target state
            event_data: Optional event data for additional validation
            
        Raises:
            InvalidStateTransitionError: If transition is not allowed
        """
        if not is_valid_transition(from_state, to_state):
            raise InvalidStateTransitionError(
                event_id=event_id,
                current_state=from_state,
                target_state=to_state,
                reason=f"Transition not allowed by state machine: {from_state} -> {to_state}",
            )
        
        # Additional guard: cannot transition from terminal state
        if is_terminal(from_state):
            raise InvalidStateTransitionError(
                event_id=event_id,
                current_state=from_state,
                target_state=to_state,
                reason=f"Cannot transition from terminal state '{from_state}'",
            )
    
    @staticmethod
    def validate_score_requirement(event_id: str, state: str, score: float | None) -> None:
        """Validate that state requiring score has valid score."""
        if requires_score(state):
            if score is None:
                raise EventStateError(
                    event_id,
                    f"{state} (requires score)",
                    f"{state} (no score)",
                )
            if not (0 <= score <= 100):
                raise EventStateError(
                    event_id,
                    f"{state} (score 0-100)",
                    f"{state} (score={score})",
                )
    
    @staticmethod
    def validate_terminal_transition(
        event_id: str,
        from_state: str,
        to_state: str,
    ) -> None:
        """Validate transition from terminal state."""
        if is_terminal(from_state):
            raise InvalidStateTransitionError(
                event_id=event_id,
                current_state=from_state,
                target_state=to_state,
                reason=f"Cannot transition from terminal state '{from_state}'",
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
            raise TransitionGuardError(
                event_id,
                "scored",
                "signal",
                "score_threshold",
                f"Score {score:.2f} below threshold {threshold} for {operation}",
            )
    
    @staticmethod
    def validate_not_terminal(event_id: str, state: str) -> None:
        """Validate that state is not terminal."""
        if is_terminal(state):
            raise EventStateError(
                event_id,
                expected_state="non-terminal",
                actual_state=state,
            )


# Guard functions for specific transitions (string-based for Event Engine)
def guard_new_to_qualified(event_id: str, event_data: dict) -> None:
    """Guard: NEW -> QUALIFIED."""
    if not is_valid_transition("new", "qualified"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="new",
            target_state="qualified",
            reason="Transition not allowed by state machine",
        )


def guard_qualified_to_scored(event_id: str, event_data: dict, score: float) -> None:
    """Guard: QUALIFIED -> SCORED."""
    if not is_valid_transition("qualified", "scored"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="qualified",
            target_state="scored",
            reason="Transition not allowed by state machine",
        )
    if score is None or not (0 <= score <= 100):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="qualified",
            target_state="scored",
            reason="Score required for scoring (0-100)",
        )


def guard_scored_to_signal(event_id: str, score: float, threshold: float = 80.0) -> None:
    """Guard: SCORED -> SIGNAL."""
    if not is_valid_transition("scored", "signal"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="scored",
            target_state="signal",
            reason="Transition not allowed by state machine",
        )
    if score < threshold:
        raise TransitionGuardError(
            event_id,
            "scored",
            "signal",
            "score_threshold",
            f"Score {score:.2f} below threshold {threshold} for signal transition",
        )


def guard_any_to_dismissed(event_id: str, from_state: str) -> None:
    """Guard: ANY -> DISMISSED."""
    active_states = {"new", "qualified", "scored", "signal"}
    if from_state not in active_states:
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state=from_state,
            target_state="dismissed",
            reason="Can only dismiss from active states",
        )


def guard_any_to_failed(event_id: str, from_state: str) -> None:
    """Guard: ANY -> FAILED."""
    active_states = {"new", "qualified", "scored", "signal", "monitoring"}
    if from_state not in active_states:
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state=from_state,
            target_state="failed",
            reason="Can only fail from active processing states",
        )


def guard_new_to_dismissed(event_id: str, event_data: dict) -> None:
    """Guard: NEW -> DISMISSED."""
    if not is_valid_transition("new", "dismissed"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="new",
            target_state="dismissed",
            reason="Transition not allowed by state machine",
        )


def guard_qualified_to_dismissed(event_id: str, event_data: dict) -> None:
    """Guard: QUALIFIED -> DISMISSED."""
    if not is_valid_transition("qualified", "dismissed"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="qualified",
            target_state="dismissed",
            reason="Transition not allowed by state machine",
        )


def guard_scored_to_dismissed(event_id: str, event_data: dict) -> None:
    """Guard: SCORED -> DISMISSED."""
    if not is_valid_transition("scored", "dismissed"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="scored",
            target_state="dismissed",
            reason="Transition not allowed by state machine",
        )


def guard_signal_to_dismissed(event_id: str, event_data: dict) -> None:
    """Guard: SIGNAL -> DISMISSED."""
    if not is_valid_transition("signal", "dismissed"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="signal",
            target_state="dismissed",
            reason="Transition not allowed by state machine",
        )


def guard_signal_to_monitoring(event_id: str, event_data: dict) -> None:
    """Guard: SIGNAL -> MONITORING."""
    if not is_valid_transition("signal", "monitoring"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="signal",
            target_state="monitoring",
            reason="Transition not allowed by state machine",
        )


def guard_monitoring_to_completed(event_id: str, event_data: dict) -> None:
    """Guard: MONITORING -> COMPLETED."""
    if not is_valid_transition("monitoring", "completed"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="monitoring",
            target_state="completed",
            reason="Transition not allowed by state machine",
        )


def guard_monitoring_to_expired(event_id: str, event_data: dict) -> None:
    """Guard: MONITORING -> EXPIRED."""
    if not is_valid_transition("monitoring", "expired"):
        raise InvalidStateTransitionError(
            event_id=event_id,
            current_state="monitoring",
            target_state="expired",
            reason="Transition not allowed by state machine",
        )


def guard_monitoring_to_failed(event_id: str, event_data: dict) -> None:
    """Guard: MONITORING -> FAILED."""
    # FAILED is not a valid state in models, but kept for compatibility
    raise InvalidStateTransitionError(
        event_id=event_id,
        current_state="monitoring",
        target_state="failed",
        reason="FAILED is not a valid terminal state (use EXPIRED)",
    )