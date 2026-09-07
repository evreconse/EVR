"""
EVRECONSE Application Layer - Main Application.

Top-level application facade that composes all layers and manages lifecycle.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from core import get_logger

from .bootstrap import BootstrapContext
from .health import (
    ComponentHealth,
    HealthChecker,
    HealthReport,
    create_standard_health_checker,
)
from .lifecycle import (
    ApplicationState,
    LifecycleManager,
    LifecycleMetrics,
)
from .service_container import ServiceContainer

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ApplicationInfo:
    """Immutable application information."""
    name: str = "EVRECONSE"
    version: str = "1.0.0"
    started_at: datetime | None = None
    environment: str = "production"


class Application:
    """
    Main application class - single entry point for the trading bot.

    Composes all layers:
    - Configuration
    - Storage
    - Data Provider
    - Strategy Engine
    - Scoring Engine
    - Notification
    - Event Engine

    Provides:
    - Lifecycle management (initialize, start, stop, reload)
    - Health checking
    - Dependency injection container access
    - Component access via explicit methods
    """

    def __init__(
        self,
        config_path: str | None = None,
        name: str = "EVRECONSE",
        version: str = "1.0.0",
    ) -> None:
        self._config_path = config_path
        self._info = ApplicationInfo(
            name=name,
            version=version,
            started_at=None,
            environment="production",
        )
        self._lifecycle = LifecycleManager(config_path=config_path)
        self._container = ServiceContainer()
        self._health_checker: HealthChecker | None = None
        self._lock = threading.RLock()
        self._started = False

        # Register lifecycle state change callback
        self._lifecycle.add_state_change_callback(self._on_state_change)

    def _on_state_change(self, old_state: ApplicationState, new_state: ApplicationState) -> None:
        """Handle lifecycle state changes."""
        logger.info("Application state: %s -> %s", old_state.value, new_state.value)

        if new_state == ApplicationState.RUNNING:
            with self._lock:
                self._started = True
                self._info = ApplicationInfo(
                    name=self._info.name,
                    version=self._info.version,
                    started_at=datetime.now(UTC),
                    environment=self._info.environment,
                )

    # =========================================================================
    # Lifecycle Methods (Idempotent)
    # =========================================================================

    async def initialize(self) -> BootstrapContext:
        """
        Initialize all application components.

        Returns:
            BootstrapContext with all initialized components

        Raises:
            StartupError: If initialization fails
        """
        return await self._lifecycle.initialize()

    async def start(self) -> None:
        """
        Start all application components.

        Idempotent - safe to call multiple times.
        """
        await self._lifecycle.start()

    async def stop(self, timeout: float = 30.0) -> None:
        """
        Gracefully stop all components.

        Idempotent - safe to call multiple times.

        Args:
            timeout: Maximum time to wait for shutdown
        """
        await self._lifecycle.stop(timeout=timeout)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """
        Full shutdown - alias for stop().

        Idempotent - safe to call multiple times.
        """
        await self.stop(timeout=timeout)

    async def reload(self) -> BootstrapContext:
        """
        Reload configuration and restart components.

        Idempotent - safe to call multiple times.

        Returns:
            New BootstrapContext
        """
        return await self._lifecycle.reload()

    # =========================================================================
    # Health Checking
    # =========================================================================

    def setup_health_checks(self, context: BootstrapContext) -> None:
        """
        Configure health checks for all components.

        Args:
            context: Bootstrap context with initialized components
        """
        self._health_checker = create_standard_health_checker(
            data_provider=context.data_provider,
            storage=context.storage_engine,
            strategy_engine=context.strategy_engine,
            scoring_engine=context.scoring_engine,
            notification_engine=context.notification_engine,
            event_engine=context.event_engine,
        )

    async def health_check(self) -> HealthReport:
        """
        Run all health checks.

        Returns:
            HealthReport with overall status and component details
        """
        if self._health_checker is None:
            raise RuntimeError("Health checks not configured. Call setup_health_checks() first.")
        return await self._health_checker.check_all()

    async def check_component(self, name: str) -> ComponentHealth:
        """
        Run health check for a specific component.

        Args:
            name: Component name

        Returns:
            ComponentHealth for the component
        """
        if self._health_checker is None:
            raise RuntimeError("Health checks not configured")
        return await self._health_checker.check_component(name)

    # =========================================================================
    # Component Access (Read-only)
    # =========================================================================

    @property
    def config_path(self) -> str | None:
        return self._config_path

    @property
    def info(self) -> ApplicationInfo:
        return self._info

    @property
    def state(self) -> ApplicationState:
        return self._lifecycle.state

    @property
    def metrics(self) -> LifecycleMetrics:
        return self._lifecycle.metrics

    @property
    def is_running(self) -> bool:
        return self._lifecycle.state == ApplicationState.RUNNING

    @property
    def is_initialized(self) -> bool:
        return self._lifecycle.context is not None

    @property
    def container(self) -> ServiceContainer:
        return self._container

    @property
    def health_checker(self) -> HealthChecker | None:
        return self._health_checker

    # Context components (available after initialize())
    @property
    def context(self) -> BootstrapContext | None:
        return self._lifecycle.context

    @property
    def config(self):
        """Get application configuration."""
        ctx = self.context
        return ctx.config if ctx else None

    @property
    def storage_engine(self):
        """Get storage engine."""
        ctx = self.context
        return ctx.storage_engine if ctx else None

    @property
    def data_provider(self):
        """Get data provider."""
        ctx = self.context
        return ctx.data_provider if ctx else None

    @property
    def strategy_engine(self):
        """Get strategy engine."""
        ctx = self.context
        return ctx.strategy_engine if ctx else None

    @property
    def scoring_engine(self):
        """Get scoring engine."""
        ctx = self.context
        return ctx.scoring_engine if ctx else None

    @property
    def notification_engine(self):
        """Get notification engine."""
        ctx = self.context
        return ctx.notification_engine if ctx else None

    @property
    def event_engine(self):
        """Get event engine."""
        ctx = self.context
        return ctx.event_engine if ctx else None

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def wait_for_ready(self, timeout: float | None = None) -> bool:
        """Wait for application to be fully started."""
        return self._lifecycle.wait_for_startup(timeout)

    async def wait_for_stopped(self, timeout: float | None = None) -> bool:
        """Wait for application to fully stop."""
        return self._lifecycle.wait_for_shutdown(timeout)

    def is_healthy(self) -> bool:
        """Quick health check - is application in running state?"""
        return self._lifecycle.is_healthy()


# =============================================================================
# Factory Function
# =============================================================================

def create_application(
    config_path: str | None = None,
    name: str = "EVRECONSE",
    version: str = "1.0.0",
) -> Application:
    """
    Create a new Application instance.

    Args:
        config_path: Optional path to configuration file
        name: Application name
        version: Application version

    Returns:
        Application instance
    """
    return Application(config_path=config_path, name=name, version=version)