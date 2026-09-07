"""
EVRECONSE Strategy - Strategy Interface.

Abstract interface that all strategies must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .context import StrategyConfig, StrategyContext, StrategyResult


class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Strategies are stateless evaluators that receive a StrategyContext
    and return a StrategyResult. They must be pure functions with
    no internal state that affects evaluation.
    """

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique identifier for this strategy (e.g., 'LW-001')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the strategy."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy version (semver)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the strategy."""
        ...

    @property
    @abstractmethod
    def supported_markets(self) -> list[str]:
        """List of supported markets (e.g., ['bybit', 'binance'])."""
        ...

    @property
    @abstractmethod
    def supported_timeframes(self) -> list[str]:
        """List of supported timeframes (e.g., ['15m', '1h', '4h'])."""
        ...

    @abstractmethod
    def supports(self, context: StrategyContext) -> bool:
        """
        Check if this strategy can evaluate the given context.
        
        Called before evaluate() to quickly filter incompatible strategies.
        
        Args:
            context: Strategy context to check
            
        Returns:
            True if strategy can evaluate this context
        """
        ...

    @abstractmethod
    def validate_config(self, config: StrategyConfig) -> None:
        """
        Validate strategy-specific configuration.
        
        Called during registration and when config is updated.
        Should raise StrategyValidationError for invalid config.
        
        Args:
            config: Strategy configuration to validate
            
        Raises:
            StrategyValidationError: If configuration is invalid
        """
        ...

    @abstractmethod
    async def evaluate(self, context: StrategyContext) -> StrategyResult:
        """
        Evaluate the market event and return a strategy result.
        
        This is the core evaluation method. It must be pure and
        have no side effects on the strategy instance.
        
        Args:
            context: Immutable evaluation context
            
        Returns:
            StrategyResult with qualification decision and scoring
            
        Raises:
            StrategyExecutionError: If evaluation fails
        """
        ...

    def initialize(self, config: StrategyConfig) -> None:
        """
        Initialize strategy with configuration.
        
        Called once after registration. Override for one-time setup.
        Default implementation does nothing.
        
        Args:
            config: Strategy configuration
        """

    async def shutdown(self) -> None:
        """
        Cleanup resources.
        
        Called when strategy is unregistered or system shuts down.
        Default implementation does nothing.
        """

    def get_metadata(self) -> dict[str, Any]:
        """Get strategy metadata for registration."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "supported_markets": self.supported_markets,
            "supported_timeframes": self.supported_timeframes,
        }