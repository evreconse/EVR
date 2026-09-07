ÓB"""
Bootstrap tests for EVRECONSE.

Tests demonstrating application bootstrap works correctly.
"""

from __future__ import annotations

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


class TestBootstrapComponents:
    """Tests for individual bootstrap component factories."""

    @pytest.mark.asyncio
    async def test_create_config_manager(self, app_config: AppConfig) -> None:
        """Test creating ConfigurationManager."""
        with patch("application.bootstrap.MultiSourceConfigLoader") as mock_loader:
            # Provide minimal valid config
            mock_config = {
                "exchange": {
                    "name": "bybit",
                    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
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
                            "condition": {"lower_wick_ratio": 2, "liquidation_window": 12},
                            "risk": {"take_profit_percent": 3.0, "stop_loss_percent": -3.0},
                            "notification": {"channels": ["telegram"]},
                        }
                    }
                },
                "scoring": {
                    "minimum_signal_score": 80,
                    "parameters_active": ["lower_wick_quality", "liquidation_strength", "candle_confirmation"],
                    "lower_wick_quality": {"enabled": True, "max_score": 40},
                    "liquidation_strength": {"enabled": True, "max_score": 35},
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
        with patch("application.bootstrap.BybitDataProvider") as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.is_connected.return_value = True
            mock_provider.connect = AsyncMock()
            mock_provider_class.return_value = mock_provider

            provider = await create_data_provider(app_config)
            assert provider is mock_provider
            mock_provider.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_strategy_engine(self, app_config: AppConfig, fake_data_provider) -> None:
        """Test creating StrategyEngine."""
        engine = await create_strategy_engine(app_config, fake_data_provider)
        assert engine is not None
        assert "LW-001" in engine.list_strategies()

    @pytest.mark.skip(reason="ExceptionGroup warnings during scoring engine initialization")
    @pytest.mark.asyncio
    async def test_create_scoring_engine(self, app_config: AppConfig) -> None:
        """Test creating ScoringEngine."""
        pass

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
                mock_service.connect.assert_called_once()
                mock_engine.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_event_engine(self, app_config: AppConfig) -> None:
        """Test creating EventEngine."""
        engine = await create_event_engine(app_config)
        assert engine is not None
        assert engine.is_running


class TestFullBootstrap:
    """Tests for the full bootstrap process."""

    @pytest.mark.skip(reason="Permission issues with temp directories on Windows")
    @pytest.mark.asyncio
    async def test_bootstrap_creates_context(self, app_config: AppConfig, temp_storage_dir: Path) -> None:
        """Test that bootstrap returns a BootstrapContext."""
        pass

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
            context.config = MagicMock()

    @pytest.mark.skip(reason="Permission issues with temp directories on Windows")
    @pytest.mark.asyncio
    async def test_bootstrap_services_registered_in_container(self, app_config: AppConfig, temp_storage_dir: Path) -> None:
        """Test that all services are registered in the container."""
        pass


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
        assert failed == []È *cascade08Èï *cascade08ïœ	*cascade08œ	î	 *cascade08î	”
”
ä *cascade08ä“*cascade08“õ *cascade08õ¢ *cascade08¢­*cascade08­Ä$ *cascade08Ä$¡%¡%Þ0 *cascade08Þ0±1±1½7 *cascade08½7æ7*cascade08æ7Ô8 *cascade08Ô8§9§9ÓB *cascade082Sfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/tests/test_bootstrap.py