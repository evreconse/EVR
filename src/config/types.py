"""
Configuration type definitions for EVRECONSE.

This module contains all type definitions, enums, and dataclasses
used by the Configuration Manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConfigCategory(str, Enum):
    """Configuration parameter categories."""

    STATIC = "static"
    SECRET = "secret"
    RUNTIME = "runtime"


class ConfigSection(str, Enum):
    """Configuration sections."""

    EXCHANGE = "exchange"
    STRATEGY = "strategy"
    SCORING = "scoring"
    NOTIFICATION = "notification"
    RISK = "risk"
    STORAGE = "storage"
    SYSTEM = "system"


class Timeframe(str, Enum):
    """Supported timeframes."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class ExchangeName(str, Enum):
    """Supported exchanges."""

    BYBIT = "bybit"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    TELEGRAM = "telegram"


class ScoringParameter(str, Enum):
    """Scoring parameters."""

    LOWER_WICK_QUALITY = "lower_wick_quality"
    CANDLE_CONFIRMATION = "candle_confirmation"


class ConfigVersion:
    """Configuration schema version."""

    MAJOR = 1
    MINOR = 0

    @classmethod
    def current(cls) -> str:
        return f"{cls.MAJOR}.{cls.MINOR}"

    @classmethod
    def is_compatible(cls, version: str) -> bool:
        try:
            major, _ = map(int, version.split("."))
            return major == cls.MAJOR
        except (ValueError, AttributeError):
            return False


# Default values as separate classes (no magic numbers in code)
class ExchangeDefaults:
    """Exchange configuration defaults."""

    NAME = "bybit"
    SYMBOLS = ("BTCUSDT", "ETHUSDT")
    SYMBOLS_MIN = 20
    SYMBOLS_MAX = 250
    TIMEFRAME = "M15"
    RECONNECT_MAX_ATTEMPTS = 0  # 0 = unlimited
    RECONNECT_INITIAL_DELAY = 1
    RECONNECT_MAX_DELAY = 300
    RECONNECT_BACKOFF_MULTIPLIER = 2
    CONNECTION_TIMEOUT = 30
    CONNECTION_HEARTBEAT_INTERVAL = 30
    TESTNET = False
    RECV_WINDOW = 5000
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW_SECONDS = 1.0
    WEBSOCKET_PING_INTERVAL = 20.0
    WEBSOCKET_PING_TIMEOUT = 10.0


class StrategyDefaults:
    """Strategy configuration defaults."""

    ACTIVE = ("LW-001",)
    LW001_ENABLED = True
    LW001_TIMEFRAME = "M15"
    LW001_TAKE_PROFIT = 3.0
    LW001_STOP_LOSS = -3.0
    LW001_NOTIFICATION_CHANNELS = ("telegram",)


class ScoringDefaults:
    """Scoring configuration defaults."""

    MINIMUM_SIGNAL_SCORE = 80
    MAXIMUM_SCORE = 100
    MINIMUM_SCORE = 0
    PARAMETERS_ACTIVE = (
        "lower_wick_quality",
        "candle_confirmation",
    )
    LW_QUALITY_ENABLED = True
    LW_QUALITY_MAX_SCORE = 40
    CANDLE_CONF_ENABLED = True
    CANDLE_CONF_MAX_SCORE = 25
    PENALTY_ENABLED = True


class NotificationDefaults:
    """Notification configuration defaults."""

    CHANNELS = ("telegram",)
    TELEGRAM_ENABLED = True
    PARSE_MODE = "MarkdownV2"
    DISABLE_WEB_PAGE_PREVIEW = True
    DISABLE_NOTIFICATION = False
    QUEUE_MAX_SIZE = 10000
    QUEUE_TIMEOUT_SECONDS = 30.0
    RATE_LIMIT_REQUESTS = 10.0
    RATE_LIMIT_BURST_SIZE = 30
    RETRY_MAX_ATTEMPTS = 3
    RETRY_BASE_DELAY = 1.0
    RETRY_MAX_DELAY = 60.0
    RETRY_EXPONENTIAL_BASE = 2.0
    DEFAULT_PRIORITY = 0
    DELIVERY_TIMEOUT_SECONDS = 30.0


class RiskDefaults:
    """Risk configuration defaults."""

    TAKE_PROFIT = 3.0
    STOP_LOSS = -3.0
    MAX_DURATION = 24
    EXPIRE_AFTER = 48


class StorageDefaults:
    """Storage configuration defaults."""

    DATA_PATH = "./data"
    RETENTION_DAYS = 90
    BUFFER_SIZE = 100


class SystemDefaults:
    """System configuration defaults."""

    TIMEZONE = "UTC"
    LOG_LEVEL = "info"
    LOG_PATH = "./logs"
    CONFIG_VERSION = "1.0"
    MAX_CONCURRENT_EVENTS = 100
    EXECUTION_TIMEOUT_SECONDS = 30.0
    ENABLE_METRICS = True
    ENABLE_PERSISTENCE = False
    ENABLE_RECOVERY = False


