"""
EVRECONSE Event Engine - Engine Configuration.

Configuration dataclasses for Event Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Configuration for Event Engine."""
    
    max_concurrent_events: int = 10
    execution_timeout: float = 30.0
    enable_metrics: bool = True
    enable_persistence: bool = True
    enable_recovery: bool = True
    
    # Scheduler config
    scheduler_interval: float = 0.1
    
    # Pipeline config
    pipeline_timeout: float = 30.0
    pipeline_continue_on_error: bool = False
    
    # Registry config
    registry_max_events: int = 10000
    
    # Custom config
    extra: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if self.max_concurrent_events <= 0:
            raise ValueError("max_concurrent_events must be positive")
        if self.execution_timeout <= 0:
            raise ValueError("execution_timeout must be positive")
        if self.scheduler_interval <= 0:
            raise ValueError("scheduler_interval must be positive")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_concurrent_events": self.max_concurrent_events,
            "execution_timeout": self.execution_timeout,
            "enable_metrics": self.enable_metrics,
            "enable_persistence": self.enable_persistence,
            "enable_recovery": self.enable_recovery,
            "scheduler_interval": self.scheduler_interval,
            "pipeline_timeout": self.pipeline_timeout,
            "pipeline_continue_on_error": self.pipeline_continue_on_error,
            "registry_max_events": self.registry_max_events,
            **self.extra,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineConfig:
        """Create from dictionary."""
        known_keys = {
            "max_concurrent_events",
            "execution_timeout",
            "enable_metrics",
            "enable_persistence",
            "enable_recovery",
            "scheduler_interval",
            "pipeline_timeout",
            "pipeline_continue_on_error",
            "registry_max_events",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        known = {k: v for k, v in data.items() if k in known_keys}
        return cls(**known, extra=extra)


@dataclass(frozen=True, slots=True)
class EngineStats:
    """Engine statistics snapshot."""
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    rejected: int = 0
    active_events: int = 0
    queued_events: int = 0
    avg_processing_time_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "rejected": self.rejected,
            "active_events": self.active_events,
            "queued_events": self.queued_events,
            "avg_processing_time_ms": self.avg_processing_time_ms,
        }