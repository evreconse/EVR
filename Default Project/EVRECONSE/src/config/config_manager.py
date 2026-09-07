"""
Configuration Manager for EVRECONSE.

Single source of configuration for all modules.
Follows Configuration First principle - all configurable parameters managed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import (
    ConfigurationError,
    ConfigurationNotInitializedError,
    MissingRequiredParameterError,
)
from .loader import ConfigLoader, StubConfigLoader
from .types import (
    RESTART_PARAMETERS,
    RUNTIME_PARAMETERS,
    SECRET_FIELD_NAMES,
    AppConfig,
    ExchangeConfig,
    NotificationConfig,
    NotificationTelegramConfig,
    RiskConfig,
    ScoringConfig,
    ScoringParameterConfig,
    StorageConfig,
    StrategyConditionConfig,
    StrategyConfig,
    StrategyNotificationConfig,
    StrategyRiskConfig,
    StrategySectionConfig,
    SystemConfig,
)
from .validator import ConfigValidator, ValidationResult


@dataclass(frozen=True)
class InitializationResult:
    """Result of configuration initialization."""

    success: bool
    validation_result: ValidationResult
    source_name: str


class ConfigurationManager:
    """
    Configuration Manager - single source of configuration for all modules.

    Implements Configuration First principle: all configurable parameters
    are managed here. Modules retrieve settings through this manager.

    The manager uses a ConfigLoader to load raw configuration, validates it
    via ConfigValidator, and provides typed access to configuration sections.

    Public API is stable - future loaders (YAML, .env, JSON) will be plugged
    in via ConfigLoader interface without changing this class.
    """

    def __init__(self, loader: ConfigLoader | None = None) -> None:
        """
        Initialize Configuration Manager.

        Args:
            loader: Configuration loader instance. Defaults to StubConfigLoader.
        """
        self._loader = loader or StubConfigLoader()
        self._validator = ConfigValidator()
        self._config: AppConfig | None = None
        self._is_initialized = False

    def initialize(self, override_config: dict[str, Any] | None = None) -> InitializationResult:
        """
        Initialize the configuration manager.

        Loads configuration via loader, merges with overrides, validates,
        and stores the result.

        Args:
            override_config: Optional configuration overrides (e.g., for testing).

        Returns:
            InitializationResult with success status and validation details.

        Raises:
            ConfigurationError: If initialization fails critically.
        """
        if self._is_initialized:
            raise ConfigurationError("ConfigurationManager already initialized")

        try:
            raw_config = self._loader.load()
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

        # Apply overrides if provided
        if override_config:
            raw_config = self._deep_merge(raw_config, override_config)

        # Convert to AppConfig (using defaults for missing values)
        config = self._raw_to_app_config(raw_config)

        # Validate
        validator = ConfigValidator()
        validation_result = validator.validate(config)

        if not validation_result.is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in validation_result.errors
            )
            raise ConfigurationError(error_msg)

        self._config = config
        self._is_initialized = True

        return InitializationResult(
            success=True,
            validation_result=validation_result,
            source_name=self._loader.get_source_name(),
        )

    def reload(self, override_config: dict[str, Any] | None = None) -> InitializationResult:
        """
        Reload configuration.

        Uses the same internal mechanism as initialize() - follows DRY principle.

        Args:
            override_config: Optional configuration overrides.

        Returns:
            InitializationResult with success status and validation details.

        Raises:
            ConfigurationError: If reload fails.
        """
        if not self._is_initialized:
            raise ConfigurationError("ConfigurationManager not initialized")

        # Reuse initialize logic - DRY principle
        self._is_initialized = False
        self._config = None
        return self.initialize(override_config)

    def is_initialized(self) -> bool:
        """Check if manager has been initialized."""
        return self._is_initialized

    def get_config(self) -> AppConfig:
        """
        Get complete application configuration.

        Returns:
            Complete application configuration.

        Raises:
            ConfigurationNotInitializedError: If not initialized.
        """
        if not self._is_initialized:
            raise ConfigurationNotInitializedError()
        return self._config

    # Section getters - universal interface for modules

    def get_exchange(self) -> ExchangeConfig:
        """Get exchange configuration."""
        return self.get_config().exchange

    def get_strategy(self) -> StrategySectionConfig:
        """Get strategy section configuration."""
        return self.get_config().strategy

    def get_strategy_config(self, strategy_id: str) -> StrategyConfig:
        """
        Get configuration for a specific strategy.

        Args:
            strategy_id: Strategy identifier (e.g., "LW-001").

        Returns:
            Strategy configuration.

        Raises:
            KeyError: If strategy not found.
        """
        strategies = self.get_config().strategy.strategies
        if strategy_id not in strategies:
            raise KeyError(f"Strategy '{strategy_id}' not configured")
        return strategies[strategy_id]

    def get_scoring(self) -> ScoringConfig:
        """Get scoring configuration."""
        return self.get_config().scoring

    def get_notification(self) -> NotificationConfig:
        """Get notification configuration."""
        return self.get_config().notification

    def get_risk(self) -> RiskConfig:
        """Get risk configuration."""
        return self.get_config().risk

    def get_storage(self) -> StorageConfig:
        """Get storage configuration."""
        return self.get_config().storage

    def get_system(self) -> SystemConfig:
        """Get system configuration."""
        return self.get_config().system

    # Parameter introspection

    def is_parameter_runtime(self, parameter_path: str) -> bool:
        """
        Check if a parameter can be changed at runtime.

        Args:
            parameter_path: Dot-separated parameter path.

        Returns:
            True if parameter can be changed without restart.
        """
        return any(parameter_path.startswith(p.rstrip("*")) for p in RUNTIME_PARAMETERS)

    def is_parameter_restart(self, parameter_path: str) -> bool:
        """
        Check if a parameter requires restart.

        Args:
            parameter_path: Dot-separated parameter path.

        Returns:
            True if parameter requires restart to take effect.
        """
        return any(parameter_path.startswith(p.rstrip("*")) for p in RESTART_PARAMETERS)

    def get_version(self) -> str:
        """Get configuration schema version."""
        return self.get_config().system.config_version

    # Masking for safe logging

    def to_dict(self, mask_secrets: bool = True) -> dict[str, Any]:
        """
        Export configuration as dictionary, optionally masking secrets.

        Args:
            mask_secrets: Whether to mask secret values.

        Returns:
            Configuration dictionary.
        """
        config_dict = self._config_to_dict(self._config)
        if mask_secrets:
            return self._mask_secrets(config_dict)
        return config_dict

    # Private methods

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _raw_to_app_config(self, raw: dict[str, Any]) -> AppConfig:
        """Convert raw dict configuration to AppConfig dataclass."""
        exchange = self._build_exchange_config(raw.get("exchange", {}))
        strategy = self._build_strategy_config(raw.get("strategy", {}))
        scoring = self._build_scoring_config(raw.get("scoring", {}))
        notification = self._build_notification_config(raw.get("notification", {}))
        risk = self._build_risk_config(raw.get("risk", {}))
        storage = self._build_storage_config(raw.get("storage", {}))
        system = self._build_system_config(raw.get("system", {}))

        return AppConfig(
            exchange=exchange,
            strategy=strategy,
            scoring=scoring,
            notification=notification,
            risk=risk,
            storage=storage,
            system=system,
        )

    def _build_exchange_config(self, raw: dict[str, Any]) -> ExchangeConfig:
        from .types import ExchangeConfig, ExchangeDefaults

        reconnect = raw.get("reconnect", {})
        connection = raw.get("connection", {})
        return ExchangeConfig(
            name=raw.get("name", ExchangeDefaults.NAME),
            symbols=tuple(raw.get("symbols", ExchangeDefaults.SYMBOLS)),
            symbols_min=raw.get("symbols_min", ExchangeDefaults.SYMBOLS_MIN),
            symbols_max=raw.get("symbols_max", ExchangeDefaults.SYMBOLS_MAX),
            timeframe=raw.get("timeframe", ExchangeDefaults.TIMEFRAME),
            api_key=raw.get("api_key", ""),
            api_secret=raw.get("api_secret", ""),
            testnet=raw.get("testnet", ExchangeDefaults.TESTNET),
            recv_window=raw.get("recv_window", ExchangeDefaults.RECV_WINDOW),
            rate_limit_requests=raw.get("rate_limit_requests", ExchangeDefaults.RATE_LIMIT_REQUESTS),
            rate_limit_window_seconds=raw.get("rate_limit_window_seconds", ExchangeDefaults.RATE_LIMIT_WINDOW_SECONDS),
            websocket_ping_interval=raw.get("websocket_ping_interval", ExchangeDefaults.WEBSOCKET_PING_INTERVAL),
            websocket_ping_timeout=raw.get("websocket_ping_timeout", ExchangeDefaults.WEBSOCKET_PING_TIMEOUT),
            reconnect_max_attempts=reconnect.get("max_attempts", ExchangeDefaults.RECONNECT_MAX_ATTEMPTS),
            reconnect_initial_delay=reconnect.get("initial_delay", ExchangeDefaults.RECONNECT_INITIAL_DELAY),
            reconnect_max_delay=reconnect.get("max_delay", ExchangeDefaults.RECONNECT_MAX_DELAY),
            reconnect_backoff_multiplier=reconnect.get("backoff_multiplier", ExchangeDefaults.RECONNECT_BACKOFF_MULTIPLIER),
            connection_timeout=connection.get("timeout", ExchangeDefaults.CONNECTION_TIMEOUT),
            connection_heartbeat_interval=connection.get("heartbeat_interval", ExchangeDefaults.CONNECTION_HEARTBEAT_INTERVAL),
        )

    def _build_strategy_config(self, raw: dict[str, Any]) -> StrategySectionConfig:
        from .types import StrategyConfig, StrategyDefaults, StrategySectionConfig

        active = tuple(raw.get("active", StrategyDefaults.ACTIVE))
        strategies = {}
        for strategy_id in active:
            strategy_raw = raw.get("strategies", {}).get(strategy_id, {})
            if not strategy_raw:
                raise MissingRequiredParameterError(f"strategy.{strategy_id}")
            condition = strategy_raw.get("condition", {})
            risk = strategy_raw.get("risk", {})
            notification = strategy_raw.get("notification", {})
            strategies[strategy_id] = StrategyConfig(
                enabled=strategy_raw.get("enabled", StrategyDefaults.LW001_ENABLED),
                timeframe=strategy_raw.get("timeframe", StrategyDefaults.LW001_TIMEFRAME),
                condition=StrategyConditionConfig(
                    lower_wick_ratio=condition.get("lower_wick_ratio", StrategyDefaults.LW001_LOWER_WICK_RATIO),
                    liquidation_window=condition.get("liquidation_window", StrategyDefaults.LW001_LIQUIDATION_WINDOW),
                ),
                risk=StrategyRiskConfig(
                    take_profit_percent=risk.get("take_profit_percent", StrategyDefaults.LW001_TAKE_PROFIT),
                    stop_loss_percent=risk.get("stop_loss_percent", StrategyDefaults.LW001_STOP_LOSS),
                ),
                notification=StrategyNotificationConfig(
                    channels=tuple(notification.get("channels", StrategyDefaults.LW001_NOTIFICATION_CHANNELS))
                ),
            )
        return StrategySectionConfig(active=active, strategies=strategies)

    def _build_scoring_config(self, raw: dict[str, Any]) -> ScoringConfig:
        from .types import ScoringConfig, ScoringDefaults

        params = raw.get("parameters", {})
        return ScoringConfig(
            minimum_signal_score=raw.get("minimum_signal_score", ScoringDefaults.MINIMUM_SIGNAL_SCORE),
            maximum_score=raw.get("maximum_score", ScoringDefaults.MAXIMUM_SCORE),
            minimum_score=raw.get("minimum_score", ScoringDefaults.MINIMUM_SCORE),
            parameters_active=tuple(raw.get("parameters_active", ScoringDefaults.PARAMETERS_ACTIVE)),
            lower_wick_quality=self._build_scoring_param(params.get("lower_wick_quality", {}), ScoringDefaults.LW_QUALITY_ENABLED, ScoringDefaults.LW_QUALITY_MAX_SCORE),
            liquidation_strength=self._build_scoring_param(params.get("liquidation_strength", {}), ScoringDefaults.LIQ_STRENGTH_ENABLED, ScoringDefaults.LIQ_STRENGTH_MAX_SCORE),
            candle_confirmation=self._build_scoring_param(params.get("candle_confirmation", {}), ScoringDefaults.CANDLE_CONF_ENABLED, ScoringDefaults.CANDLE_CONF_MAX_SCORE),
            penalty_enabled=raw.get("penalty_enabled", ScoringDefaults.PENALTY_ENABLED),
        )

    def _build_scoring_param(self, raw: dict[str, Any], default_enabled: bool, default_max_score: int) -> ScoringConfig:
        return ScoringParameterConfig(
            enabled=raw.get("enabled", default_enabled),
            max_score=raw.get("max_score", default_max_score),
        )

    def _build_notification_config(self, raw: dict[str, Any]) -> NotificationConfig:
        from .types import NotificationConfig, NotificationDefaults

        telegram = raw.get("telegram", {})
        return NotificationConfig(
            channels=tuple(raw.get("channels", NotificationDefaults.CHANNELS)),
            telegram=NotificationTelegramConfig(
                enabled=telegram.get("enabled", NotificationDefaults.TELEGRAM_ENABLED),
                bot_token=telegram.get("bot_token", ""),
                chat_id=telegram.get("chat_id", ""),
                parse_mode=telegram.get("parse_mode", NotificationDefaults.PARSE_MODE),
                disable_web_page_preview=telegram.get("disable_web_page_preview", NotificationDefaults.DISABLE_WEB_PAGE_PREVIEW),
                disable_notification=telegram.get("disable_notification", NotificationDefaults.DISABLE_NOTIFICATION),
            ),
            queue_max_size=raw.get("queue_max_size", NotificationDefaults.QUEUE_MAX_SIZE),
            queue_timeout_seconds=raw.get("queue_timeout_seconds", NotificationDefaults.QUEUE_TIMEOUT_SECONDS),
            rate_limit_requests=raw.get("rate_limit_requests", NotificationDefaults.RATE_LIMIT_REQUESTS),
            rate_limit_burst_size=raw.get("rate_limit_burst_size", NotificationDefaults.RATE_LIMIT_BURST_SIZE),
            retry_max_attempts=raw.get("retry_max_attempts", NotificationDefaults.RETRY_MAX_ATTEMPTS),
            retry_base_delay=raw.get("retry_base_delay", NotificationDefaults.RETRY_BASE_DELAY),
            retry_max_delay=raw.get("retry_max_delay", NotificationDefaults.RETRY_MAX_DELAY),
            retry_exponential_base=raw.get("retry_exponential_base", NotificationDefaults.RETRY_EXPONENTIAL_BASE),
            default_priority=raw.get("default_priority", NotificationDefaults.DEFAULT_PRIORITY),
            delivery_timeout_seconds=raw.get("delivery_timeout_seconds", NotificationDefaults.DELIVERY_TIMEOUT_SECONDS),
        )

    def _build_risk_config(self, raw: dict[str, Any]) -> RiskConfig:
        from .types import RiskConfig, RiskDefaults

        monitoring = raw.get("monitoring", {})
        return RiskConfig(
            take_profit_percent=raw.get("take_profit_percent", RiskDefaults.TAKE_PROFIT),
            stop_loss_percent=raw.get("stop_loss_percent", RiskDefaults.STOP_LOSS),
            monitoring_max_duration=monitoring.get("max_duration", RiskDefaults.MAX_DURATION),
            monitoring_expire_after=monitoring.get("expire_after", RiskDefaults.EXPIRE_AFTER),
        )

    def _build_storage_config(self, raw: dict[str, Any]) -> StorageConfig:
        from .types import StorageConfig, StorageDefaults

        events = raw.get("events", {})
        return StorageConfig(
            data_path=raw.get("data_path", StorageDefaults.DATA_PATH),
            events_retention_days=events.get("retention_days", StorageDefaults.RETENTION_DAYS),
            events_buffer_size=events.get("buffer_size", StorageDefaults.BUFFER_SIZE),
        )

    def _build_system_config(self, raw: dict[str, Any]) -> SystemConfig:
        from .types import SystemConfig, SystemDefaults

        return SystemConfig(
            timezone=raw.get("timezone", SystemDefaults.TIMEZONE),
            log_level=raw.get("log_level", SystemDefaults.LOG_LEVEL),
            log_path=raw.get("log_path", SystemDefaults.LOG_PATH),
            config_version=raw.get("config_version", SystemDefaults.CONFIG_VERSION),
            max_concurrent_events=raw.get("max_concurrent_events", SystemDefaults.MAX_CONCURRENT_EVENTS),
            execution_timeout_seconds=raw.get("execution_timeout_seconds", SystemDefaults.EXECUTION_TIMEOUT_SECONDS),
            enable_metrics=raw.get("enable_metrics", SystemDefaults.ENABLE_METRICS),
            enable_persistence=raw.get("enable_persistence", SystemDefaults.ENABLE_PERSISTENCE),
            enable_recovery=raw.get("enable_recovery", SystemDefaults.ENABLE_RECOVERY),
        )

    def _config_to_dict(self, config: AppConfig) -> dict[str, Any]:
        """Convert AppConfig to dictionary."""
        return {
            "exchange": self._dataclass_to_dict(config.exchange),
            "strategy": self._dataclass_to_dict(config.strategy),
            "scoring": self._dataclass_to_dict(config.scoring),
            "notification": self._dataclass_to_dict(config.notification),
            "risk": self._dataclass_to_dict(config.risk),
            "storage": self._dataclass_to_dict(config.storage),
            "system": self._dataclass_to_dict(config.system),
        }

    def _dataclass_to_dict(self, obj: Any) -> dict[str, Any]:
        """Convert dataclass to dictionary recursively."""
        if hasattr(obj, "__dataclass_fields__"):
            return {k: self._dataclass_to_dict(v) for k, v in vars(obj).items()}
        if isinstance(obj, (list, tuple)):
            return [self._dataclass_to_dict(v) for v in obj]
        if isinstance(obj, dict):
            return {k: self._dataclass_to_dict(v) for k, v in obj.items()}
        return obj

    def _mask_secrets(self, obj: Any) -> Any:
        """Mask secret values based on field NAMES (not content)."""
        if isinstance(obj, dict):
            return {
                k: "*****" if k in SECRET_FIELD_NAMES else self._mask_secrets(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [self._mask_secrets(v) for v in obj]
        return obj