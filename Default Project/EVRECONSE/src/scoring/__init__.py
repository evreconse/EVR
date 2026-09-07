"""
EVRECONSE Scoring Module.

Scoring engine, parameter registry, and parameter implementations.
"""

from .context import (
    DataProviderProtocol,
    Penalty,
    ScoreContribution,
    ScoringConfig,
    ScoringContext,
    ScoringResult,
    StorageProtocol,
)
from .exceptions import (
    ParameterAlreadyRegisteredError,
    ParameterNotFoundError,
    ParameterNotRegisteredError,
    ScoringComputationError,
    ScoringConfigurationError,
    ScoringContextError,
    ScoringError,
    ScoringValidationError,
)
from .parameter import ScoringParameter
from .parameters import (
    CandleConfirmationScore,
    LiquidationStrengthScore,
    LowerWickQualityScore,
)
from .registry import ScoringParameterRegistry, get_registry, reset_registry
from .scoring_engine import ScoringEngine, ScoringEngineConfig

__all__ = [
    # Context
    "ScoringContext",
    "ScoringConfig",
    "ScoringResult",
    "ScoreContribution",
    "Penalty",
    "DataProviderProtocol",
    "StorageProtocol",
    # Core
    "ScoringParameter",
    "ScoringEngine",
    "ScoringEngineConfig",
    "ScoringParameterRegistry",
    "get_registry",
    "reset_registry",
    # Implementations
    "LowerWickQualityScore",
    "LiquidationStrengthScore",
    "CandleConfirmationScore",
    # Exceptions
    "ScoringError",
    "ScoringValidationError",
    "ScoringConfigurationError",
    "ScoringComputationError",
    "ParameterNotFoundError",
    "ParameterAlreadyRegisteredError",
    "ParameterNotRegisteredError",
    "ScoringContextError",
]