"""
EVRECONSE Notification - Rate Limiter.

Thread-safe rate limiter with sliding window algorithm.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Rate limit configuration."""
    
    requests_per_second: float = 10.0
    requests_per_minute: float | None = None
    requests_per_hour: float | None = None
    burst_allowance: int = 5

    def __post_init__(self) -> None:
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.requests_per_minute is not None and self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.requests_per_hour is not None and self.requests_per_hour <= 0:
            raise ValueError("requests_per_hour must be positive")
        if self.burst_allowance < 0:
            raise ValueError("burst_allowance cannot be negative")


class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Supports multiple time windows (second, minute, hour) with burst allowance.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()

        # Sliding windows for each time unit
        self._second_window: deque[float] = deque()
        self._minute_window: deque[float] = deque() if config.requests_per_minute else None
        self._hour_window: deque[float] = deque() if config.requests_per_hour else None

        # Burst tracking
        self._burst_used = 0
        self._burst_reset_time = time.monotonic()

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire permission to make requests.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Returns:
            Time waited in seconds (0 if immediately allowed)
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        async with self._lock:
            now = time.monotonic()

            # Clean expired entries
            self._clean_windows(now)

            # Check burst allowance
            if self._config.burst_allowance > 0:
                if now - self._burst_reset_time >= 1.0:
                    self._burst_used = 0
                    self._burst_reset_time = now

                if self._burst_used + tokens <= self._config.burst_allowance:
                    self._burst_used += tokens
                    return 0.0

            # Check rate limits
            wait_time = self._calculate_wait_time(now, tokens)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = time.monotonic()
                self._clean_windows(now)

            # Record request
            now = time.monotonic()
            self._second_window.append(now)
            if self._minute_window is not None:
                self._minute_window.append(now)
            if self._hour_window is not None:
                self._hour_window.append(now)

            return max(0.0, self._calculate_wait_time(time.monotonic(), 0))

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False if rate limited
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        now = time.monotonic()
        self._clean_windows(now)

        # Check burst allowance
        if self._config.burst_allowance > 0:
            if now - self._burst_reset_time >= 1.0:
                self._burst_used = 0
                self._burst_reset_time = now

            if self._burst_used + tokens <= self._config.burst_allowance:
                self._burst_used += tokens
                return True

        # Check rate limits
        if not self._check_limits(now, tokens):
            return False

        # Record request
        self._second_window.append(now)
        if self._minute_window is not None:
            self._minute_window.append(now)
        if self._hour_window is not None:
            self._hour_window.append(now)

        return True

    def _clean_windows(self, now: float) -> None:
        """Remove expired entries from sliding windows."""
        # Second window (keep last 1 second)
        while self._second_window and self._second_window[0] <= now - 1.0:
            self._second_window.popleft()

        # Minute window (keep last 60 seconds)
        if self._minute_window:
            while self._minute_window and self._minute_window[0] <= now - 60.0:
                self._minute_window.popleft()

        # Hour window (keep last 3600 seconds)
        if self._hour_window:
            while self._hour_window and self._hour_window[0] <= now - 3600.0:
                self._hour_window.popleft()

        # Reset burst counter every second
        if now - self._burst_reset_time >= 1.0:
            self._burst_used = 0
            self._burst_reset_time = now

    def _check_limits(self, now: float, tokens: int) -> bool:
        """Check if request would exceed rate limits."""
        # Second limit
        if len(self._second_window) + tokens > self._config.requests_per_second:
            return False

        # Minute limit
        if self._minute_window and self._config.requests_per_minute:
            max_per_minute = int(self._config.requests_per_minute)
            if len(self._minute_window) + tokens > max_per_minute:
                return False

        # Hour limit
        if self._hour_window and self._config.requests_per_hour:
            max_per_hour = int(self._config.requests_per_hour)
            if len(self._hour_window) + tokens > max_per_hour:
                return False

        return True

    def _calculate_wait_time(self, now: float, tokens: int) -> float:
        """Calculate time to wait before request can proceed."""
        wait_times = []

        # Second window
        if len(self._second_window) >= self._config.requests_per_second:
            if self._second_window:
                wait = self._second_window[0] + 1.0 - now
                if wait > 0:
                    wait_times.append(wait)

        # Minute window
        if self._minute_window and self._config.requests_per_minute:
            max_per_minute = int(self._config.requests_per_minute)
            if len(self._minute_window) + tokens > max_per_minute:
                if self._minute_window:
                    wait = self._minute_window[0] + 60.0 - now
                    if wait > 0:
                        wait_times.append(wait)

        # Hour window
        if self._hour_window and self._config.requests_per_hour:
            max_per_hour = int(self._config.requests_per_hour)
            if len(self._hour_window) + tokens > max_per_hour:
                if self._hour_window:
                    wait = self._hour_window[0] + 3600.0 - now
                    if wait > 0:
                        wait_times.append(wait)

        return max(wait_times) if wait_times else 0.0

    def _check_limits(self, now: float, tokens: int) -> bool:
        """Check if request would exceed any limits."""
        # Second limit
        if len(self._second_window) + tokens > self._config.requests_per_second:
            return False

        # Minute limit
        if self._minute_window and self._config.requests_per_minute:
            max_per_minute = int(self._config.requests_per_minute)
            if len(self._minute_window) + tokens > max_per_minute:
                return False

        # Hour limit
        if self._hour_window and self._config.requests_per_hour:
            max_per_hour = int(self._config.requests_per_hour)
            if len(self._hour_window) + tokens > max_per_hour:
                return False

        return True

    async def release(self, tokens: int = 1) -> None:
        """Release tokens back to the pool (for cancelled operations)."""
        async with self._lock:
            self._burst_used = max(0, self._burst_used - tokens)

    def get_current_usage(self) -> dict[str, Any]:
        """Get current usage statistics."""
        now = time.monotonic()
        self._clean_windows(now)

        return {
            "second": {
                "used": len(self._second_window),
                "limit": self._config.requests_per_second,
            },
            "minute": {
                "used": len(self._minute_window) if self._minute_window else 0,
                "limit": self._config.requests_per_minute,
            },
            "hour": {
                "used": len(self._hour_window) if self._hour_window else 0,
                "limit": self._config.requests_per_hour,
            },
            "burst": {
                "used": self._burst_used,
                "limit": self._config.burst_allowance,
            },
        }


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for smoother rate limiting.
    
    Allows burst traffic up to bucket capacity, then limits to refill rate.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time waited in seconds
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self._capacity:
            raise ValueError(f"tokens ({tokens}) exceeds capacity ({self._capacity})")

        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return 0.0
                # Wait for tokens to refill
                needed = tokens - self._tokens
                wait_time = needed / self._refill_rate
                await asyncio.sleep(wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking."""
        if tokens <= 0:
            return False
        if tokens > self._capacity:
            return False

        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._refill_rate
        self._tokens = min(self._capacity, self._tokens + new_tokens)
        self._last_refill = now

    def get_available_tokens(self) -> float:
        """Get current available tokens (without acquiring)."""
        self._refill()
        return self._tokens

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def refill_rate(self) -> float:
        return self._refill_rate