"""
Bootstrap tests for EVRECONSE.

Tests demonstrating application bootstrap works correctly.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.bootstrap import (
    BootstrapContext,
    bootstrap,
    create_config_manager,
    create_data_provider,
    create_event_engine,
    create_notification_engine,
    create_scoring_engine,
    create_storage_engine,
    create_strategy_engine,
    shutdown,
)
from application.service_container import ServiceContainer
from config import AppConfig, ConfigurationManager
from config.types import StorageConfig, SystemConfig


async def _bootstrap_with_fakes(
    app_config: AppConfig,
    temp_storage_dir: Path,
) -> tuple[BootstrapContext, MagicMock]:
    """Run the real bootstrap orchestration with filesystem/network boundaries faked."""
    from storage import FileStorageRepository
    from storage.storage_engine import StorageEngine

    test_config = replace(
        app_config,
        storage=StorageConfig(data_path=str(temp_storage_dir)),
        system=SystemConfig(log_level="INFO", log_path=""),
    )
    manager = ConfigurationManager()
    manager._config = test_config
    manager._is_initialized = True

    storage_repository = FileStorageRepository(storage_dir=temp_storage_dir)
    storage_engine = StorageEngine(storage_repository)
    await storage_engine.startup()

    provider = MagicMock()
    provider.connect = AsyncMock()
    provider.disconnect = AsyncMock()
    provider.set_market_event_handler = MagicMock()
    provider.get_symbols = AsyncMock(return_value=list(test_config.exchange.symbols))
    provider.subscribe_symbols = AsyncMock()
    provider.is_connected = True

    with (
        patch(
            "application.bootstrap.create_config_manager",
            new=AsyncMock(return_value=manager),
        ),
        patch(
            "application.bootstrap.create_storage_engine",
            new=AsyncMock(return_value=storage_engine),
        ),
        patch(
            "application.bootstrap.create_data_provider",
            new=AsyncMock(return_value=provider),
        ),
    ):
        context = await bootstrap()

    return context, provider


class TestBootstrapComponents:
    """Tests for individual bootstrap component factories."""

    @pytest.mark.asyncio
    async def test_create_config_manager(self, app_config: AppConfig) -> None:
        """Test creating ConfigurationManager."""
        with patch("application.bootstrap.MultiSourceConfigLoader") as mock_loader:
            # Provide minimal valid config
            mock_config = {
                "exchange": {
                    "name": "bingx",
                    "symbols": ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"],
                    "api_key": "test",
                    "api_secret": "test",
                    "symbols_min": 5,
                },
                "strategy": {
                    "active": ["LW-001"],
                    "strategies": {
                        "LW-001": {
                            "enabled": True,
                            "timeframe": "15m",
                            "condition": {},
                            "risk": {"take_profit_percent": 3.0, "stop_loss_percent": -3.0},
                            "notification": {"channels": ["telegram"]},
                        }
                    }
                },
                "scoring": {
                    "minimum_signal_score": 80,
                    "parameters_active": ["lower_wick_quality", "candle_confirmation"],
                    "lower_wick_quality": {"enabled": True, "max_score": 40},
                    "candle_confirmation": {"enabled": True, "max_score": 25},
                },
                "notification": {
                    "channels": ["telegram"],
                    "telegram": {
                        "enabled": True,
                        "bot_token": "test",
                        "chat_id": "123",
                    },
                },
                "risk": {
                    "take_profit_percent": 3.0,
                    "stop_loss_percent": -3.0,
                    "monitoring_max_duration": 24,
                    "monitoring_expire_after": 48,
                },
                "storage": {"data_path": "./data"},
                "system": {
                    "log_level": "INFO",
                    "log_path": "./logs",
                },
            }
            mock_loader.return_value.load.return_value = mock_config
            mock_loader.return_value.get_source_name.return_value = "test"

            manager = await create_config_manager(None)
            assert isinstance(manager, ConfigurationManager)
            assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_create_storage_engine(self, app_config: AppConfig) -> None:
        """Test creating StorageEngine."""
        from storage import FileStorageRepository
        engine = await create_storage_engine(app_config)
        assert engine is not None
        assert isinstance(engine.repository, FileStorageRepository)

    @pytest.mark.asyncio
    async def test_create_data_provider(self, app_config: AppConfig) -> None:
        """Test creating DataProvider (mocked)."""
        with patch("application.bootstrap.create_bingx_data_provider") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.is_connected.return_value = True
            mock_provider.connect = AsyncMock()
            mock_factory.return_value = mock_provider

            provider = await create_data_provider(app_config)
            assert provider is mock_provider
            mock_provider.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_strategy_engine(self, app_config: AppConfig, fake_data_provider) -> None:
        """Test creating StrategyEngine."""
        engine = await create_strategy_engine(app_config, fake_data_provider)
        assert engine is not None
        assert "LW-001" in engine.list_strategies()

    @pytest.mark.asyncio
    async def test_create_scoring_engine(self, app_config: AppConfig) -> None:
        """Test creating ScoringEngine."""
        from scoring.registry import reset_registry

        reset_registry()
        engine = await create_scoring_engine(app_config)

        assert engine.is_initialized() is True
        parameter_ids = {param.parameter_id for param in engine.get_parameters()}
        assert parameter_ids == {"lower_wick_quality", "candle_confirmation"}

    @pytest.mark.asyncio
    async def test_create_notification_engine(self, app_config: AppConfig) -> None:
        """Test creating NotificationEngine (mocked)."""
        with patch("application.bootstrap.create_telegram_service") as mock_telegram:
            mock_service = AsyncMock()
            mock_service.is_connected = True
            mock_service.connect = AsyncMock()
            mock_telegram.return_value = mock_service

            with patch("application.bootstrap.NotificationEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.start = AsyncMock()
                mock_engine.register_service = MagicMock()
                mock_engine_class.return_value = mock_engine

                engine = await create_notification_engine(app_config)
                assert engine is mock_engine
                mock_engine.register_service.assert_called_once_with(mock_service)

    @pytest.mark.asyncio
    async def test_create_event_engine(self, app_config: AppConfig) -> None:
        """Test creating EventEngine."""
        engine = await create_event_engine(app_config)
        assert engine is not None
        assert engine.is_running


class TestFullBootstrap:
    """Tests for the full bootstrap process."""

    @pytest.mark.asyncio
    async def test_bootstrap_creates_context(
        self, app_config: AppConfig, temp_storage_dir: Path
    ) -> None:
        """Test that bootstrap returns a BootstrapContext."""
        context, provider = await _bootstrap_with_fakes(app_config, temp_storage_dir)

        assert isinstance(context, BootstrapContext)
        assert context.config.exchange.symbols == app_config.exchange.symbols
        assert context.config.storage.data_path == str(temp_storage_dir)
        assert context.data_provider is provider
        assert context.event_engine.is_running is True
        assert len(context.strategy_engine.list_strategies()) == 1
        assert context.scoring_engine.is_initialized() is True
        assert context.storage_engine.repository is not None

        failed = await shutdown(context)
        assert failed == []

    def test_bootstrap_context_immutability(self, app_config: AppConfig) -> None:
        """Test that BootstrapContext is immutable."""
        from dataclasses import FrozenInstanceError
        context = BootstrapContext(
            config=app_config,
            container=ServiceContainer(),
            config_manager=MagicMock(),
            storage_engine=MagicMock(),
            data_provider=MagicMock(),
            strategy_engine=MagicMock(),
            scoring_engine=MagicMock(),
            notification_engine=MagicMock(),
            event_engine=MagicMock(),
            outcome_tracker=MagicMock(),
        )
        with pytest.raises(FrozenInstanceError):
            context.config = MagicMock()  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_bootstrap_services_registered_in_container(
        self, app_config: AppConfig, temp_storage_dir: Path
    ) -> None:
        """Test that all services are registered in the container."""
        from event_engine import EventEngine
        from notification import NotificationEngine
        from outcome import OutcomeTracker
        from scoring import ScoringEngine
        from storage import StorageEngine
        from strategy import StrategyEngine

        context, _ = await _bootstrap_with_fakes(app_config, temp_storage_dir)
        container = context.container

        assert container.has(AppConfig)
        assert container.has(ConfigurationManager)
        assert container.has(StorageEngine)
        assert container.has(StrategyEngine)
        assert container.has(ScoringEngine)
        assert container.has(NotificationEngine)
        assert container.has(EventEngine)
        assert container.has(OutcomeTracker)

        failed = await shutdown(context)
        assert failed == []


class TestBootstrapShutdown:
    """Tests for shutdown process."""

    @pytest.mark.asyncio
    async def test_shutdown_order(self) -> None:
        """Test shutdown calls components in correct order."""
        context = MagicMock()
        context.event_engine = AsyncMock()
        context.event_engine.stop = AsyncMock()
        context.notification_engine = AsyncMock()
        context.notification_engine.stop = AsyncMock()
        context.scoring_engine = MagicMock()
        context.scoring_engine.close = MagicMock()
        context.strategy_engine = MagicMock()
        context.data_provider = AsyncMock()
        context.data_provider.disconnect = AsyncMock()

        failed = await shutdown(context)

        context.event_engine.stop.assert_called_once()
        context.notification_engine.stop.assert_called_once()
        context.scoring_engine.close.assert_called_once()
        context.data_provider.disconnect.assert_called_once()
        assert failed == []
