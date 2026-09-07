"""
EVRECONSE Notification - Heartbeat Monitor.

Heartbeat monitoring for notification services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class HeartbeatConfig:
    """Heartbeat monitor configuration."""

    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    max_missed: int = 3


class HeartbeatMonitor:
    """Heartbeat monitor for notification services."""

    def __init__(self, config: HeartbeatConfig | None = None) -> None:
        self._config = config or HeartbeatConfig()
        self._running = False
        self._last_beat: Optional[float] = None

    def start(self) -> None:
        """Start heartbeat monitoring."""
        self._running = True
        self._last_beat = 0.0

    def stop(self) -> None:
        """Stop heartbeat monitoring."""
        self._running = False

    def beat(self) -> None:
        """Record a heartbeat."""
        import time
        self._last_beat = time.monotonic()

    def is_healthy(self) -> bool:
        """Check if heartbeat is healthy."""
        if not self._running or self._last_beat is None:
            return False
        import time
        elapsed = time.monotonic() - self._last_beat
        return elapsed < self._config.timeout_seconds * self._config.max_missed

    def get_stats(self) -> dict[str, Any]:
        """Get heartbeat statistics."""
        return {
            "running": self._running,
            "healthy": self.is_healthy(),
        }