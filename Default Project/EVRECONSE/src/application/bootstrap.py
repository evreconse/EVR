"""
EVRECONSE Bootstrap - Application Composition.

Centralized bootstrap that creates and wires all components.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from config import AppConfig, ConfigurationManager, MultiSourceConfigLoader
from config.exceptions import ConfigurationError
from core import LoggingConfig, LogLevel, get_logger, init_logging
from data_provider import (
    BybitDataProvider,
    BybitDataProviderConfig,
    DataProvider,
)
from event_engine import EngineConfig as EventEngineConfig, EventEngine
from notification import (
    NotificationEngine,
    NotificationQueue,
    RateLimiter,
    RetryPolicy,
)
from notification.notification_engine import EngineConfig as NotificationEngineConfig
from notification.rate_limiter import RateLimitConfig
from notification.retry_policy import RetryPolicyConfig
from notification.telegram_service import create_telegram_service
from scoring import ScoringEngine
from scoring.scoring_engine import ScoringEngineConfig
from outcome import OutcomeConfig, OutcomeTracker
from storage import FileStorageRepository, StorageEngine
from strategy import StrategyEngine
from strategy.strategy_engine import StrategyEngineConfig

from .service_container import ServiceContainer

if TYPE_CHECKING:
    from .application import Application

logger = get_logger(__name__)


# =============================================================================
# Bootstrap Context
# =============================================================================

@dataclass(frozen=True, slots=True)
class BootstrapContext:
    """Immutable bootstrap context with all initialized components."""
    config: AppConfig
    container: ServiceContainer
    config_manager: ConfigurationManager
    storage_engine: StorageEngine
    data_provider: DataProvider
    strategy_engine: StrategyEngine
    scoring_engine: ScoringEngine
    notification_engine: NotificationEngine
    event_engine: EventEngine
    outcome_tracker: OutcomeTracker


# =============================================================================
# Component Factories
# =============================================================================

async def create_config_manager(config_path: Path | None = None) -> ConfigurationManager:
    """Create and initialize ConfigurationManager."""
    # Use multi-source loader: ENV > .env > config file > defaults
    # Default to config.yaml if no path provided
    if config_path is None:
        config_path = Path("config.yaml")
    
    loader = MultiSourceConfigLoader(
        file_path=config_path,
        dotenv_path=Path(".env"),
        env_prefix="EVRECONSE_",
    )
    manager = ConfigurationManager(loader=loader)

    result = manager.initialize()

    if not result.success:
        raise ConfigurationError(
            f"Configuration initialization failed: {result.validation_result.errors}"
        )

    return manager


async def create_storage_engine(config: AppConfig) -> StorageEngine:
    """Create and initialize StorageEngine."""
    repository = FileStorageRepository(storage_dir=config.storage.data_path)
    engine = StorageEngine(repository)
    await engine.startup()
    return engine


async def create_data_provider(config: AppConfig) -> DataProvider:
    """Create and initialize BybitDataProvider."""
    provider_config = BybitDataProviderConfig(
        api_key=config.exchange.api_key,
        api_secret=config.exchange.api_secret,
        testnet=config.exchange.testnet,
        recv_window=config.exchange.recv_window,
        rate_limit_requests=config.exchange.rate_limit_requests,
        rate_limit_window_seconds=config.exchange.rate_limit_window_seconds,
        websocket_ping_interval=config.exchange.websocket_ping_interval,
        websocket_ping_timeout=config.exchange.websocket_ping_timeout,
        max_reconnect_attempts=config.exchange.reconnect_max_attempts,
        reconnect_base_delay=config.exchange.reconnect_initial_delay,
        reconnect_max_delay=config.exchange.reconnect_max_delay,
    )
    provider = BybitDataProvider(provider_config)
    await provider.connect()
    return provider


async def create_strategy_engine(
    config: AppConfig,
    data_provider: DataProvider,
) -> StrategyEngine:
    """Create and initialize StrategyEngine."""
    engine_config = StrategyEngineConfig(
        max_concurrent_strategies=10,
        execution_timeout=5.0,
        enable_metrics=True,
    )
    engine = StrategyEngine(engine_config)

    # Register strategies from config
    from strategy.context import StrategyConfig as StrategyConfigData
    for strategy_id in config.strategy.active:
        strategy_config = config.strategy.strategies.get(strategy_id)
        if strategy_config and strategy_config.enabled:
            # Import and register strategy instance
            from strategy.lw_001 import LW001Strategy
            strategy_instance = LW001Strategy()
            strategy_params = {
                "lower_wick_ratio": strategy_config.condition.lower_wick_ratio,
                "liquidation_window": strategy_config.condition.liquidation_window,
                "take_profit_percent": strategy_config.risk.take_profit_percent,
                "stop_loss_percent": strategy_config.risk.stop_loss_percent,
                "min_confidence_score": config.scoring.minimum_signal_score,
                "scoring_weights": {
                    "lower_wick_quality": config.scoring.lower_wick_quality.max_score,
                    "liquidation_strength": config.scoring.liquidation_strength.max_score,
                    "candle_confirmation": config.scoring.candle_confirmation.max_score,
                },
            }
            ctx_config = StrategyConfigData(
                strategy_id=strategy_id,
                version="1.0.0",
                parameters=strategy_params,
                enabled=True,
            )
            engine.register_strategy(strategy_instance, ctx_config)
            engine.activate_strategy(strategy_id)

    return engine


async def create_scoring_engine(config: AppConfig) -> ScoringEngine:
    """Create and initialize ScoringEngine."""
    engine_config = ScoringEngineConfig(
        max_concurrent_parameters=10,
        execution_timeout=5.0,
        enable_metrics=True,
    )

    # Register scoring parameters in global registry before creating engine
    from scoring.context import ScoringConfig
    from scoring.parameters.candle_confirmation import CandleConfirmationScore
    from scoring.parameters.liquidation import LiquidationStrengthScore
    from scoring.parameters.lower_wick import LowerWickQualityScore
    from scoring.registry import get_registry

    registry = get_registry()

    # Lower Wick Quality Parameter
    if config.scoring.lower_wick_quality.enabled:
        param = LowerWickQualityScore()
        param_config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={
                "lower_wick_ratio": 2.0,
            },
            enabled=True,
        )
        registry.register(param, param_config)

    # Liquidation Strength Parameter
    if config.scoring.liquidation_strength.enabled:
        param = LiquidationStrengthScore()
        param_config = ScoringConfig(
            scoring_id="liquidation_strength",
            version="1.0.0",
            parameters={
                "liquidation_window": 12,
            },
            enabled=True,
        )
        registry.register(param, param_config)

    # Candle Confirmation Parameter
    if config.scoring.candle_confirmation.enabled:
        param = CandleConfirmationScore()
        param_config = ScoringConfig(
            scoring_id="candle_confirmation",
            version="1.0.0",
            parameters={},
            enabled=True,
        )
        registry.register(param, param_config)

    engine = ScoringEngine(engine_config, registry)
    engine.initialize()
    return engine


async def create_notification_engine(config: AppConfig) -> NotificationEngine:
    """Create and initialize NotificationEngine."""
    # Create Telegram service
    telegram_config = config.notification.telegram
    telegram_service = create_telegram_service(
        bot_token=telegram_config.bot_token,
        chat_id=telegram_config.chat_id,
        parse_mode=telegram_config.parse_mode,
        disable_web_page_preview=telegram_config.disable_web_page_preview,
        disable_notification=telegram_config.disable_notification,
    )
    # Note: Don't connect during bootstrap - connect during start() instead

    # Create queue
    queue = NotificationQueue(
        max_size=config.notification.queue_max_size,
        default_timeout=config.notification.queue_timeout_seconds,
    )

    # Create rate limiter
    rate_limiter = RateLimiter(
        RateLimitConfig(
            requests_per_second=config.notification.rate_limit_requests,
            burst_allowance=config.notification.rate_limit_burst_size if hasattr(config.notification, 'rate_limit_burst_size') else 5,
        )
    )

    # Create retry policy config
    retry_policy_config = RetryPolicyConfig(
        max_attempts=config.notification.retry_max_attempts,
        base_delay=config.notification.retry_base_delay,
        max_delay=config.notification.retry_max_delay,
        multiplier=config.notification.retry_exponential_base,
        jitter=0.1,
    )

    # Create notification engine
    engine_config = NotificationEngineConfig(
        queue_size=config.notification.queue_max_size,
        max_concurrent_deliveries=10,
        default_timeout=config.notification.delivery_timeout_seconds,
        retry_policy=retry_policy_config,
        rate_limit=None,  # Rate limiter handled separately
    )
    engine = NotificationEngine(engine_config)
    engine.register_service(telegram_service)

    # Don't start during bootstrap - start during lifecycle.start()
    return engine


async def create_event_engine(
    config: AppConfig,
    strategy_engine=None,
    scoring_engine=None,
    notification_engine=None,
    outcome_tracker=None,
    storage_service=None,
) -> EventEngine:
    """Create and initialize EventEngine."""
    print(f"[DEBUG-BOOT] create_event_engine called with engines: strategy={strategy_engine is not None}, scoring={scoring_engine is not None}, notification={notification_engine is not None}, outcome={outcome_tracker is not None}, storage={storage_service is not None}")
    engine_config = {
        "max_concurrent_events": config.system.max_concurrent_events,
        "execution_timeout": config.system.execution_timeout_seconds,
        "enable_metrics": config.system.enable_metrics,
        "enable_persistence": config.system.enable_persistence,
        "enable_recovery": config.system.enable_recovery,
    }
    engine = EventEngine(engine_config)
    engine.initialize()
    engine.start(
        strategy_engine=strategy_engine,
        scoring_engine=scoring_engine,
        notification_engine=notification_engine,
        outcome_tracker=outcome_tracker,
        storage_service=storage_service,
    )
    return engine


async def create_outcome_tracker(config: AppConfig) -> OutcomeTracker:
    """Create and initialize OutcomeTracker."""
    outcome_config = OutcomeConfig(
        take_profit_percent=config.risk.take_profit_percent,
        stop_loss_percent=config.risk.stop_loss_percent,
        max_duration_hours=config.risk.monitoring_max_duration,
        expire_after_hours=config.risk.monitoring_expire_after,
    )
    tracker = OutcomeTracker(outcome_config)
    return tracker


# =============================================================================
# Main Bootstrap
# =============================================================================

async def bootstrap(
    config_path: Path | None = None,
) -> BootstrapContext:
    """
    Bootstrap the entire application.

    Creates all components in correct dependency order:
    1. Configuration
    2. Logging
    3. Storage
    4. Data Provider
    5. Strategy Engine
    6. Scoring Engine
    7. Notification
    8. Event Engine
    9. Outcome Tracker

    Args:
        config_path: Optional path to configuration file

    Returns:
        BootstrapContext with all initialized components

    Raises:
        ConfigurationError: If configuration fails
        Exception: If any component fails to initialize
    """
    logger.info("Starting application bootstrap...")

    # 1. Configuration (no dependencies)
    logger.info("Initializing ConfigurationManager...")
    config_manager = await create_config_manager(config_path)
    config = config_manager.get_config()
    logger.info("ConfigurationManager initialized")

    # 2. Logging
    logger.info("Initializing Logging...")
    log_config = LoggingConfig(
        level=LogLevel.from_string(config.system.log_level),
        log_path=Path(config.system.log_path) if config.system.log_path else None,
        console_enabled=True,
        file_enabled=bool(config.system.log_path),
        json_format=True,
        max_bytes=10_000_000,
        backup_count=10,
    )
    init_logging(log_config)
    logger.info("Logging initialized")

    # 3. Storage (depends on config)
    logger.info("Initializing StorageEngine...")
    storage_engine = await create_storage_engine(config)
    logger.info("StorageEngine initialized")

    # 4. Data Provider (depends on config)
    logger.info("Initializing DataProvider...")
    data_provider = await create_data_provider(config)
    logger.info("DataProvider initialized")

    # 5. Strategy Engine (depends on config, data_provider)
    logger.info("Initializing StrategyEngine...")
    strategy_engine = await create_strategy_engine(config, data_provider)
    logger.info("StrategyEngine initialized")

    # 6. Scoring Engine (depends on config)
    logger.info("Initializing ScoringEngine...")
    scoring_engine = await create_scoring_engine(config)
    logger.info("ScoringEngine initialized")

    # 7. Notification Engine (depends on config)
    logger.info("Initializing NotificationEngine...")
    notification_engine = await create_notification_engine(config)
    logger.info("NotificationEngine initialized")

    # 8. Outcome Tracker (depends on config)
    logger.info("Initializing OutcomeTracker...")
    outcome_tracker = await create_outcome_tracker(config)
    logger.info("OutcomeTracker initialized")

    # 8. Event Engine (depends on config)
    logger.info("Initializing EventEngine...")
    event_engine = await create_event_engine(
        config,
        strategy_engine=strategy_engine,
        scoring_engine=scoring_engine,
        notification_engine=notification_engine,
        outcome_tracker=outcome_tracker,
        storage_service=storage_engine,
    )
    logger.info("EventEngine initialized")

    # Create immutable context
    context = BootstrapContext(
        config=config,
        container=ServiceContainer(),
        config_manager=config_manager,
        storage_engine=storage_engine,
        data_provider=data_provider,
        strategy_engine=strategy_engine,
        scoring_engine=scoring_engine,
        notification_engine=notification_engine,
        event_engine=event_engine,
        outcome_tracker=outcome_tracker,
    )

    # Register services in container
    container = context.container
    container.register_instance(AppConfig, config)
    container.register_instance(ConfigurationManager, config_manager)
    container.register_instance(StorageEngine, storage_engine)
    container.register_instance(DataProvider, data_provider)
    container.register_instance(StrategyEngine, strategy_engine)
    container.register_instance(ScoringEngine, scoring_engine)
    container.register_instance(NotificationEngine, notification_engine)
    container.register_instance(EventEngine, event_engine)
    container.register_instance(OutcomeTracker, outcome_tracker)

    logger.info("Application bootstrap completed successfully")
    return context


# =============================================================================
# Shutdown Helpers
# =============================================================================

async def shutdown(context: BootstrapContext) -> list[str]:
    """
    Shutdown all components in reverse dependency order.

    Returns:
        List of components that failed to shutdown
    """
    logger.info("Starting application shutdown...")
    failed = []

    # 1. Event Engine (top of dependency chain)
    try:
        await context.event_engine.stop()
        logger.info("EventEngine shutdown complete")
    except Exception as e:
        logger.error("EventEngine shutdown failed: %s", e)
        failed.append("EventEngine")

    # 2. Notification Engine
    try:
        await context.notification_engine.stop()
        logger.info("NotificationEngine shutdown complete")
    except Exception as e:
        logger.error("NotificationEngine shutdown failed: %s", e)
        failed.append("NotificationEngine")

    # 3. Scoring Engine
    try:
        context.scoring_engine.close()
        logger.info("ScoringEngine shutdown complete")
    except Exception as e:
        logger.error("ScoringEngine shutdown failed: %s", e)
        failed.append("ScoringEngine")

    # 4. Strategy Engine
    try:
        # StrategyEngine doesn't have a shutdown method - strategies are managed individually
        logger.info("StrategyEngine shutdown complete")
    except Exception as e:
        logger.error("StrategyEngine shutdown failed: %s", e)
        failed.append("StrategyEngine")

    # 5. Data Provider
    try:
        await context.data_provider.disconnect()
        logger.info("DataProvider shutdown complete")
    except Exception as e:
        logger.error("DataProvider shutdown failed: %s", e)
        failed.append("DataProvider")

    # 6. Storage Engine - no async shutdown needed
    logger.info("StorageEngine ready")

    logger.info("Application shutdown complete")
    return failed


# =============================================================================
# Signal Handlers
# =============================================================================

def setup_signal_handlers(app: Application) -> None:
    """Setup graceful signal handlers."""
    import signal

    def signal_handler(signum, frame):
        logger.info("Received signal %s, initiating graceful shutdown...", signum)
        asyncio.create_task(app.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)