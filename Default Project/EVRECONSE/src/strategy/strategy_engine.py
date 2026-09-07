"""
EVRECONSE Strategy - Strategy Engine.

Engine for managing and executing strategies.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models import MarketEvent
from .exceptions import (
    StrategyAlreadyRegisteredError,
    StrategyExecutionError,
    StrategyInitializationError,
    StrategyNotFoundError,
    StrategyNotRegisteredError,
)


@dataclass(frozen=True, slots=True)
class StrategyEngineConfig:
    """Configuration for the Strategy Engine."""
    
    max_concurrent_strategies: int = 10
    execution_timeout: float = 5.0  # seconds
    enable_metrics: bool = True


@dataclass(frozen=True, slots=True)
class StrategyExecutionContext:
    """Context passed to strategy execution."""
    
    event_id: str
    timestamp: datetime
    provider: str
    config: dict[str, Any]


class StrategyEngine:
    """
    Engine for managing and executing strategies.
    
    Responsibilities:
    - Strategy registration and lifecycle
    - Event routing to strategies
    - Execution with timeout and error handling
    - Metrics collection
    """
    
    def __init__(
        self,
        config: StrategyEngineConfig | None = None,
        data_provider: Any = None,
        config_manager: Any = None,
    ) -> None:
        self._config = config or StrategyEngineConfig()
        self._data_provider = data_provider
        self._config_manager = config_manager
        
        self._strategies: dict[str, Any] = {}  # Strategy instances
        self._strategy_configs: dict[str, Any] = {}
        self._active_strategies: set[str] = set()
        self._lock = threading.RLock()
        
        # Metrics
        self._execution_count = 0
        self._error_count = 0
        self._total_execution_time = 0.0
    
    def register_strategy(self, strategy: Any, config: Any | None = None) -> None:
        """
        Register a strategy with the engine.
        
        Args:
            strategy: Strategy instance to register
            config: Optional strategy configuration
            
        Raises:
            StrategyAlreadyRegisteredError: If strategy ID already registered
            StrategyInitializationError: If strategy initialization fails
        """
        with self._lock:
            strategy_id = strategy.strategy_id
            
            if strategy_id in self._strategies:
                raise StrategyAlreadyRegisteredError(f"Strategy {strategy_id} already registered")
            
            # Store strategy and config
            self._strategies[strategy_id] = strategy
            self._strategy_configs[strategy_id] = config or {}
            
            # Initialize strategy
            try:
                strategy.initialize(config or {})
            except Exception as e:
                self._strategies.pop(strategy_id, None)
                raise StrategyInitializationError(f"Failed to initialize strategy {strategy.strategy_id}: {e}") from e
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """
        Unregister a strategy.
        
        Args:
            strategy_id: Strategy identifier
            
        Raises:
            StrategyNotRegisteredError: If strategy not found
        """
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotRegisteredError(f"Strategy {strategy_id} not registered")
            
            strategy = self._strategies.pop(strategy_id)
            self._strategy_configs.pop(strategy_id, None)
            self._active_strategies.discard(strategy_id)
            
            # Cleanup
            import asyncio
            try:
                asyncio.run(strategy.shutdown())
            except Exception:
                pass  # Ignore shutdown errors
    
    def get_strategy(self, strategy_id: str) -> Any:
        """Get strategy by ID."""
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")
            return self._strategies[strategy_id]
    
    def list_strategies(self) -> list[str]:
        """List all registered strategy IDs."""
        with self._lock:
            return list(self._strategies.keys())
    
    def is_active(self, strategy_id: str) -> bool:
        """Check if strategy is active."""
        with self._lock:
            return strategy_id in self._active_strategies
    
    def activate_strategy(self, strategy_id: str) -> None:
        """Activate a strategy for event processing."""
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")
            self._active_strategies.add(strategy_id)
    
    def deactivate_strategy(self, strategy_id: str) -> None:
        """Deactivate a strategy."""
        with self._lock:
            self._active_strategies.discard(strategy_id)
    
    async def process_event(self, event: MarketEvent) -> list[Any]:
        """
        Process event through all active strategies.
        
        Args:
            event: Market event to process
            
        Returns:
            List of strategy results
        """
        start_time = time.monotonic()
        results = []
        
        with self._lock:
            active_strategies = [
                self._strategies[sid] for sid in self._active_strategies
                if sid in self._strategies
            ]
        
        print(f"DEBUG ENGINE: process_event called, active_strategies={len(active_strategies)}")
        
        if not active_strategies:
            return results
        
        # Execute strategies concurrently with timeout
        tasks = []
        for strategy in active_strategies:
            task = asyncio.create_task(self._execute_strategy(strategy, event))
            tasks.append((strategy.strategy_id, task))
        
        # Wait for all with timeout
        done, pending = await asyncio.wait(
            [task for _, task in tasks],
            timeout=self._config.execution_timeout,
            return_when=asyncio.ALL_COMPLETED
        )
        
        # Cancel pending
        for task in pending:
            task.cancel()
        
        # Collect results
        for strategy_id, task in tasks:
            try:
                if task in done:
                    result = task.result()
                    if result:
                        results.append(result)
            except asyncio.CancelledError:
                pass  # Timeout
            except Exception:
                # Log error but continue
                pass
        
        # Update metrics
        elapsed = time.monotonic() - start_time
        self._execution_count += 1
        self._total_execution_time += elapsed
        self._error_count += len(pending)  # Count timeouts as errors
        
        print(f"DEBUG ENGINE: process_event completed, results={len(results)}")
        return results
    
    async def _execute_strategy(self, strategy: Any, event: MarketEvent) -> Any:
        """Execute single strategy with error handling."""
        try:
            # Create StrategyContext for evaluation with proper config
            from .context import StrategyContext, StrategyConfig
            strategy_id = strategy.strategy_id
            # Get the stored config for this strategy
            strategy_config = self._strategy_configs.get(strategy_id, {})
            # Handle both dict and StrategyConfigData
            if hasattr(strategy_config, 'parameters'):
                params = strategy_config.parameters
            elif isinstance(strategy_config, dict):
                params = strategy_config.get("parameters", {})
            else:
                params = {}
            print(f"DEBUG ENGINE: strategy={strategy_id}, params={params}")
            config = StrategyConfig(
                strategy_id=strategy_id,
                version="1.0.0",
                parameters=params,
                enabled=True,
            )
            context = StrategyContext(
                market_event=event,
                config=config,
                data_provider=self._data_provider,
                config_manager=self._config_manager,
            )
            print(f"DEBUG ENGINE: calling strategy.evaluate for {strategy_id}")
            return await asyncio.wait_for(
                strategy.evaluate(context),
                timeout=self._config.execution_timeout
            )
        except TimeoutError:
            raise StrategyExecutionError("Strategy execution timeout")
        except Exception as e:
            print(f"DEBUG ENGINE: Exception in _execute_strategy: {e}")
            raise StrategyExecutionError(f"Strategy execution failed: {e}") from e
    
    def get_metrics(self) -> dict[str, Any]:
        """Get engine metrics."""
        with self._lock:
            return {
                "registered_strategies": len(self._strategies),
                "active_strategies": len(self._active_strategies),
                "total_executions": self._execution_count,
                "total_errors": self._error_count,
                "avg_execution_time": (
                    self._total_execution_time / self._execution_count
                    if self._execution_count > 0 else 0
                ),
            }