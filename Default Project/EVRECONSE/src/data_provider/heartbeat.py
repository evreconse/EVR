"""
EVRECONSE Data Provider - Heartbeat Monitor.

Monitors connection health via periodic heartbeats and message timeouts.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HeartbeatConfig:
    """Heartbeat configuration."""
    interval: float = 30.0          # Seconds between heartbeats
    timeout: float = 60.0           # Max time without messages
    ping_timeout: float = 10.0      # Ping response timeout
    enabled: bool = True


class HeartbeatMonitor:
    """
    Monitors connection health via heartbeats and message timeouts.

    Features:
    - Periodic ping/pong
    - Message timeout detection
    - Automatic timeout callbacks
    - Thread-safe for sync and async use
    """

    def __init__(self, config: HeartbeatConfig | None = None) -> None:
        self._config = config or HeartbeatConfig()
        self._callback: Callable[[float], None] | None = None
        self._ping_callback: Callable[[], Any] | None = None
        self._last_message_time = time.monotonic()
        self._last_ping_time = 0.0
        self._running = False
        self._task: asyncio.Task | None = None
        self._lock = threading.Lock()

    def set_timeout_callback(self, callback: Callable[[float], None]) -> None:
        """Set callback for message timeout (elapsed seconds since last message)."""
        self._callback = callback

    def set_ping_callback(self, callback: Callable[[], Any]) -> None:
        """Set callback to send ping (should return awaitable)."""
        self._ping_callback = callback

    def record_message(self) -> None:
        """Record received message timestamp."""
        with self._lock:
            self._last_message_time = time.monotonic()

    def record_ping(self) -> None:
        """Record sent ping timestamp."""
        with self._lock:
            self._last_ping_time = time.monotonic()

    def record_pong(self) -> None:
        """Record received pong - updates last message time."""
        with self._lock:
            self._last_message_time = time.monotonic()

    def start(self) -> None:
        """Start heartbeat monitoring."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_message_time = time.monotonic()

        # Start async task
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._monitor_loop())
        except RuntimeError:
            # No running loop - will start when loop runs
            pass

    def stop(self) -> None:
        """Stop heartbeat monitoring."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._task and not self._task.done():
            self._task.cancel()

    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    def get_time_since_last_message(self) -> float:
        """Get seconds since last message received."""
        with self._lock:
            return time.monotonic() - self._last_message_time

    def get_time_since_last_ping(self) -> float:
        """Get seconds since last ping sent."""
        with self._lock:
            if self._last_ping_time == 0:
                return float('inf')
            return time.monotonic() - self._last_ping_time

    def get_status(self) -> dict[str, Any]:
        """Get monitor status."""
        with self._lock:
            now = time.monotonic()
            return {
                "running": self._running,
                "interval": self._config.interval,
                "timeout": self._config.timeout,
                "time_since_last_message": now - self._last_message_time,
                "time_since_last_ping": now - self._last_ping_time if self._last_ping_time else None,
                "message_timeout": self._config.timeout,
            }

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self._config.interval)

                with self._lock:
                    if not self._running:
                        break

                    now = time.monotonic()
                    time_since_message = now - self._last_message_time

                    # Check message timeout
                    if time_since_message >= self._config.timeout:
                        if self._callback:
                            try:
                                self._callback(time_since_message)
                            except Exception as e:
                                logger.error("Timeout callback failed: %s", e)
                        break  # Stop on timeout

                    # Send ping if needed
                    if self._ping_callback and (now - self._last_ping_time) >= self._config.interval:
                        self._last_ping_time = now
                        try:
                            result = self._ping_callback()
                            if asyncio.iscoroutine(result):
                                await asyncio.wait_for(result, timeout=self._config.ping_timeout)
                        except TimeoutError:
                            logger.warning("Ping timeout")
                        except Exception as e:
                            logger.error("Ping failed: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat monitor error: %s", e)
                await asyncio.sleep(1.0)  # Brief pause before retry


class SyncHeartbeatMonitor:
    """
    Synchronous heartbeat monitor for non-async code paths.

    Uses threading.Timer for periodic checks.
    """

    def __init__(self, interval: float = 30.0, timeout: float = 60.0) -> None:
        self._interval = interval
        self._timeout = timeout
        self._callback: Callable[[float], None] | None = None
        self._ping_callback: Callable[[], None] | None = None
        self._last_message = time.monotonic()
        self._running = False
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def set_timeout_callback(self, callback: Callable[[float], None]) -> None:
        self._callback = callback

    def set_ping_callback(self, callback: Callable[[], None]) -> None:
        self._ping_callback = callback

    def record_message(self) -> None:
        with self._lock:
            self._last_message = time.monotonic()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_message = time.monotonic()
        self._run_check()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()

    def _run_check(self) -> None:
        with self._lock:
            if not self._running:
                return

            now = time.monotonic()
            time_since = now - self._last_message

            if time_since >= self._timeout:
                if self._callback:
                    try:
                        self._callback(time_since)
                    except Exception:
                        pass
                return

            if self._ping_callback:
                try:
                    self._ping_callback()
                except Exception:
                    pass

            self._timer = threading.Timer(self._interval, self._run_check)
            self._timer.daemon = True
            self._timer.start()