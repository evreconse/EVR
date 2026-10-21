"""
Lifecycle tests for EVRECONSE.

Tests demonstrating application lifecycle management works correctly.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application import Application, create_application
from application.exceptions import (
    ReloadError,
    ShutdownError,
    StartupError,
)
from application.lifecycle import (
    ApplicationState,
    LifecycleManager,
    LifecycleMetrics,
)


class TestApplicationState:
    """Tests for ApplicationState enum."""

    def test_state_values(self) -> None:
        """Test all state values."""
        assert ApplicationState.CREATED.value == "created"
        assert ApplicationState.INITIALIZING.value == "initializing"
        assert ApplicationState.STARTING.value == "starting"
        assert ApplicationState.RUNNING.value == "running"
        assert ApplicationState.STOPPING.value == "stopping"
        assert ApplicationState.STOPPED.value == "stopped"
        assert ApplicationState.RELOADING.value == "reloading"
        assert ApplicationState.FAILED.value == "failed"


class TestLifecycleMetrics:
    """Tests for LifecycleMetrics."""

    def test_default_metrics(self) -> None:
        """Test default metrics values."""
        metrics = LifecycleMetrics(state=ApplicationState.CREATED)
        assert metrics.state == ApplicationState.CREATED
        assert metrics.startup_time_ms is None
        assert metrics.shutdown_time_ms is None
        assert metrics.last_transition is None
        assert metrics.total_restarts == 0
        assert metrics.failed_starts == 0
        assert metrics.failed_shutdowns == 0

    def test_metrics_with_values(self) -> None:
        """Test metrics with values."""
        from datetime import datetime
        metrics = LifecycleMetrics(
            state=ApplicationState.RUNNING,
            startup_time_ms=100.5,
            shutdown_time_ms=50.0,
            last_transition=datetime.now(UTC),
            total_restarts=1,
            failed_starts=0,
            failed_shutdowns=0,
        )
        assert metrics.startup_time_ms == 100.5
        assert metrics.shutdown_time_ms == 50.0
        assert metrics.total_restarts == 1


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    @pytest.fixture
    def bootstrap_context(self) -> MagicMock:
        """Create a bootstrap context with async-aware component mocks."""
        context = MagicMock()
        context.config.exchange.timeframe = "15m"

        provider = MagicMock()
        provider.connect = AsyncMock()
        provider.disconnect = AsyncMock()
        provider.set_market_event_handler = MagicMock()
        provider.get_symbols = AsyncMock(return_value=["BTC-USDT", "ETH-USDT"])
        provider.subscribe_symbols = AsyncMock()
        provider.set_health_check_callback = MagicMock()
        provider.start_heartbeat = AsyncMock()
        provider.start_ws_health_monitor = AsyncMock()
        context.data_provider = provider

        context.event_engine.start = MagicMock()
        context.event_engine.stop = AsyncMock()
        context.notification_engine.start = AsyncMock()
        context.notification_engine.stop = AsyncMock()
        context.scoring_engine.close = MagicMock()
        context.strategy_engine = MagicMock()
        context.outcome_tracker = MagicMock()
        context.storage_engine = MagicMock()
        return context

    @pytest.fixture
    def mock_bootstrap(self, bootstrap_context: MagicMock) -> AsyncMock:
        """Create a mock bootstrap function."""
        return AsyncMock(return_value=bootstrap_context)

    @pytest.mark.asyncio
    async def test_initial_state(self, mock_bootstrap: AsyncMock) -> None:
        """Test initial state is CREATED."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        assert manager.state == ApplicationState.CREATED
        assert manager.context is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_bootstrap: AsyncMock) -> None:
        """Test successful initialization."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        context = await manager.initialize()
        assert manager.state == ApplicationState.INITIALIZING or manager.state == ApplicationState.RUNNING
        assert manager.context is not None
        assert context is manager.context

    @pytest.mark.asyncio
    async def test_initialize_twice_raises(self, mock_bootstrap: AsyncMock) -> None:
        """Test that initializing twice raises error."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()

        with pytest.raises(StartupError, match="Cannot initialize"):
            await manager.initialize()

        assert mock_bootstrap.await_count == 1

    @pytest.mark.asyncio
    async def test_initialize_from_stopped(self, mock_bootstrap: AsyncMock) -> None:
        """Test re-initialization from stopped state."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.start()
        with patch("application.lifecycle.shutdown", new=AsyncMock(return_value=[])):
            await manager.stop()

        assert manager.state == ApplicationState.STOPPED
        await manager.initialize()

        assert manager.state == ApplicationState.INITIALIZING
        assert mock_bootstrap.await_count == 2

    @pytest.mark.asyncio
    async def test_initialize_failed_sets_failed_state(self, mock_bootstrap: AsyncMock) -> None:
        """Test that failed initialization sets FAILED state."""
        mock_bootstrap.side_effect = Exception("Bootstrap failed")
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        with pytest.raises(StartupError):
            await manager.initialize()
        assert manager.state == ApplicationState.FAILED
        assert manager.metrics.failed_starts == 1

    @pytest.mark.asyncio
    async def test_start_success(
        self, mock_bootstrap: AsyncMock, bootstrap_context: MagicMock
    ) -> None:
        """Test successful start."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()

        await manager.start()

        assert manager.state == ApplicationState.RUNNING
        assert manager.metrics.startup_time_ms is not None
        assert manager.wait_for_startup(timeout=0) is True
        bootstrap_context.data_provider.connect.assert_awaited_once()
        bootstrap_context.data_provider.subscribe_symbols.assert_awaited_once_with(
            ["BTC-USDT", "ETH-USDT"], "15m"
        )
        bootstrap_context.notification_engine.start.assert_awaited_once()
        bootstrap_context.event_engine.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_without_initialize_raises(self, mock_bootstrap: AsyncMock) -> None:
        """Test that start without initialize raises error."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)

        with pytest.raises(StartupError, match="Cannot start"):
            await manager.start()

        assert mock_bootstrap.await_count == 0

    @pytest.mark.asyncio
    async def test_stop_success(
        self, mock_bootstrap: AsyncMock, bootstrap_context: MagicMock
    ) -> None:
        """Test successful stop."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.start()

        with patch("application.lifecycle.shutdown", new=AsyncMock(return_value=[])) as mocked_shutdown:
            await manager.stop()

        assert manager.state == ApplicationState.STOPPED
        assert manager.metrics.shutdown_time_ms is not None
        assert manager.wait_for_shutdown(timeout=0) is True
        mocked_shutdown.assert_awaited_once_with(bootstrap_context)

    @pytest.mark.asyncio
    async def test_stop_not_running_returns_early(self, mock_bootstrap: AsyncMock) -> None:
        """Test that stop when not running returns early."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.stop()  # First stop
        await manager.stop()  # Second stop should not raise

    @pytest.mark.asyncio
    async def test_stop_timeout_raises(self, mock_bootstrap: AsyncMock) -> None:
        """Test that stop timeout raises ShutdownError."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.start()

        with patch(
            "application.lifecycle.shutdown",
            new=AsyncMock(side_effect=TimeoutError("shutdown timeout")),
        ):
            with pytest.raises(ShutdownError, match="timed out"):
                await manager.stop(timeout=0.01)

        assert manager.state == ApplicationState.FAILED
        assert manager.metrics.failed_shutdowns == 1
        assert manager.wait_for_shutdown(timeout=0) is True

    @pytest.mark.asyncio
    async def test_reload_success(
        self, mock_bootstrap: AsyncMock, bootstrap_context: MagicMock
    ) -> None:
        """Test successful reload."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.start()

        reloaded_context = await manager.reload()

        assert reloaded_context is bootstrap_context
        assert manager.state == ApplicationState.RUNNING
        assert manager.metrics.total_restarts == 1
        assert mock_bootstrap.await_count == 2
        assert bootstrap_context.event_engine.stop.await_count == 1
        assert bootstrap_context.notification_engine.stop.await_count == 1

    @pytest.mark.asyncio
    async def test_reload_not_running_raises(self, mock_bootstrap: AsyncMock) -> None:
        """Test that reload when not running raises error."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)

        with pytest.raises(ReloadError, match="Cannot reload"):
            await manager.reload()

    @pytest.mark.asyncio
    async def test_reload_failed_sets_failed_state(self, mock_bootstrap: AsyncMock) -> None:
        """Test that failed reload sets FAILED state."""
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        await manager.initialize()
        await manager.start()
        mock_bootstrap.side_effect = Exception("reload failed")

        with pytest.raises(ReloadError, match="reload failed"):
            await manager.reload()

        assert manager.state == ApplicationState.FAILED

    @pytest.mark.asyncio
    async def test_state_change_callback(self, mock_bootstrap: AsyncMock) -> None:
        """Test state change callback is called."""
        callback = MagicMock()
        manager = LifecycleManager(bootstrap_func=mock_bootstrap)
        manager.add_state_change_callback(callback)

        await manager.initialize()

        callback.assert_any_call(ApplicationState.CREATED, ApplicationState.INITIALIZING)


