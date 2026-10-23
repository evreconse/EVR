"""
EVRECONSE Strategy Layer.

Strategy management, execution engine, and LW-001 implementation.
"""

from .context import (
    DataProviderProtocol,
    Penalty,
    ScoreContribution,
    StorageProtocol,
    StrategyConfig,
    StrategyContext,
    StrategyResult,
)
from .exceptions import (
    StrategyAlreadyRegisteredError,
    StrategyConfigurationError,
    StrategyContextError,
    StrategyError,
    StrategyExecutionError,
    StrategyNotFoundError,
    StrategyNotRegisteredError,
    StrategyRegistrationError,
    StrategyValidationError,
)
from .lw_001 import LW001Strategy
from .registry import StrategyRegistry
from .strategy import Strategy
from .strategy_engine import StrategyEngine, StrategyEngineConfig, StrategyExecutionContext

__all__ = [
    # Exceptions
    "StrategyError",
    "StrategyRegistrationError",
    "StrategyNotFoundError",
    "StrategyAlreadyRegisteredError",
    "StrategyNotRegisteredError",
    "StrategyValidationError",
    "StrategyConfigurationError",
    "StrategyExecutionError",
    "StrategyContextError",
    # Context & Results
    "StrategyContext",
    "StrategyConfig",
    "StrategyResult",
    "ScoreContribution",
    "Penalty",
    "DataProviderProtocol",
    "StorageProtocol",
    # Core
    "Strategy",
    "StrategyEngine",
    "StrategyEngineConfig",
    "StrategyExecutionContext",
    "StrategyRegistry",
    # Implementations
    "LW001Strategy",
]