"""
EVRECONSE Event Engine - Exceptions.

Event Engine-specific exceptions for validation, processing, and state errors.
"""

from __future__ import annotations


class EventEngineError(Exception):
    """Base exception for Event Engine errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class EventNotFoundError(EventEngineError):
    """Raised when event is not found in registry."""

    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event not found: {event_id}")


class EventAlreadyExistsError(EventEngineError):
    """Raised when attempting to create duplicate event."""

    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event already exists: {event_id}")


class InvalidStateTransitionError(EventEngineError):
    """Raised when state transition is not allowed."""

    def __init__(
        self,
        event_id: str,
        current_state: str,
        target_state: str,
        reason: str | None = None,
    ) -> None:
        self.event_id = event_id
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason
        msg = f"Invalid transition for {event_id}: {current_state} -> {target_state}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class EventValidationError(EventEngineError):
    """Raised when event validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class EventCreationError(EventEngineError):
    """Raised when event creation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class PipelineError(EventEngineError):
    """Raised when pipeline execution fails."""

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        event_id: str | None = None,
        recoverable: bool = True,
    ) -> None:
        self.stage = stage
        self.event_id = event_id
        self.recoverable = recoverable
        msg = message
        if stage:
            msg = f"Pipeline stage '{stage}' failed: {message}"
        if event_id:
            msg += f" (event: {event_id})"
        super().__init__(msg)


class StateMachineError(EventEngineError):
    """Raised when state machine operation fails."""

    def __init__(self, message: str, event_id: str | None = None, state: str | None = None) -> None:
        self.event_id = event_id
        self.state = state
        super().__init__(message)


class TransitionGuardError(EventEngineError):
    """Raised when transition guard condition fails."""

    def __init__(
        self,
        event_id: str,
        from_state: str,
        to_state: str,
        guard_name: str,
        reason: str,
    ) -> None:
        self.event_id = event_id
        self.from_state = from_state
        self.to_state = to_state
        self.guard_name = guard_name
        self.reason = reason
        super().__init__(
            f"Transition guard '{guard_name}' failed for {event_id}: "
            f"{from_state} -> {to_state}: {reason}"
        )


class EventEngineNotInitializedError(EventEngineError):
    """Raised when engine is used before initialization."""

    def __init__(self, message: str = "Event Engine not initialized") -> None:
        super().__init__(message)


class EventEngineShutdownError(EventEngineError):
    """Raised when operation attempted during shutdown."""

    def __init__(self, message: str = "Event Engine is shutting down") -> None:
        super().__init__(message)


class EventTimeoutError(EventEngineError):
    """Raised when event processing times out."""

    def __init__(self, event_id: str, stage: str, timeout_seconds: float) -> None:
        self.event_id = event_id
        self.stage = stage
        self.timeout = timeout_seconds
        super().__init__(
            f"Event {event_id} timed out at stage '{stage}' after {timeout_seconds} seconds"
        )


class EventPersistenceError(EventEngineError):
    """Raised when event persistence fails."""

    def __init__(self, message: str, event_id: str | None = None, operation: str | None = None) -> None:
        self.event_id = event_id
        self.operation = operation
        msg = message
        if event_id:
            msg += f" (event: {event_id})"
        if operation:
            msg += f" (operation: {operation})"
        super().__init__(msg)


class EventRecoveryError(EventEngineError):
    """Raised when event recovery fails."""

    def __init__(self, message: str, event_id: str | None = None, stage: str | None = None) -> None:
        self.event_id = event_id
        self.stage = stage
        super().__init__(message)


class EventSerializationError(EventEngineError):
    """Raised when event serialization/deserialization fails."""

    def __init__(self, message: str, event_id: str | None = None) -> None:
        self.event_id = event_id
        super().__init__(message)


class InvalidEventStateError(EventEngineError):
    """Raised when event is in unexpected state."""

    def __init__(self, event_id: str, expected_state: str, actual_state: str) -> None:
        self.event_id = event_id
        self.expected_state = expected_state
        self.actual_state = actual_state
        super().__init__(
            f"Event {event_id} has invalid state: expected {expected_state}, got {actual_state}"
        )


class DuplicateEventError(EventEngineError):
    """Raised when duplicate event is detected."""

    def __init__(self, event_id: str, existing_id: str | None = None) -> None:
        self.event_id = event_id
        self.existing_id = existing_id
        super().__init__(f"Duplicate event: {event_id}" + (f" (conflicts with {existing_id})" if existing_id else ""))


class EventConflictError(EventEngineError):
    """Raised when event conflicts with existing event."""

    def __init__(
        self,
        event_id: str,
        conflicting_id: str,
        reason: str,
    ) -> None:
        self.event_id = event_id
        self.conflicting_id = conflicting_id
        self.reason = reason
        super().__init__(
            f"Event {event_id} conflicts with {conflicting_id}: {reason}"
        )


class EventDispatcherError(EventEngineError):
    """Raised when dispatcher operation fails."""

    def __init__(
        self,
        message: str,
        event_id: str | None = None,
    ) -> None:
        self.event_id = event_id
        super().__init__(message)


class EventRegistryError(EventEngineError):
    """Raised when registry operation fails."""

    def __init__(
        self,
        message: str,
        event_id: str | None = None,
    ) -> None:
        self.event_id = event_id
        super().__init__(message)


class EventSchedulerError(EventEngineError):
    """Raised when scheduler operation fails."""

    def __init__(
        self,
        message: str,
        event_id: str | None = None,
    ) -> None:
        self.event_id = event_id
        super().__init__(message)


# Aliases for backward compatibility
EventPipelineError = PipelineError
EventProcessingError = StateMachineError
EventStateError = InvalidEventStateError
EventTransitionError = InvalidStateTransitionError