"""
Configuration module for EVRECONSE.

Public API:
- ConfigurationManager: Main configuration manager class
- ConfigValidator: Configuration validator
- ConfigLoader: Abstract loader interface
- Exceptions: ConfigurationError, ValidationError, etc.
- Types: AppConfig, ExchangeConfig, etc.
"""

from .config_manager import ConfigurationManager, InitializationResult
from .exceptions import (
    ConfigurationError,
    ConfigurationNotInitializedError,
    ConfigurationVersionError,
    DependencyValidationError,
    HotReloadError,
    InvalidParameterTypeError,
    MissingRequiredParameterError,
    ParameterOutOfRangeError,
    SecretsNotFoundError,
)
from .loader import ConfigLoader, StubConfigLoader, MultiSourceConfigLoader, YamlConfigLoader, JsonConfigLoader, EnvConfigLoader, DotEnvConfigLoader
from .types import (
    REQUIRED_PARAMETERS,
    RESTART_PARAMETERS,
    RUNTIME_PARAMETERS,
    SECRET_FIELD_NAMES,
    AppConfig,
    ConfigCategory,
    ConfigSection,
    ConfigVersion,
    ExchangeConfig,
    ExchangeName,
    NotificationChannel,
    NotificationConfig,
    NotificationTelegramConfig,
    ParamPath,
    RiskConfig,
    ScoringConfig,
    ScoringParameter,
    ScoringParameterConfig,
    StorageConfig,
    StrategyConfig,
    StrategySectionConfig,
    SystemConfig,
    Timeframe,
)
from .validator import ConfigValidator, ValidationResult

__all__ = [
    # Main classes
    "ConfigurationManager",
    "InitializationResult",
    "ConfigValidator",
    "ValidationResult",
    "ConfigLoader",
    "StubConfigLoader",
    "MultiSourceConfigLoader",
    "YamlConfigLoader",
    "JsonConfigLoader",
    "EnvConfigLoader",
    "DotEnvConfigLoader",
    # Exceptions
    "ConfigurationError",
    "ConfigurationNotInitializedError",
    "ConfigurationVersionError",
    "MissingRequiredParameterError",
    "InvalidParameterTypeError",
    "ParameterOutOfRangeError",
    "DependencyValidationError",
    "SecretsNotFoundError",
    "HotReloadError",
    # Types
    "AppConfig",
    "ExchangeConfig",
    "StrategyConfig",
    "StrategySectionConfig",
    "ScoringConfig",
    "ScoringParameterConfig",
    "NotificationConfig",
    "NotificationTelegramConfig",
    "RiskConfig",
    "StorageConfig",
    "SystemConfig",
    "ConfigVersion",
    "ConfigCategory",
    "ConfigSection",
    "Timeframe",
    "ExchangeName",
    "NotificationChannel",
    "ScoringParameter",
    "ParamPath",
    "REQUIRED_PARAMETERS",
    "RUNTIME_PARAMETERS",
    "RESTART_PARAMETERS",
    "SECRET_FIELD_NAMES",
]