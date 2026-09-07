"""
EVRECONSE Event Engine Module.

Core event processing orchestration engine.
"""

from .enums import EventStatus, EventType, ProcessingStage
from .event_dispatcher import EventDispatcher
from .event_engine import (
    EngineConfig,
    EngineStats,
    EventEngine,
    get_event_engine,
    reset_event_engine,
)
from .event_factory import EventFactory
from .event_pipeline import EventPipeline, PipelineConfig, PipelineResult
from .event_registry import EventRegistry
from .event_scheduler import EventScheduler
from .exceptions import (
    DuplicateEventError,
    EventAlreadyExistsError,
    EventConflictError,
    EventCreationError,
    EventDispatcherError,
    EventEngineError,
    EventNotFoundError,
    EventPersistenceError,
    EventPipelineError,
    EventProcessingError,
    EventRecoveryError,
    EventRegistryError,
    EventSchedulerError,
    EventStateError,
    EventTimeoutError,
    EventTransitionError,
    EventValidationError,
    InvalidEventStateError,
    InvalidStateTransitionError,
    TransitionGuardError,
)
from .metrics import MetricsCollector, get_metrics
from .state_machine import is_valid_transition
from .transition_guard import TransitionGuard

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