@dataclass(frozen=True)
class ExchangeConfig:
    """Exchange configuration."""

    name: str = ExchangeDefaults.NAME
    symbols: tuple[str, ...] = field(default_factory=lambda: ExchangeDefaults.SYMBOLS)
    symbols_min: int = ExchangeDefaults.SYMBOLS_MIN
    symbols_max: int = ExchangeDefaults.SYMBOLS_MAX
    timeframe: str = ExchangeDefaults.TIMEFRAME
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = ExchangeDefaults.TESTNET
    recv_window: int = ExchangeDefaults.RECV_WINDOW
    rate_limit_requests: int = ExchangeDefaults.RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: float = ExchangeDefaults.RATE_LIMIT_WINDOW_SECONDS
    websocket_ping_interval: float = ExchangeDefaults.WEBSOCKET_PING_INTERVAL
    websocket_ping_timeout: float = ExchangeDefaults.WEBSOCKET_PING_TIMEOUT
    reconnect_max_attempts: int = ExchangeDefaults.RECONNECT_MAX_ATTEMPTS
    reconnect_initial_delay: int = ExchangeDefaults.RECONNECT_INITIAL_DELAY
    reconnect_max_delay: int = ExchangeDefaults.RECONNECT_MAX_DELAY
    reconnect_backoff_multiplier: int = ExchangeDefaults.RECONNECT_BACKOFF_MULTIPLIER
    connection_timeout: int = ExchangeDefaults.CONNECTION_TIMEOUT
    connection_heartbeat_interval: int = ExchangeDefaults.CONNECTION_HEARTBEAT_INTERVAL


@dataclass(frozen=True)
class StrategyConditionConfig:
    """Strategy condition parameters.

    All qualification thresholds are fixed in the canonical LW-001 spec:
    - Range >= 4.5%
    - Body >= 0.8%
    - LW/Body >= 1.3x
    - LW/Range >= 55.0%
    - Open->Low <= -2.5%
    - Volume Ratio >= 1.5x (current / volume 3 candles ago)
    - Red candle only (Close < Open)

    No configurable thresholds needed.
    """
    pass


@dataclass(frozen=True)
class StrategyRiskConfig:
    """Strategy risk parameters."""

    take_profit_percent: float = StrategyDefaults.LW001_TAKE_PROFIT
    stop_loss_percent: float = StrategyDefaults.LW001_STOP_LOSS


@dataclass(frozen=True)
class StrategyNotificationConfig:
    """Strategy notification parameters."""

    channels: tuple[str, ...] = field(
        default_factory=lambda: StrategyDefaults.LW001_NOTIFICATION_CHANNELS
    )


@dataclass(frozen=True)
class StrategyConfig:
    """Individual strategy configuration."""

    enabled: bool = StrategyDefaults.LW001_ENABLED
    timeframe: str = StrategyDefaults.LW001_TIMEFRAME
    condition: StrategyConditionConfig = field(default_factory=StrategyConditionConfig)
    risk: StrategyRiskConfig = field(default_factory=StrategyRiskConfig)
    notification: StrategyNotificationConfig = field(
        default_factory=StrategyNotificationConfig
    )


