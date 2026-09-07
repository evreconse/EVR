“|"""
EVRECONSE Test Infrastructure - Shared Fixtures.

Reusable fixtures for all test modules.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from application import Application, create_application
from application.service_container import ServiceContainer, reset_container
from config import (
    AppConfig,
    ConfigurationManager,
    ExchangeConfig,
    NotificationConfig,
    ScoringConfig,
    StorageConfig,
    StrategyConfig,
    StrategySectionConfig,
    SystemConfig,
)
from config.types import (
    NotificationDefaults,
    NotificationTelegramConfig,
    ScoringDefaults,
    ScoringParameterConfig,
    StrategyConditionConfig,
    StrategyDefaults,
    StrategyNotificationConfig,
    StrategyRiskConfig,
)
from core import LoggingConfig, LogLevel, init_logging, shutdown_logging
from models import Exchange, MarketEvent, Timeframe
from scoring import reset_registry as reset_scoring_registry
from storage.file_repository import FileStorageRepository
from storage.storage_engine import StorageEngine
from strategy.context import StrategyConfig as StrategyConfigData

# =============================================================================
# Session-scoped fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create a session-scoped event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_storage_dir(tmp_path_factory: Any) -> Path:
    """Create a temporary storage directory for tests."""
    return tmp_path_factory.mktemp("storage")


# =============================================================================
# Config fixtures
# =============================================================================

@pytest.fixture
def app_config() -> AppConfig:
    """Return a default AppConfig with test-safe values."""
    return AppConfig(
        exchange=ExchangeConfig(
            name="bybit",
            symbols=("BTCUSDT", "ETHUSDT"),
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=True,
        ),
        strategy=StrategySectionConfig(
            active=("LW-001",),
            strategies={
                "LW-001": StrategyConfig(
                    enabled=True,
                    timeframe="15m",
                    condition=StrategyConditionConfig(
                        lower_wick_ratio=2,
                        liquidation_window=12,
                    ),
                    risk=StrategyRiskConfig(
                        take_profit_percent=3.0,
                        stop_loss_percent=-3.0,
                    ),
                    notification=StrategyNotificationConfig(
                        channels=("telegram",),
                    ),
                ),
            },
        ),
        scoring=ScoringConfig(
            minimum_signal_score=80,
            parameters_active=("lower_wick_quality", "liquidation_strength", "candle_confirmation"),
            lower_wick_quality=ScoringParameterConfig(
                enabled=ScoringDefaults.LW_QUALITY_ENABLED,
                max_score=ScoringDefaults.LW_QUALITY_MAX_SCORE,
            ),
            liquidation_strength=ScoringParameterConfig(
                enabled=ScoringDefaults.LIQ_STRENGTH_ENABLED,
                max_score=ScoringDefaults.LIQ_STRENGTH_MAX_SCORE,
            ),
            candle_confirmation=ScoringParameterConfig(
                enabled=ScoringDefaults.CANDLE_CONF_ENABLED,
                max_score=ScoringDefaults.CANDLE_CONF_MAX_SCORE,
            ),
        ),
        notification=NotificationConfig(
            channels=("telegram",),
            telegram=NotificationTelegramConfig(
                enabled=True,
                bot_token="test_token",
                chat_id="123456789",
            ),
        ),
        storage=StorageConfig(
            data_path="./data",
        ),
        system=SystemConfig(
            log_level="INFO",
            log_path="./logs",
        ),
    )


@pytest.fixture
def config_manager(app_config: AppConfig) -> ConfigurationManager:
    """Return a ConfigurationManager pre-loaded with test config."""
    manager = ConfigurationManager()
    manager._config = app_config
    manager._is_initialized = True
    return manager


# =============================================================================
# Fake Data Provider
# =============================================================================

@pytest.fixture
def fake_data_provider() -> MagicMock:
    """Create a fake MarketDataProvider for testing."""
    provider = MagicMock()
    provider.exchange_name = "bybit"
    provider.supported_timeframes = ["1m", "5m", "15m", "1h"]
    provider.supported_symbols = ["BTCUSDT", "ETHUSDT"]
    provider.is_connected = False
    
    async def connect():
        provider.is_connected = True
    
    async def disconnect():
        provider.is_connected = False
    
    provider.connect = AsyncMock(side_effect=connect)
    provider.disconnect = AsyncMock(side_effect=disconnect)
    provider.reconnect = AsyncMock()
    provider.subscribe_symbols = AsyncMock()
    provider.unsubscribe_symbols = AsyncMock()
    provider.subscribe_timeframe = AsyncMock()
    provider.get_snapshot.return_value = [
        {
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 100.5,
            "timestamp": 1700000000000,
        }
    ]
    provider.ping = AsyncMock(return_value=True)
    provider.stream = AsyncMock(side_effect=TimeoutError("Stream not needed in tests"))
    return provider


# =============================================================================
# Fake Telegram Service
# =============================================================================

@pytest.fixture
def fake_telegram_service() -> MagicMock:
    """Create a fake TelegramService for testing."""
    service = MagicMock()
    service.channel_name = "telegram"
    service.is_connected = True
    service.connect = AsyncMock()
    service.disconnect = AsyncMock()
    service.send = AsyncMock(return_value=MagicMock(success=True))
    service.send_batch = AsyncMock(return_value=[])
    service.health_check = AsyncMock(return_value=True)
    service.close = AsyncMock()
    return service


# =============================================================================
# Fake Storage
# =============================================================================

@pytest.fixture
def fake_storage(temp_storage_dir: Path) -> StorageEngine:
    """Create a fake storage engine using a temp directory."""
    repository = FileStorageRepository(storage_dir=temp_storage_dir)
    engine = StorageEngine(repository)
    return engine


@pytest.fixture
def fake_storage_repository() -> "FakeStorageRepository":
    """Create a fake storage repository for testing."""
    from tests.fixtures.fake_storage import create_fake_repository
    return create_fake_repository()


# =============================================================================
# Fake WebSocket Client
# =============================================================================

@pytest.fixture
def fake_websocket_client() -> MagicMock:
    """Create a fake WebSocketClient for testing."""
    client = MagicMock()
    client.is_connected = True
    client.url = "wss://stream-testnet.bybit.com/v5/public/linear"
    client.connect = MagicMock()
    client.disconnect = MagicMock()
    client.send_json = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.get_stats.return_value = {"connected": True, "subscriptions": 0}
    return client


# =============================================================================
# Fake REST Client
# =============================================================================

@pytest.fixture
def fake_rest_client() -> MagicMock:
    """Create a fake RestClient for testing."""
    client = MagicMock()
    client.get_server_time = AsyncMock(return_value={"result": {"time": "2026-01-01T00:00:00Z"}})
    client.get_instruments_info = AsyncMock(return_value={"result": {"list": []}})
    client.get_tickers = AsyncMock(return_value={"result": {"list": []}})
    client.get_orderbook = AsyncMock(return_value={"result": {"bids": [], "asks": []}})
    client.get_recent_trades = AsyncMock(return_value={"result": {"list": []}})
    client.get_klines = AsyncMock(return_value={"result": {"list": []}})
    client.get_mark_price_klines = AsyncMock(return_value={"result": {"list": []}})
    client.get_index_price_klines = AsyncMock(return_value={"result": {"list": []}})
    client.get_premium_index_klines = AsyncMock(return_value={"result": {"list": []}})
    client.get_wallet_balance = AsyncMock(return_value={"result": {"list": []}})
    client.get_positions = AsyncMock(return_value={"result": {"list": []}})
    client.place_order = AsyncMock(return_value={"result": {"orderId": "test"}})
    client.cancel_order = AsyncMock(return_value={"result": {}})
    client.get_order_history = AsyncMock(return_value={"result": {"list": []}})
    client.close = AsyncMock()
    return client


# =============================================================================
# Fake Event Engine
# =============================================================================

@pytest.fixture
def fake_event_engine() -> MagicMock:
    """Create a fake EventEngine for testing."""
    engine = MagicMock()
    engine.is_running = True
    engine.is_initialized = True
    engine.start = MagicMock()
    engine.stop = AsyncMock()
    engine.shutdown = AsyncMock()
    engine.process_market_data = MagicMock(return_value={"success": True})
    engine.process_event = MagicMock(return_value={"success": True})
    engine.get_stats.return_value = {"processed": 0, "succeeded": 0, "failed": 0}
    engine.get_metrics.return_value = {}
    return engine


# =============================================================================
# Fake Strategy Engine
# =============================================================================

@pytest.fixture
def fake_strategy_engine() -> MagicMock:
    """Create a fake StrategyEngine for testing."""
    engine = MagicMock()
    engine.is_active = MagicMock(return_value=True)
    engine.list_strategies.return_value = ["LW-001"]
    engine.get_strategy.return_value = MagicMock()
    engine.get_metrics.return_value = {"registered_strategies": 1, "active_strategies": 1}
    engine.process_event = AsyncMock(return_value=[])
    return engine


# =============================================================================
# Fake Scoring Engine
# =============================================================================

@pytest.fixture
def fake_scoring_engine() -> MagicMock:
    """Create a fake ScoringEngine for testing."""
    engine = MagicMock()
    engine.is_initialized = True
    engine.get_parameters.return_value = []
    engine.get_stats.return_value = {"initialized": True, "parameter_count": 0}
    engine.evaluate = MagicMock(return_value=MagicMock(qualified=False, final_score=0.0))
    engine.get_parameter.return_value = None
    engine.close = MagicMock()
    return engine


# =============================================================================
# Fake Notification Engine
# =============================================================================

@pytest.fixture
def fake_notification_engine() -> MagicMock:
    """Create a fake NotificationEngine for testing."""
    engine = MagicMock()
    engine._running = False
    engine.start = AsyncMock()
    engine.stop = AsyncMock()
    engine.send = AsyncMock()
    engine.get_stats.return_value = {"running": False, "registered_channels": [], "queue_size": 0}
    engine.close = AsyncMock()
    return engine


# =============================================================================
# Service Container fixtures
# =============================================================================

@pytest.fixture
def fresh_container() -> ServiceContainer:
    """Return a fresh, empty ServiceContainer for testing."""
    container = ServiceContainer()
    return container


@pytest.fixture
def populated_container(app_config: AppConfig, fake_data_provider: MagicMock, fake_storage: StorageEngine, fake_strategy_engine: MagicMock, fake_scoring_engine: MagicMock, fake_notification_engine: MagicMock, fake_event_engine: MagicMock) -> ServiceContainer:
    """Return a ServiceContainer pre-populated with test services."""
    from data_provider import MarketDataProvider
    from event_engine import EventEngine
    from notification import NotificationEngine
    from scoring import ScoringEngine
    from strategy import StrategyEngine
    
    container = ServiceContainer()
    container.register_instance(AppConfig, app_config)
    container.register_instance(MarketDataProvider, fake_data_provider)
    container.register_instance(StorageEngine, fake_storage)
    container.register_instance(StrategyEngine, fake_strategy_engine)
    container.register_instance(ScoringEngine, fake_scoring_engine)
    container.register_instance(NotificationEngine, fake_notification_engine)
    container.register_instance(EventEngine, fake_event_engine)
    return container


# =============================================================================
# Application fixtures
# =============================================================================

@pytest.fixture
def fresh_application() -> Application:
    """Return a fresh Application instance for testing."""
    return create_application(name="EVRECONSE", version="1.0.0")


# =============================================================================
# Market Event fixtures
# =============================================================================

@pytest.fixture
def sample_market_event() -> MarketEvent:
    """Create a sample MarketEvent for testing."""
    return MarketEvent.new(
        symbol="BTCUSDT",
        exchange=Exchange.BYBIT,
        timeframe=Timeframe.M15,
        event_time=__import__("datetime").datetime(2026, 1, 1, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc),
        open_price=50000.0,
        high_price=50100.0,
        low_price=49900.0,
        close_price=50050.0,
        volume=100.5,
    )


# =============================================================================
# Logging fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Set up logging for tests."""
    log_config = LoggingConfig(
        level=LogLevel.INFO,
        console_enabled=False,
        file_enabled=False,
    )
    init_logging(log_config)
    yield
    shutdown_logging()


