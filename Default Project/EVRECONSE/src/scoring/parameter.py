"""
EVRECONSE Scoring - Parameter Interface.

Abstract interface that all scoring parameters must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .context import ScoringConfig, ScoringContext


class ScoringParameter(ABC):
    """
    Abstract base class for all scoring parameters.
    
    Each parameter is a self-contained evaluator that computes
    a single score component from the scoring context.
    """

    @property
    @abstractmethod
    def parameter_id(self) -> str:
        """Unique identifier for this parameter (e.g., 'lower_wick_quality')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the parameter."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Parameter version (semver)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this parameter evaluates."""
        ...

    @property
    @abstractmethod
    def max_score(self) -> float:
        """Maximum possible score this parameter can contribute."""
        ...

    @property
    @abstractmethod
    def weight(self) -> float:
        """Weight of this parameter in final score (0.0 to 1.0)."""
        ...

    @property
    @abstractmethod
    def min_score(self) -> float:
        """Minimum possible score (usually 0.0)."""
        ...

    @abstractmethod
    def supports(self, context: ScoringContext) -> bool:
        """
        Check if this parameter can evaluate the given context.
        
        Called before evaluate() to quickly filter incompatible parameters.
        
        Args:
            context: Scoring context to check
            
        Returns:
            True if parameter can evaluate this context
        """
        ...

    @abstractmethod
    def validate_config(self, config: ScoringConfig) -> None:
        """
        Validate parameter-specific configuration.
        
        Called during registration and when config is updated.
        
        Args:
            config: Scoring configuration to validate
            
        Raises:
            ScoringValidationError: If configuration is invalid
        """
        ...

    @abstractmethod
    async def evaluate(self, context: ScoringContext) -> tuple[float, list[Any], str]:
        """
        Evaluate this parameter against the context.
        
        This is the core computation method. Must be pure and
        have no side effects on the parameter instance.
        
        Args:
            context: Immutable evaluation context
            
        Returns:
            Tuple of (score, penalties, explanation)
            
        Returns:
            Tuple of (score, penalties, explanation)
            
        Raises:
            ScoringComputationError: If evaluation fails
        """
        ...

    def initialize(self, config: ScoringConfig) -> None:
        """
        Initialize parameter with configuration.
        
        Called once after registration. Override for one-time setup.
        
        Args:
            config: Scoring configuration
        """

    async def shutdown(self) -> None:
        """
        Cleanup resources.
        
        Called when parameter is unregistered or system shuts down.
        Default implementation does nothing.
        """

    def get_metadata(self) -> dict[str, Any]:
        """Get parameter metadata for registration."""
        return {
            "parameter_id": self.parameter_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "max_score": self.max_score,
            "weight": self.weight,
            "min_score": self.min_score,
        }