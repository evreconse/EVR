"""
EVRECONSE Data Provider - Reconnect Strategy.

Exponential backoff reconnection with jitter.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ReconnectConfig:
    """
    Reconnection configuration.

    Attributes:
        max_attempts: Maximum reconnection attempts (0 = unlimited)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_multiplier: Exponential backoff multiplier
        jitter: Jitter factor (0.0 - 1.0)
    """
    max_attempts: int = 0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.1

    def __post_init__(self) -> None:
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.backoff_multiplier <= 1.0:
            raise ValueError("backoff_multiplier must be > 1.0")
        if not 0.0 <= self.jitter <= 1.0:
            raise ValueError("jitter must be between 0.0 and 1.0")


class ReconnectStrategy:
    """
    Exponential backoff reconnection strategy with jitter.

    Features:
    - Configurable max attempts
    - Exponential backoff with cap
    - Random jitter to prevent thundering herd
    - Attempt tracking
    """

    def __init__(self, config: ReconnectConfig | None = None) -> None:
        self._config = config or ReconnectConfig()
        self._attempt = 0
        self._last_delay = 0.0
        self._lock: Any = None

    def get_delay(self, attempt: int | None = None) -> float:
        """
        Calculate delay for given attempt.

        Args:
            attempt: Attempt number (uses internal counter if None)

        Returns:
            Delay in seconds
        """
        if attempt is None:
            attempt = self._attempt

        # Exponential backoff
        delay = min(
            self._config.initial_delay * (self._config.backoff_multiplier ** attempt),
            self._config.max_delay,
        )

        # Add jitter
        if self._config.jitter > 0:
            jitter_range = delay * self._config.jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)

    def next_delay(self) -> float:
        """
        Get delay for next attempt and increment counter.

        Returns:
            Delay in seconds
        """
        delay = self.get_delay()
        self._attempt += 1
        self._last_delay = delay
        return delay

    def reset(self) -> None:
        """Reset attempt counter (call on successful connection)."""
        self._attempt = 0
        self._last_delay = 0.0

    def get_status(self) -> dict[str, Any]:
        """Get current strategy status."""
        return {
            "attempt": self._attempt,
            "last_delay": self._last_delay,
            "max_attempts": self._config.max_attempts,
            "initial_delay": self._config.initial_delay,
            "max_delay": self._config.max_delay,
            "backoff_multiplier": self._config.backoff_multiplier,
            "jitter": self._config.jitter,
        }

    def is_exhausted(self) -> bool:
        """Check if max attempts reached."""
        if self._config.max_attempts <= 0:
            return False
        return self._attempt >= self._config.max_attempts


class AsyncReconnectStrategy:
    """
    Async reconnect strategy with built-in sleep.

    Combines delay calculation with async waiting.
    """

    def __init__(self, config: ReconnectConfig | None = None) -> None:
        self._strategy = ReconnectStrategy(config)

    async def wait(self) -> float:
        """
        Wait for next reconnection attempt.

        Returns:
            Actual delay waited
        """
        delay = self._strategy.next_delay()
        await asyncio.sleep(delay)
        return delay

    def reset(self) -> None:
        self._strategy.reset()

    def get_status(self) -> dict[str, Any]:
        return self._strategy.get_status()

    def is_exhausted(self) -> bool:
        return self._strategy.is_exhausted()


class SyncReconnectStrategy:
    """
    Synchronous reconnect strategy with built-in sleep.

    For use in synchronous code paths.
    """

    def __init__(self, config: ReconnectConfig | None = None) -> None:
        self._strategy = ReconnectStrategy(config)

    def wait(self) -> float:
        """
        Wait for next reconnection attempt.

        Returns:
            Actual delay waited
        """
        delay = self._strategy.next_delay()
        time.sleep(delay)
        return delay

    def reset(self) -> None:
        self._strategy.reset()

    def get_status(self) -> dict[str, Any]:
        return self._strategy.get_status()

    def is_exhausted(self) -> bool:
        return self._strategy.is_exhausted()