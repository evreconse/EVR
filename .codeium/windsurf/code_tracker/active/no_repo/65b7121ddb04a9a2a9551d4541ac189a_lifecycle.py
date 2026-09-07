Ú`from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from core import get_logger

from .bootstrap import BootstrapContext, bootstrap, shutdown
from .exceptions import (
    ApplicationError,
    LifecycleError,
    StartupError,
    ShutdownError,
    ReloadError,
)

logger = get_logger(__name__)


class ApplicationState(Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RELOADING = "reloading"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LifecycleMetrics:
    state: ApplicationState
    startup_time_ms: float | None = None
    shutdown_time_ms: float | None = None
    last_transition: datetime | None = None
    total_restarts: int = 0
    failed_starts: int = 0
    failed_shutdowns: int = 0


class LifecycleManager:
    def __init__(
        self,
        config_path: str | None = None,
        bootstrap_func: Callable[..., BootstrapContext] = bootstrap,
    ) -> None:
        self._config_path = config_path
        self._bootstrap_func = bootstrap_func
        self._state = ApplicationState.CREATED
        self._lock = threading.RLock()
        self._context: BootstrapContext | None = None
        self._startup_start: float | None = None
        self._shutdown_start: float | None = None
        self._metrics = LifecycleMetrics(state=ApplicationState.CREATED)
        self._state_change_callbacks: list[Callable[[ApplicationState, ApplicationState], Any]] = []
        self._shutdown_event = threading.Event()
        self._startup_complete = threading.Event()

    @property
    def state(self) -> ApplicationState:
        with self._lock:
            return self._state

    @property
    def context(self) -> BootstrapContext | None:
        with self._lock:
            return self._context

    @property
    def metrics(self) -> LifecycleMetrics:
        with self._lock:
            return self._metrics

    def add_state_change_callback(
        self,
        callback: Callable[[ApplicationState, ApplicationState], Any],
    ) -> None:
        with self._lock:
            self._state_change_callbacks.append(callback)

    def _set_state(self, new_state: ApplicationState) -> None:
        with self._lock:
            old_state = self._state
            if old_state == new_state:
                return
            self._state = new_state
            self._metrics = LifecycleMetrics(
                state=new_state,
                startup_time_ms=self._metrics.startup_time_ms,
                shutdown_time_ms=self._metrics.shutdown_time_ms,
                last_transition=datetime.now(timezone.utc),
                total_restarts=self._metrics.total_restarts,
                failed_starts=self._metrics.failed_starts,
                failed_shutdowns=self._metrics.failed_shutdowns,
            )
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error("State change callback failed: %s", e)

    async def initialize(self) -> BootstrapContext:
        with self._lock:
            if self._state not in (ApplicationState.CREATED, ApplicationState.STOPPED, ApplicationState.FAILED):
                raise StartupError(
                    f"Cannot initialize from state {self._state.value}",
                    component="LifecycleManager",
                    reason="Invalid state for initialization",
                )
        self._set_state(ApplicationState.INITIALIZING)
        self._startup_start = time.monotonic()
        try:
            context = await self._bootstrap_func(config_path=self._config_path)
            self._context = context
            startup_time = (time.monotonic() - self._startup_start) * 1000
            self._metrics = LifecycleMetrics(
                state=ApplicationState.INITIALIZING,
                startup_time_ms=startup_time,
                last_transition=datetime.now(timezone.utc),
                total_restarts=self._metrics.total_restarts,
                failed_starts=self._metrics.failed_starts,
                failed_shutdowns=self._metrics.failed_shutdowns,
            )
            return context
        except Exception as e:
            self._set_state(ApplicationState.FAILED)
            with self._lock:
                self._metrics = LifecycleMetrics(
                    state=ApplicationState.FAILED,
                    failed_starts=self._metrics.failed_starts + 1,
                )
            raise StartupError(
                "Application initialization failed",
                component="LifecycleManager",
                reason=str(e),
            ) from e

    async def start(self) -> None:
        with self._lock:
            if self._state == ApplicationState.RUNNING:
                return
            if self._state not in (ApplicationState.INITIALIZING, ApplicationState.STOPPED):
                raise StartupError(
                    f"Cannot start from state {self._state.value}",
                    component="LifecycleManager",
                    reason="Invalid state for startup",
                )
            if self._context is None:
                raise StartupError(
                    "Not initialized",
                    component="LifecycleManager",
                    reason="Call initialize() first",
                )
        self._set_state(ApplicationState.STARTING)
        start_time = time.monotonic()
        try:
            # Connect data provider and wire up event handler
            await self._context.data_provider.connect()
            
            # Wire data provider to event engine
            self._context.data_provider.set_market_event_handler(
                lambda event: self._context.event_engine.process_event(event)
            )
            
            # Subscribe to symbols from config (symbols are in exchange section, not strategy)
            symbols = self._context.config.exchange.symbols
            timeframe = self._context.config.exchange.timeframe
            await self._context.data_provider.subscribe_symbols(symbols, timeframe)
            
            await self._context.notification_engine.start()
            self._context.event_engine.start()
            startup_time_val = (time.monotonic() - start_time) * 1000
            self._set_state(ApplicationState.RUNNING)
            self._metrics = LifecycleMetrics(
                state=ApplicationState.RUNNING,
                startup_time_ms=startup_time_val,
                last_transition=datetime.now(timezone.utc),
                total_restarts=self._metrics.total_restarts,
                failed_starts=self._metrics.failed_starts,
                failed_shutdowns=self._metrics.failed_shutdowns,
            )
        except Exception as e:
            with self._lock:
                self._metrics = LifecycleMetrics(
                    state=ApplicationState.FAILED,
                    failed_starts=self._metrics.failed_starts + 1,
                )
            raise StartupError(
                "Application startup failed",
                component="LifecycleManager",
                reason=str(e),
            ) from e

    async def stop(self, timeout: float = 30.0) -> None:
        with self._lock:
            if self._state not in (ApplicationState.RUNNING, ApplicationState.STARTING):
                return
            if self._context is None:
                raise ShutdownError(
                    "No context to stop",
                    component="LifecycleManager",
                    reason="Not initialized",
                )
        self._set_state(ApplicationState.STOPPING)
        self._shutdown_start = time.monotonic()
        self._shutdown_event.clear()
        try:
            failed = await asyncio.wait_for(
                shutdown(self._context),
                timeout=timeout,
            )
            shutdown_time_val = (time.monotonic() - self._shutdown_start) * 1000
            self._metrics = LifecycleMetrics(
                state=ApplicationState.STOPPED,
                shutdown_time_ms=shutdown_time_val,
                last_transition=datetime.now(timezone.utc),
                total_restarts=self._metrics.total_restarts,
                failed_starts=self._metrics.failed_starts,
                failed_shutdowns=self._metrics.failed_shutdowns + (1 if failed else 0),
            )
            if failed:
                self._set_state(ApplicationState.FAILED)
                raise ShutdownError(
                    "Shutdown completed with failures: " + ", ".join(failed),
                    component="LifecycleManager",
                    reason="Failed components: " + ", ".join(failed),
                )
            else:
                self._set_state(ApplicationState.STOPPED)
        except asyncio.TimeoutError:
            self._set_state(ApplicationState.FAILED)
            with self._lock:
                self._metrics = LifecycleMetrics(
                    state=ApplicationState.FAILED,
                    failed_shutdowns=self._metrics.failed_shutdowns + 1,
                )
            raise ShutdownError(
                f"Shutdown timed out after {timeout}s",
                component="LifecycleManager",
                reason="Timeout",
            ) from None
        except Exception as e:
            self._set_state(ApplicationState.FAILED)
            with self._lock:
                self._metrics = LifecycleMetrics(
                    state=ApplicationState.FAILED,
                    failed_shutdowns=self._metrics.failed_shutdowns + 1,
                )
            raise ShutdownError(
                "Shutdown failed",
                component="LifecycleManager",
                reason=str(e),
            ) from e

    async def reload(self) -> BootstrapContext:
        with self._lock:
            if self._state != ApplicationState.RUNNING:
                raise ReloadError(
                    f"Cannot reload from state {self._state.value}",
                    component="LifecycleManager",
                    reason="Application must be running",
                )
        self._set_state(ApplicationState.RELOADING)
        try:
            await self._stop_async_components()
            new_context = await self._bootstrap_func(config_path=self._config_path)
            self._context = new_context
            await self.start()
            with self._lock:
                self._metrics = LifecycleMetrics(
                    state=ApplicationState.RUNNING,
                    startup_time_ms=self._metrics.startup_time_ms,
                    shutdown_time_ms=self._metrics.shutdown_time_ms,
                    last_transition=datetime.now(timezone.utc),
                    total_restarts=self._metrics.total_restarts + 1,
                    failed_starts=self._metrics.failed_starts,
                    failed_shutdowns=self._metrics.failed_shutdowns,
                )
            return new_context
        except Exception as e:
            self._set_state(ApplicationState.FAILED)
            raise ReloadError(
                "Application reload failed",
                component="LifecycleManager",
                reason=str(e),
            ) from e

    async def _stop_async_components(self) -> None:
        if self._context is None:
            return
        try:
            await self._context.event_engine.stop()
        except Exception:
            logger.exception("Failed to stop EventEngine during reload")
        try:
            await self._context.notification_engine.stop()
        except Exception:
            logger.exception("Failed to stop NotificationEngine during reload")

    def wait_for_startup(self, timeout: float | None = None) -> bool:
        return self._startup_complete.wait(timeout)

    def wait_for_shutdown(self, timeout: float | None = None) -> bool:
        return self._shutdown_event.wait(timeout)

    def is_healthy(self) -> bool:
        with self._lock:
            return self._state == ApplicationState.RUNNING


# Alias for backward compatibility
ApplicationLifecycleManager = LifecycleManager·/ *cascade08·/ë0*cascade08ë0æ0 *cascade08æ0√0*cascade08√0ƒ0 *cascade08ƒ0≈0*cascade08≈0¸0 *cascade08¸0Å1*cascade08Å1Ç1 *cascade08Ç1É1*cascade08É1Ú` *cascade082Xfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/application/lifecycle.py