@dataclass(frozen=True)
class StrategySectionConfig:
    """Strategy section configuration."""

    active: tuple[str, ...] = field(default_factory=lambda: StrategyDefaults.ACTIVE)
    # Using MappingProxyType would be more correct for frozen dataclass,
    # but dict with default_factory is acceptable for internal config
    strategies: dict[str, StrategyConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoringParameterConfig:
    """Individual scoring parameter configuration."""

    enabled: bool = True
    max_score: int = 0


@dataclass(frozen=True)
class ScoringConfig:
    """Scoring configuration."""

    minimum_signal_score: int = ScoringDefaults.MINIMUM_SIGNAL_SCORE
    maximum_score: int = ScoringDefaults.MAXIMUM_SCORE
    minimum_score: int = ScoringDefaults.MINIMUM_SCORE
    parameters_active: tuple[str, ...] = field(
        default_factory=lambda: ScoringDefaults.PARAMETERS_ACTIVE
    )
    lower_wick_quality: ScoringParameterConfig = field(
        default_factory=lambda: ScoringParameterConfig(
            enabled=ScoringDefaults.LW_QUALITY_ENABLED,
            max_score=ScoringDefaults.LW_QUALITY_MAX_SCORE,
        )
    )
    candle_confirmation: ScoringParameterConfig = field(
        default_factory=lambda: ScoringParameterConfig(
            enabled=ScoringDefaults.CANDLE_CONF_ENABLED,
            max_score=ScoringDefaults.CANDLE_CONF_MAX_SCORE,
        )
    )
    penalty_enabled: bool = ScoringDefaults.PENALTY_ENABLED


@dataclass(frozen=True)
class NotificationTelegramConfig:
    """Telegram notification configuration."""

    enabled: bool = NotificationDefaults.TELEGRAM_ENABLED
    bot_token: str = ""
    chat_id: str = ""
    parse_mode: str = NotificationDefaults.PARSE_MODE
    disable_web_page_preview: bool = NotificationDefaults.DISABLE_WEB_PAGE_PREVIEW
    disable_notification: bool = NotificationDefaults.DISABLE_NOTIFICATION


@dataclass(frozen=True)
class NotificationConfig:
    """Notification configuration."""

    channels: tuple[str, ...] = field(
        default_factory=lambda: NotificationDefaults.CHANNELS
    )
    telegram: NotificationTelegramConfig = field(
        default_factory=NotificationTelegramConfig
    )
    queue_max_size: int = NotificationDefaults.QUEUE_MAX_SIZE
    queue_timeout_seconds: float = NotificationDefaults.QUEUE_TIMEOUT_SECONDS
    rate_limit_requests: float = NotificationDefaults.RATE_LIMIT_REQUESTS
    rate_limit_burst_size: int = NotificationDefaults.RATE_LIMIT_BURST_SIZE
    retry_max_attempts: int = NotificationDefaults.RETRY_MAX_ATTEMPTS
    retry_base_delay: float = NotificationDefaults.RETRY_BASE_DELAY
    retry_max_delay: float = NotificationDefaults.RETRY_MAX_DELAY
    retry_exponential_base: float = NotificationDefaults.RETRY_EXPONENTIAL_BASE
    default_priority: int = NotificationDefaults.DEFAULT_PRIORITY
    delivery_timeout_seconds: float = NotificationDefaults.DELIVERY_TIMEOUT_SECONDS


@dataclass(frozen=True)
class RiskConfig:
    """Risk configuration."""

    take_profit_percent: float = RiskDefaults.TAKE_PROFIT
    stop_loss_percent: float = RiskDefaults.STOP_LOSS
    monitoring_max_duration: int = RiskDefaults.MAX_DURATION
    monitoring_expire_after: int = RiskDefaults.EXPIRE_AFTER


@dataclass(frozen=True)
class StorageConfig:
    """Storage configuration."""

    data_path: str = StorageDefaults.DATA_PATH
    events_retention_days: int = StorageDefaults.RETENTION_DAYS
    events_buffer_size: int = StorageDefaults.BUFFER_SIZE


@dataclass(frozen=True)
class SystemConfig:
    """System configuration."""

    timezone: str = SystemDefaults.TIMEZONE
    log_level: str = SystemDefaults.LOG_LEVEL
    log_path: str = SystemDefaults.LOG_PATH
    config_version: str = SystemDefaults.CONFIG_VERSION
    max_concurrent_events: int = SystemDefaults.MAX_CONCURRENT_EVENTS
    execution_timeout_seconds: float = SystemDefaults.EXECUTION_TIMEOUT_SECONDS
    enable_metrics: bool = SystemDefaults.ENABLE_METRICS
    enable_persistence: bool = SystemDefaults.ENABLE_PERSISTENCE
    enable_recovery: bool = SystemDefaults.ENABLE_RECOVERY


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""

    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    strategy: StrategySectionConfig = field(default_factory=lambda: StrategySectionConfig())
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    system: SystemConfig = field(default_factory=SystemConfig)


@dataclass(frozen=True)
class StrategySectionConfig:
    """Strategy section configuration."""

    active: tuple[str, ...] = field(default_factory=lambda: StrategyDefaults.ACTIVE)
    strategies: dict[str, StrategyConfig] = field(default_factory=dict)


# Parameter path constants for validation and access
class ParamPath:
    """Configuration parameter paths (dot notation for nested access)."""

    # Exchange
    EXCHANGE_NAME = "exchange.name"
    EXCHANGE_SYMBOLS = "exchange.symbols"
    EXCHANGE_SYMBOLS_MIN = "exchange.symbols_min"
    EXCHANGE_SYMBOLS_MAX = "exchange.symbols_max"
    EXCHANGE_TIMEFRAME = "exchange.timeframe"
    EXCHANGE_API_KEY = "exchange.api_key"
    EXCHANGE_API_SECRET = "exchange.api_secret"
    EXCHANGE_RECONNECT_MAX_ATTEMPTS = "exchange.reconnect_max_attempts"
    EXCHANGE_RECONNECT_INITIAL_DELAY = "exchange.reconnect_initial_delay"
    EXCHANGE_RECONNECT_MAX_DELAY = "exchange.reconnect_max_delay"
    EXCHANGE_RECONNECT_BACKOFF_MULTIPLIER = "exchange.reconnect_backoff_multiplier"
    EXCHANGE_CONNECTION_TIMEOUT = "exchange.connection_timeout"
    EXCHANGE_CONNECTION_HEARTBEAT_INTERVAL = "exchange.connection_heartbeat_interval"

    # Strategy
    STRATEGY_ACTIVE = "strategy.active"
    STRATEGY_ENABLED = "strategy.{id}.enabled"
    STRATEGY_TIMEFRAME = "strategy.{id}.timeframe"
    STRATEGY_LOWER_WICK_RATIO = "strategy.{id}.condition.lower_wick_ratio"
    STRATEGY_LIQUIDATION_WINDOW = "strategy.{id}.condition.liquidation_window"
    STRATEGY_TAKE_PROFIT = "strategy.{id}.risk.take_profit_percent"
    STRATEGY_STOP_LOSS = "strategy.{id}.risk.stop_loss_percent"
    STRATEGY_NOTIFICATION_CHANNELS = "strategy.{id}.notification.channels"

    # Scoring
    SCORE_MINIMUM_SIGNAL_SCORE = "score.minimum_signal_score"
    SCORE_MAXIMUM_SCORE = "score.maximum_score"
    SCORE_MINIMUM_SCORE = "score.minimum_score"
    SCORE_PARAMETERS_ACTIVE = "score.parameters_active"
    SCORE_PARAMETER_ENABLED = "score.{name}.enabled"
    SCORE_PARAMETER_MAX_SCORE = "score.{name}.max_score"
    SCORE_PENALTY_ENABLED = "score.penalty_enabled"

    # Notification
    NOTIFICATION_CHANNELS = "notification.channels"
    NOTIFICATION_TELEGRAM_ENABLED = "notification.telegram.enabled"
    NOTIFICATION_TELEGRAM_BOT_TOKEN = "notification.telegram.bot_token"
    NOTIFICATION_TELEGRAM_CHAT_ID = "notification.telegram.chat_id"

    # Risk
    RISK_TAKE_PROFIT = "risk.take_profit_percent"
    RISK_STOP_LOSS = "risk.stop_loss_percent"
    RISK_MAX_DURATION = "risk.monitoring_max_duration"
    RISK_EXPIRE_AFTER = "risk.monitoring_expire_after"

    # Storage
    STORAGE_DATA_PATH = "storage.data_path"
    STORAGE_RETENTION_DAYS = "storage.events_retention_days"
    STORAGE_BUFFER_SIZE = "storage.events_buffer_size"

    # System
    SYSTEM_TIMEZONE = "system.timezone"
    SYSTEM_LOG_LEVEL = "system.log_level"
    SYSTEM_LOG_PATH = "system.log_path"
    SYSTEM_CONFIG_VERSION = "system.config_version"


# Required parameters that must be present for startup
REQUIRED_PARAMETERS: tuple[str, ...] = (
    ParamPath.EXCHANGE_API_KEY,
    ParamPath.EXCHANGE_API_SECRET,
    ParamPath.NOTIFICATION_TELEGRAM_BOT_TOKEN,
    ParamPath.NOTIFICATION_TELEGRAM_CHAT_ID,
)

# Parameters that can be changed at runtime (runtime config)
RUNTIME_PARAMETERS: tuple[str, ...] = (
    ParamPath.SCORE_MINIMUM_SIGNAL_SCORE,
    ParamPath.STRATEGY_ENABLED,
    ParamPath.STRATEGY_LIQUIDATION_WINDOW,
    ParamPath.SCORE_PARAMETER_ENABLED,
    ParamPath.SCORE_PARAMETER_MAX_SCORE,
    ParamPath.NOTIFICATION_CHANNELS,
    ParamPath.RISK_MAX_DURATION,
    ParamPath.SYSTEM_LOG_LEVEL,
)

# Parameters that require restart
RESTART_PARAMETERS: tuple[str, ...] = (
    ParamPath.EXCHANGE_NAME,
    ParamPath.EXCHANGE_SYMBOLS,
    ParamPath.EXCHANGE_TIMEFRAME,
    ParamPath.EXCHANGE_API_KEY,
    ParamPath.EXCHANGE_API_SECRET,
    ParamPath.NOTIFICATION_TELEGRAM_BOT_TOKEN,
    ParamPath.STORAGE_DATA_PATH,
    ParamPath.STORAGE_RETENTION_DAYS,
    ParamPath.STRATEGY_LOWER_WICK_RATIO,
    ParamPath.SYSTEM_TIMEZONE,
)

# Secret field names - values of these fields must always be masked
SECRET_FIELD_NAMES: frozenset[str] = frozenset({
    "api_key",
    "api_secret",
    "bot_token",
    "chat_id",
})