class TestApplicationLifecycle:
    """Tests for Application lifecycle integration."""

    @pytest.fixture
    def mock_components(self) -> Iterator[dict[str, Any]]:
        """Create mock components for application."""
        with patch("application.application.LifecycleManager") as mock_lifecycle_class:
            mock_lifecycle = AsyncMock()
            mock_lifecycle.state = ApplicationState.CREATED
            mock_lifecycle.is_healthy.return_value = True
            mock_lifecycle.initialize = AsyncMock()
            mock_lifecycle.start = AsyncMock()
            mock_lifecycle.stop = AsyncMock()
            mock_lifecycle.reload = AsyncMock()
            mock_lifecycle.add_state_change_callback = MagicMock()
            mock_lifecycle.wait_for_startup = AsyncMock(return_value=True)
            mock_lifecycle.wait_for_shutdown = AsyncMock(return_value=True)
            mock_lifecycle_class.return_value = mock_lifecycle

            app = create_application()
            app._lifecycle = mock_lifecycle
            yield {"app": app, "lifecycle": mock_lifecycle}

    @pytest.mark.asyncio
    async def test_create_application(self) -> None:
        """Test creating application."""
        app = create_application()
        assert isinstance(app, Application)
        assert app.state == ApplicationState.CREATED

    @pytest.mark.asyncio
    async def test_application_initialize(self, mock_components: dict) -> None:
        """Test application initialize."""
        app = mock_components["app"]
        await app.initialize()
        mock_components["lifecycle"].initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_start(self, mock_components: dict) -> None:
        """Test application start."""
        app = mock_components["app"]
        await app.start()
        mock_components["lifecycle"].start.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_stop(self, mock_components: dict) -> None:
        """Test application stop."""
        app = mock_components["app"]
        await app.stop()
        mock_components["lifecycle"].stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_shutdown_alias(self, mock_components: dict) -> None:
        """Test application shutdown alias."""
        app = mock_components["app"]
        await app.shutdown()
        mock_components["lifecycle"].stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_reload(self, mock_components: dict) -> None:
        """Test application reload."""
        app = mock_components["app"]
        mock_components["lifecycle"].reload.return_value = MagicMock()
        result = await app.reload()
        assert result is mock_components["lifecycle"].reload.return_value

    def test_application_properties(self, mock_components: dict) -> None:
        """Test application properties."""
        app = mock_components["app"]
        assert app.state == ApplicationState.CREATED
        assert app.is_running is False
        assert app.is_initialized is True  # mocked lifecycle exposes a context
        assert app.container is not None
        assert app.config_path is None
        assert app.info.name == "EVRECONSE"


class TestWaitFunctions:
    """Tests for wait functions."""

    @pytest.mark.asyncio
    async def test_wait_for_startup(self) -> None:
        """Test wait_for_startup."""
        manager = LifecycleManager()
        manager._startup_complete.set()
        assert manager.wait_for_startup(timeout=1.0) is True

    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self) -> None:
        """Test wait_for_shutdown."""
        manager = LifecycleManager()
        manager._shutdown_event.set()
        assert manager.wait_for_shutdown(timeout=1.0) is True
