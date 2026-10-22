# ruff: noqa
# mypy: ignore-errors
"""
BingX API Rate Limiter

Implements rate limiting for BingX API according to official limits:
- 500 requests per 10 seconds per IP for market data endpoints
- Uses sliding window algorithm for accurate limiting
"""
import asyncio
import time
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BingXRateLimiter:
    """
    Rate limiter for BingX API.

    Official limit: 500 requests per 10 seconds per IP for market data endpoints.
    We use a conservative limit of 450/10s to leave headroom.
    """

    def __init__(
        self,
        max_requests: int = 450,
        window_seconds: float = 10.0,
        safety_margin: float = 0.9
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window (default 450 for 500 limit with margin)
            window_seconds: Time window in seconds (default 10s per BingX docs)
            safety_margin: Additional safety factor (default 0.9 = 90% of limit).
                           Only applied when using default max_requests.
        """
        # Only apply safety margin if using default max_requests (450)
        # This allows explicit max_requests to be used without modification
        if max_requests == 450:
            self.max_requests = int(max_requests * safety_margin)
        else:
            self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = deque()
        self._lock = asyncio.Lock()
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._rate_limit_hits = 0

    async def acquire(self) -> float:
        """
        Acquire permission to make a request.

        Returns:
            Time waited in seconds (0 if no wait needed)
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            # Remove expired requests
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            if len(self._requests) < self.max_requests:
                # Room available, record request and proceed
                self._requests.append(now)
                self._total_requests += 1
                return 0.0

            # Need to wait until oldest request expires
            oldest = self._requests[0]
            wait_time = (oldest + self.window_seconds) - now

            if wait_time > 0:
                self._rate_limit_hits += 1
                self._total_wait_time += wait_time
                # Wait without holding lock
                pass
            else:
                wait_time = 0

        # Wait outside lock to avoid blocking other coroutines
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # Re-acquire lock to record the request
        async with self._lock:
            now = time.monotonic()
            self._requests.append(now)
            self._total_requests += 1

        return wait_time

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "total_wait_time_seconds": self._total_wait_time,
            "rate_limit_hits": self._rate_limit_hits,
            "current_queue_size": len(self._requests),
            "max_requests_per_window": self.max_requests,
            "window_seconds": self.window_seconds,
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._rate_limit_hits = 0


class BingXAPIError(Exception):
    """Base exception for BingX API errors."""
    def __init__(self, message: str, code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class BingXRateLimitError(BingXAPIError):
    """Rate limit error from BingX API."""
    def __init__(self, message: str = "Rate limit exceeded", code: int = 100401):
        super().__init__(message, code=code, retryable=True)


class BingXOfflineSymbolError(BingXAPIError):
    """Symbol is offline/delisted error."""
    def __init__(self, message: str, code: int = 100402):
        super().__init__(message, code=code, retryable=False)


def is_rate_limit_error(error: Exception) -> bool:
    """Check if error is a rate limit error from BingX."""
    if isinstance(error, BingXRateLimitError):
        return True
    msg = str(error).lower()
    return (
        "rate limit" in msg or
        "请稍后重试" in msg or
        "please try again later" in msg or
        "too many requests" in msg or
        "100401" in msg or
        "429" in msg
    )


def is_offline_symbol_error(error: Exception) -> bool:
    """Check if error indicates symbol is offline/delisted."""
    if isinstance(error, BingXOfflineSymbolError):
        return True
    msg = str(error).lower()
    return (
        "offline currently" in msg or
        "is offline" in msg or
        "delisted" in msg or
        "100402" in msg
    )


def classify_bingx_error(error: Exception) -> BingXAPIError:
    """Classify a generic error into a specific BingX error type."""
    if isinstance(error, BingXAPIError):
        return error

    msg = str(error)

    if is_rate_limit_error(error):
        return BingXRateLimitError(msg)

    if is_offline_symbol_error(error):
        return BingXOfflineSymbolError(msg)

    # Network/timeout errors are retryable
    if isinstance(error, (asyncio.TimeoutError, ConnectionError, OSError)):
        return BingXAPIError(msg, retryable=True)

    # Other errors are not retryable by default
    return BingXAPIError(msg, retryable=False)
