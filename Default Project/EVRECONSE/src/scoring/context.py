"""
EVRECONSE Scoring - Context and Result.

ScoringContext: Immutable context passed to parameters for evaluation.
ScoringResult: Immutable result returned by parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from models import MarketEvent


@dataclass(frozen=True, slots=True)
class ScoringContext:
    """
    Immutable context passed to scoring parameters for evaluation.

    Contains all data needed for parameter evaluation without
    exposing internal system components.
    """

    # Event data
    market_event: MarketEvent
    
    # Configuration
    config: ScoringConfig
    
    # External dependencies (interfaces only)
    data_provider: DataProviderProtocol
    storage: StorageProtocol
    
    # Metadata
    evaluation_id: UUID = field(default_factory=lambda: uuid4())
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """
    Scoring configuration.
    
    Immutable configuration for scoring parameters.
    """

    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    min_confidence_score: float = 80.0
    scoring_id: str = ""
    version: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration parameter."""
        return self.parameters.get(key, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float parameter."""
        value = self.parameters.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer parameter."""
        value = self.parameters.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean parameter."""
        value = self.parameters.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)


@dataclass(frozen=True, slots=True)
class ScoreContribution:
    """Individual score component with explanation."""

    parameter_id: str
    score: float
    max_score: float
    explanation: str
    weight: float = 1.0

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    @property
    def ratio(self) -> float:
        if self.max_score == 0:
            return 0.0
        return self.score / self.max_score


@dataclass(frozen=True, slots=True)
class Penalty:
    """Penalty applied to score."""

    reason: str
    points: float
    parameter_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """
    Immutable result of scoring evaluation.

    Contains all information about the evaluation outcome
    without any business logic.
    """

    # Core result
    qualified: bool
    final_score: float
    max_score: float
    
    # Details
    contributions: tuple[ScoreContribution, ...] = field(default_factory=tuple)
    penalties: tuple[Penalty, ...] = field(default_factory=tuple)
    
    # Metadata
    scoring_id: str = ""
    scoring_version: str = ""
    evaluation_id: UUID = field(default_factory=lambda: uuid4())
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    execution_time_ms: float = 0.0
    
    # Explanation
    explanation: str = ""
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def score_ratio(self) -> float:
        """Score as ratio of max possible score."""
        if self.max_score == 0:
            return 0.0
        return self.final_score / self.max_score

    @property
    def total_penalty(self) -> float:
        """Total penalty points applied."""
        return sum(p.points for p in self.penalties)

    @property
    def has_penalties(self) -> bool:
        return len(self.penalties) > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "qualified": self.qualified,
            "final_score": self.final_score,
            "max_score": self.max_score,
            "score_ratio": self.score_ratio,
            "total_penalty": self.total_penalty,
            "scoring_id": self.scoring_id,
            "scoring_version": self.scoring_version,
            "evaluation_id": str(self.evaluation_id),
            "evaluated_at": self.evaluated_at.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "explanation": self.explanation,
            "contributions": [
                {
                    "parameter_id": c.parameter_id,
                    "score": c.score,
                    "max_score": c.max_score,
                    "ratio": c.ratio,
                    "explanation": c.explanation,
                    "weight": c.weight,
                }
                for c in self.contributions
            ],
            "penalties": [
                {
                    "reason": p.reason,
                    "points": p.points,
                    "parameter_id": p.parameter_id,
                }
                for p in self.penalties
            ],
            "metadata": self.metadata,
        }


# Protocols for external dependencies (avoid circular imports)
from dataclasses import dataclass, field


class DataProviderProtocol(Protocol):
    """Protocol for data provider access."""
    
    async def get_snapshot(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        ...
    
    async def get_liquidations(self, symbol: str, limit: int) -> list[dict]:
        ...


class StorageProtocol(Protocol):
    """Protocol for storage access."""
    
    async def save_event(self, event: Any) -> None:
        ...
    
    async def get_events(self, symbol: str, start: datetime, end: datetime) -> list:
        ...
