"""
EVRECONSE Notification - Retry Policy.

Configurable retry policies with exponential backoff and jitter.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .exceptions import RetryPolicyError


class RetryStrategy(str, Enum):
    """Retry strategy type."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"


@dataclass(frozen=True, slots=True)
class RetryPolicyConfig:
    """
    Configuration for retry policy.
    
    Attributes:
        max_attempts: Maximum number of attempts (0 = unlimited)
        strategy: Retry strategy type
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        multiplier: Multiplier for exponential/linear backoff
        jitter: Jitter factor (0.0 to 1.0)
        jitter_type: "full" (full jitter) or "decorrelated" (decorrelated jitter)
        retryable_exceptions: Tuple of exception types to retry
        non_retryable_exceptions: Tuple of exception types to never retry
        timeout: Total timeout for all attempts (0 = no timeout)
    """
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1
    jitter_type: str = "full"  # "full" or "decorrelated"
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    non_retryable_exceptions: tuple[type[Exception], ...] = ()
    timeout: float = 0.0  # 0 = no timeout

    def __post_init__(self) -> None:
        if self.max_attempts < 0:
            raise ValueError("max_attempts cannot be negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be >= 1.0")
        if not 0.0 <= self.jitter <= 1.0:
            raise ValueError("jitter must be between 0.0 and 1.0")
        if self.jitter_type not in ("full", "decorrelated"):
            raise ValueError("jitter_type must be 'full' or 'decorrelated'")


class RetryPolicy:
    """
    Configurable retry policy with exponential backoff and jitter.
    
    Supports multiple backoff strategies and jitter types.
    """
    
    def __init__(self, config: RetryPolicyConfig | None = None) -> None:
        self._config = config or RetryPolicyConfig()
        self._last_delay = self._config.base_delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """
        Determine if an operation should be retried.
        
        Args:
            attempt: Current attempt number (0-indexed)
            exception: The exception that was raised
            
        Returns:
            True if should retry, False otherwise
        """
        # Check max attempts
        if self._config.max_attempts > 0 and attempt >= self._config.max_attempts:
            return False
        
        # Check non-retryable exceptions
        for exc_type in self._config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check retryable exceptions
        if self._config.retryable_exceptions:
            for exc_type in self._config.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True
            return False
        
        return True

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds before next attempt
        """
        if attempt == 0 or self._config.strategy == RetryStrategy.FIXED:
            delay = self._config.base_delay
        elif self._config.strategy == RetryStrategy.LINEAR:
            delay = self._config.base_delay * (attempt + 1)
        elif self._config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self._config.base_delay * (self._config.multiplier ** attempt)
        elif self._config.strategy == RetryStrategy.FIBONACCI:
            delay = self._config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self._config.base_delay

        # Apply max delay cap
        delay = min(delay, self._config.max_delay)

        # Apply jitter
        if self._config.jitter > 0:
            jitter_range = delay * self._config.jitter
            if self._config.jitter_type == "full":
                delay = random.uniform(0, delay)
            elif self._config.jitter_type == "decorrelated":
                delay = random.uniform(self._config.base_delay, delay * 3)

        return max(0, delay)

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    def get_next_delay(self, attempt: int) -> float:
        """
        Get delay for next attempt and update internal state.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.get_delay(attempt)
        self._last_delay = delay
        return delay

    def reset(self) -> None:
        """Reset internal state."""
        self._last_delay = self._config.base_delay

    def get_stats(self) -> dict[str, Any]:
        """Get policy statistics."""
        return {
            "strategy": self._config.strategy.value,
            "base_delay": self._config.base_delay,
            "max_delay": self._config.max_delay,
            "multiplier": self._config.multiplier,
            "jitter": self._config.jitter,
            "jitter_type": self._config.jitter_type,
            "max_attempts": self._config.max_attempts,
            "timeout": self._config.timeout,
        }


class RetryExecutor:
    """
    Executes a function with retry logic.
    """
    
    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy
    
    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        attempt = 0
        start_time = time.monotonic()
        last_exception = None

        while True:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self._policy.should_retry(attempt, e):
                    raise
                
                delay = self._policy.get_delay(attempt)
                
                # Check timeout
                if self._config.timeout > 0:
                    elapsed = time.monotonic() - start_time
                    if elapsed + delay > self._config.timeout:
                        raise RetryPolicyError(
                            f"Retry timeout exceeded ({self._config.timeout}s)"
                        ) from e
                
                await asyncio.sleep(delay)
                attempt += 1

        # Should not reach here, but just in case
        raise last_exception from last_exception

    def execute_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute synchronous function with retry logic.
        
        Args:
            func: Synchronous function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        attempt = 0
        start_time = time.monotonic()
        last_exception = None

        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self._policy.should_retry(attempt, e):
                    raise

                delay = self._policy.get_delay(attempt)

                # Check timeout
                if self._config.timeout > 0:
                    elapsed = time.monotonic() - start_time
                    if elapsed + delay > self._config.timeout:
                        raise RetryPolicyError(
                            f"Retry timeout exceeded ({self._config.timeout}s)"
                        ) from e

                time.sleep(delay)
                attempt += 1