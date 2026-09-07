"""
EVRECONSE Event Engine Module.

Core event processing orchestration engine.
"""

from .event_engine import (
    EventEngine,
    EngineConfig,
    EngineStats,
    get_event_engine,
    reset_event_engine,
)
from .event_pipeline import EventPipeline, PipelineConfig, PipelineResult
from .event_registry import EventRegistry
from .event_scheduler import EventScheduler
from .event_dispatcher import EventDispatcher
from .event_factory import EventFactory
from .state_machine import is_valid_transition
from .transition_guard import TransitionGuard
from .metrics import MetricsCollector, get_metrics
from .enums import EventStatus, EventType, ProcessingStage
from .exceptions import (
    EventEngineError,
    EventNotFoundError,
    EventProcessingError,
    EventPipelineError,
    EventValidationError,
    EventStateError,
    EventCreationError,
    EventAlreadyExistsError,
    EventTransitionError,
    EventDispatcherError,
    EventRegistryError,
    EventSchedulerError,
    EventRecoveryError,
    EventPersistenceError,
    EventTimeoutError,
    TransitionGuardError,
    InvalidEventStateError,
    InvalidStateTransitionError,
    DuplicateEventError,
    EventConflictError,
)

__all__ = [
    # Core Engine (Public API)
    "EventEngine",
    "EngineConfig",
    "EngineStats",
    "get_event_engine",
    "reset_event_engine",
    # Pipeline
    "EventPipeline",
    "PipelineConfig",
    "PipelineResult",
    # Registry
    "EventRegistry",
    # Scheduler
    "EventScheduler",
    # Dispatcher
    "EventDispatcher",
    # Factory
    "EventFactory",
    # State Machine (string-based for Event Engine internal use)
    "is_valid_transition",
    "TransitionGuard",
    # Metrics
    "MetricsCollector",
    "get_metrics",
    # Enums
    "EventStatus",
    "EventType",
    "ProcessingStage",
    # Exceptions
    "EventEngineError",
    "EventNotFoundError",
    "EventProcessingError",
    "EventPipelineError",
    "EventValidationError",
    "EventStateError",
    "EventCreationError",
    "EventAlreadyExistsError",
    "EventTransitionError",
    "EventDispatcherError",
    "EventRegistryError",
    "EventSchedulerError",
    "EventRecoveryError",
    "EventPersistenceError",
    "EventTimeoutError",
    "TransitionGuardError",
    "InvalidEventStateError",
    "InvalidStateTransitionError",
    "DuplicateEventError",
    "EventConflictError",
]