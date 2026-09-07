"""
EVRECONSE Strategy - Registry.

Thread-safe strategy registry with registration, lookup, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from .context import StrategyConfig
from .exceptions import (
    StrategyAlreadyRegisteredError,
    StrategyNotFoundError,
    StrategyNotRegisteredError,
    StrategyRegistrationError,
)
from .strategy import Strategy


@dataclass(frozen=True, slots=True)
class StrategyRegistration:
    """Immutable strategy registration record."""
    strategy_id: str
    name: str
    version: str
    strategy_class: type
    config: StrategyConfig
    registered_at: str
    enabled: bool = True


class StrategyRegistry:
    """
    Thread-safe strategy registry.
    
    Manages registration, lookup, and lifecycle of strategies.
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._strategies: dict[str, Strategy] = {}
        self._registrations: dict[str, StrategyRegistration] = {}
        self._enabled: set[str] = set()
    
    def register(
        self,
        strategy: Strategy,
        config: StrategyConfig,
    ) -> None:
        """
        Register a strategy.
        
        Args:
            strategy: Strategy instance to register
            config: Strategy configuration
            
        Raises:
            StrategyAlreadyRegisteredError: If strategy ID already registered
            StrategyRegistrationError: If validation fails
        """
        with self._lock:
            strategy_id = strategy.strategy_id
            
            if strategy_id in self._strategies:
                raise StrategyAlreadyRegisteredError(strategy_id)
            
            # Validate strategy
            try:
                strategy.validate_config(config)
            except Exception as e:
                raise StrategyRegistrationError(
                    f"Strategy validation failed: {e}",
                    strategy_id=strategy_id
                ) from e
            
            # Initialize strategy
            strategy.initialize(config)
            
            # Store strategy and registration
            self._strategies[strategy_id] = strategy
            self._registrations[strategy_id] = StrategyRegistration(
                strategy_id=strategy.strategy_id,
                name=strategy.name,
                version=strategy.version,
                strategy_class=type(strategy),
                config=config,
                registered_at=datetime.now(UTC).isoformat(),
                enabled=config.enabled,
            )
            
            if config.enabled:
                self._enabled.add(strategy_id)
    
    def unregister(self, strategy_id: str) -> None:
        """
        Unregister a strategy.
        
        Args:
            strategy_id: Strategy identifier
            
        Raises:
            StrategyNotRegisteredError: If strategy not found
        """
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotRegisteredError(strategy_id)
            
            strategy = self._strategies[strategy_id]
            
            # Shutdown strategy
            try:
                asyncio.run(strategy.shutdown())
            except Exception:
                pass  # Best effort
            
            # Remove from registry
            del self._strategies[strategy_id]
            del self._registrations[strategy_id]
            self._enabled.discard(strategy_id)
    
    def get(self, strategy_id: str) -> Strategy:
        """
        Get strategy by ID.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy instance
            
        Raises:
            StrategyNotFoundError: If strategy not found
        """
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(strategy_id)
            return self._strategies[strategy_id]
    
    def get_registration(self, strategy_id: str) -> StrategyRegistration:
        """
        Get strategy registration info.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Registration record
            
        Raises:
            StrategyNotFoundError: If strategy not found
        """
        with self._lock:
            if strategy_id not in self._registrations:
                raise StrategyNotFoundError(strategy_id)
            return self._registrations[strategy_id]
    
    def list_strategies(self, enabled_only: bool = False) -> list[StrategyRegistration]:
        """
        List all registered strategies.
        
        Args:
            enabled_only: If True, only return enabled strategies
            
        Returns:
            List of strategy registrations
        """
        with self._lock:
            registrations = list(self._registrations.values())
            if enabled_only:
                return [r for r in registrations if r.enabled]
            return registrations
    
    def get_enabled(self) -> list[str]:
        """Get list of enabled strategy IDs."""
        with self._lock:
            return list(self._enabled)
    
    def enable(self, strategy_id: str) -> None:
        """Enable a strategy."""
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(strategy_id)
            
            self._enabled.add(strategy_id)
            registration = self._registrations[strategy_id]
            self._registrations[strategy_id] = registration._replace(enabled=True)
            
            # Re-initialize with updated config
            strategy = self._strategies[strategy_id]
            config = self._get_config(strategy_id)
            if config:
                from dataclasses import replace
                new_config = replace(config, enabled=True)
                strategy.initialize(new_config)
    
    def disable(self, strategy_id: str) -> None:
        """Disable a strategy."""
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(strategy_id)
            
            self._enabled.discard(strategy_id)
            registration = self._registrations[strategy_id]
            self._registrations[strategy_id] = registration._replace(enabled=False)
            
            # Could also update config if needed
    
    def is_enabled(self, strategy_id: str) -> bool:
        """Check if strategy is enabled."""
        with self._lock:
            return strategy_id in self._enabled
    
    def get_strategy_config(self, strategy_id: str) -> StrategyConfig | None:
        """Get strategy configuration."""
        with self._lock:
            registration = self._registrations.get(strategy_id)
            return registration.config if registration else None
    
    def update_config(self, strategy_id: str, config: StrategyConfig) -> None:
        """Update strategy configuration."""
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(strategy_id)
            
            strategy = self._strategies[strategy_id]
            
            # Validate new config
            strategy.validate_config(config)
            
            # Update registration
            registration = self._registrations[strategy_id]
            self._registrations[strategy_id] = registration._replace(
                config=config,
                enabled=config.enabled,
            )
            
            # Re-initialize strategy
            strategy.initialize(config)
            
            # Update enabled set
            if config.enabled:
                self._enabled.add(config.strategy_id)
            else:
                self._enabled.discard(config.strategy_id)
    
    def get_all_strategies(self) -> list[Strategy]:
        """Get all registered strategies."""
        with self._lock:
            return list(self._strategies.values())
    
    def get_enabled_strategies(self) -> list[Strategy]:
        """Get all enabled strategies."""
        with self._lock:
            return [self._strategies[sid] for sid in self._enabled]
    
    def clear(self) -> None:
        """Clear all strategies (for testing)."""
        with self._lock:
            for strategy in self._strategies.values():
                try:
                    strategy.shutdown()
                except Exception:
                    pass
            self._strategies.clear()
            self._registrations.clear()
            self._enabled.clear()


# Singleton registry instance
_registry: StrategyRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> StrategyRegistry:
    """Get the global strategy registry singleton."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = StrategyRegistry()
        return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    with _registry_lock:
        if _registry is not None:
            _registry.clear()
            _registry = None