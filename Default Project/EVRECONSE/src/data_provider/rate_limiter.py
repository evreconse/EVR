"""
EVRECONSE Data Provider - Rate Limiter.

Token bucket rate limiter with async support.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """
    Rate limiter configuration.

    Attributes:
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size (tokens available at once)
    """
    requests_per_second: float = 10.0
    burst_size: int = 20

    def __post_init__(self) -> None:
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst_size <= 0:
            raise ValueError("burst_size must be positive")


class RateLimiter:
    """
    Async-safe token bucket rate limiter.

    Uses a token bucket algorithm:
    - Tokens added at rate of requests_per_second
    - Bucket capacity = burst_size
    - Each request consumes 1 token
    - Requests wait if no tokens available
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._tokens = float(self._config.burst_size)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self._config.burst_size, self._tokens + elapsed * self._config.requests_per_second)
        self._last_update = now
        return self._tokens

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Raises:
            ValueError: If tokens > burst_size
        """
        if tokens > self._config.burst_size:
            raise ValueError(f"Cannot acquire {tokens} tokens, burst size is {self._config.burst_size}")

        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(self._config.burst_size, self._tokens + elapsed * self._config.requests_per_second)
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                # Calculate wait time
                needed = tokens - self._tokens
                wait_time = needed / self._config.requests_per_second
                await asyncio.sleep(wait_time)

    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise
        """
        if tokens > self._config.burst_size:
            return False

        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._config.burst_size, self._tokens + elapsed * self._config.requests_per_second)
            self._last_update = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def get_status(self) -> dict[str, Any]:
        """Get current rate limiter status."""
        return {
            "requests_per_second": self._config.requests_per_second,
            "burst_size": self._config.burst_size,
            "available_tokens": round(self.available_tokens, 2),
        }


class SyncRateLimiter:
    """
    Thread-safe synchronous rate limiter.

    For use in synchronous code paths.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._tokens = float(self._config.burst_size)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: float | None = None) -> bool:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if acquired, False if timeout
        """
        if tokens > self._config.burst_size:
            raise ValueError(f"Cannot acquire {tokens} tokens, burst size is {self._config.burst_size}")

        start = time.monotonic()
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(self._config.burst_size, self._tokens + elapsed * self._config.requests_per_second)
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            if timeout is not None and time.monotonic() - start >= timeout:
                return False

            # Wait for next token
            wait_time = 1.0 / self._config.requests_per_second
            time.sleep(min(wait_time, 0.1))

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting."""
        if tokens > self._config.burst_size:
            return False

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._config.burst_size, self._tokens + elapsed * self._config.requests_per_second)
            self._last_update = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def get_status(self) -> dict[str, Any]:
        """Get current status."""
        with self._lock:
            return {
                "requests_per_second": self._config.requests_per_second,
                "burst_size": self._config.burst_size,
                "available_tokens": round(self._tokens, 2),
            }