# =============================================================================
# Cleanup fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test() -> None:
    """Reset global state after each test."""
    yield
    reset_container()
    reset_scoring_registry()
    from strategy.registry import reset_registry
    reset_registry()


# =============================================================================
# Common test utilities
# =============================================================================

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for test artifacts."""
    return tmp_pathß *cascade08ßÿ*cascade08ÿ *cascade08ªª“ *cascade08“¬*cascade08¬ª *cascade08ªÚÚƒ *cascade08ƒÒ*cascade08Òî *cascade08îÉ *cascade08Éš*cascade08šµ *cascade08µåå‹ *cascade08‹Û*cascade08ÛÌ *cascade08ÌÏ*cascade08ÏĞ *cascade08Ğ×*cascade08×Ø *cascade08Øîîï *cascade08ïğ*cascade08ğñ *cascade08ñŒ Œ   *cascade08 — *cascade08— ˜  *cascade08˜ ™ *cascade08™ š  *cascade08š Ô *cascade08Ô ( *cascade08(‘( *cascade08‘(’( *cascade08’(–( *cascade08–(™(*cascade08™(¥( *cascade08¥(©(*cascade08©(µ( *cascade08µ(¶( *cascade08¶(Ú( *cascade08Ú(İ(*cascade08İ(é( *cascade08é(ì(*cascade08ì(ò( *cascade08ò(ó(*cascade08ó(÷( *cascade08÷(ı(*cascade08ı(ÿ( *cascade08ÿ(‚)*cascade08‚)„) *cascade08„)‹) *cascade08‹))*cascade08)’) *cascade08’)“)*cascade08“)¯) *cascade08¯)°)*cascade08°)±) *cascade08±)²)*cascade08²)´) *cascade08´)¸)*cascade08¸)¾) *cascade08¾)Û) *cascade08Û)î)*cascade08î)”* *cascade08”*ª**cascade08ª*—8 *cascade08—8˜8*cascade08˜8™8 *cascade08™8›8*cascade08›8­8 *cascade08­8®8*cascade08®8ì8 *cascade08ì8í8*cascade08í8î8 *cascade08î8ò8*cascade08ò8ó8 *cascade08ó8ú8*cascade08ú8ş8 *cascade08ş8†9*cascade08†9Œ9 *cascade08Œ9¡9*cascade08¡9ª9 *cascade08ª9±9*cascade08±9²9 *cascade08²9·9*cascade08·9¸9 *cascade08¸9¹9*cascade08¹9º9 *cascade08º9»9*cascade08»9½9 *cascade08½9Â9*cascade08Â9Å9 *cascade08Å9Æ9*cascade08Æ9Ç9 *cascade08Ç9È9*cascade08È9Ë9 *cascade08Ë9Í9*cascade08Í9çd *cascade08çdÄf*cascade08Äfºg *cascade08ºg»g*cascade08»g¼g *cascade08¼g½g*cascade08½g¿g *cascade08¿gÁg*cascade08ÁgÄg *cascade08ÄgÅg*cascade08Åg¿h *cascade08¿hÀh*cascade08ÀhÇh *cascade08ÇhÈh*cascade08Èh…i *cascade08…i†i*cascade08†iŒi *cascade08Œii*cascade08iÉi *cascade08ÉiÊi*cascade08ÊiÕi *cascade08ÕiÖi*cascade08Öi—j *cascade08—j˜j*cascade08˜jœj *cascade08œjj*cascade08j“| *cascade082Mfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/tests/conftest.py