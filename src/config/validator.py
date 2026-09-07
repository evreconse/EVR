"""
Configuration validator for EVRECONSE.

This module contains all validation logic for the configuration.
It is separated from ConfigurationManager to follow SRP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import (
    REQUIRED_PARAMETERS,
    AppConfig,
    ConfigVersion,
    ParamPath,
    ScoringParameter,
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


class ConfigValidator:
    """
    Configuration validator.

    Validates configuration against all rules defined in CONFIGURATION_SYSTEM.md.
    Does not modify configuration - only validates and returns results.
    """

    def __init__(self) -> None:
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def validate(self, config: AppConfig) -> ValidationResult:
        """
        Validate complete configuration.

        Args:
            config: Configuration to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        self._errors = []
        self._warnings = []

        self._validate_version(config)
        self._validate_required_parameters(config)
        self._validate_parameter_types(config)
        self._validate_parameter_ranges(config)
        self._validate_dependencies(config)

        return ValidationResult(
            is_valid=len(self._errors) == 0,
            errors=tuple(self._errors),
            warnings=tuple(self._warnings),
        )

    def _validate_version(self, config: AppConfig) -> None:
        """Validate configuration schema version."""
        if not ConfigVersion.is_compatible(config.system.config_version):
            self._errors.append(
                f"Configuration version {config.system.config_version} "
                f"is incompatible with current version {ConfigVersion.current()}"
            )

    def _validate_required_parameters(self, config: AppConfig) -> None:
        """Validate that all required parameters are present and non-empty."""
        for param_path in REQUIRED_PARAMETERS:
            value = self._get_nested_value(config, param_path)
            if not value:
                self._errors.append(
                    f"Required parameter '{param_path}' is missing or empty"
                )

    def _validate_parameter_types(self, config: AppConfig) -> None:
        """Validate parameter types."""

        # Exchange
        self._check_type(
            config, ParamPath.EXCHANGE_SYMBOLS, (tuple, list), "sequence"
        )
        self._check_type(config, ParamPath.EXCHANGE_TIMEFRAME, str, "string")
        self._check_type(config, ParamPath.EXCHANGE_API_KEY, str, "string")
        self._check_type(config, ParamPath.EXCHANGE_API_SECRET, str, "string")

        # Strategy
        self._check_type(config, ParamPath.STRATEGY_ACTIVE, (tuple, list), "sequence")

        # Scoring
        self._check_type(
            config,
            ParamPath.SCORE_MINIMUM_SIGNAL_SCORE,
            int,
            "integer",
        )
        self._check_type(
            config, ParamPath.SCORE_PARAMETERS_ACTIVE, (tuple, list), "sequence"
        )

        # Notification
        self._check_type(config, ParamPath.NOTIFICATION_CHANNELS, (tuple, list), "sequence")

    def _validate_parameter_ranges(self, config: AppConfig) -> None:
        """Validate parameter value ranges."""

        # Scoring validation
        if not (0 <= config.scoring.minimum_signal_score <= 100):
            self._errors.append(
                f"Parameter '{ParamPath.SCORE_MINIMUM_SIGNAL_SCORE}' "
                f"must be between 0 and 100, got {config.scoring.minimum_signal_score}"
            )

        if not (
            0 <= config.scoring.minimum_score
            <= config.scoring.maximum_score
            <= 100
        ):
            self._errors.append(
                "Score bounds invalid: minimum_score <= maximum_score <= 100 required"
            )

        # Exchange validation
        if config.exchange.symbols_min > config.exchange.symbols_max:
            self._errors.append(
                f"Parameter '{ParamPath.EXCHANGE_SYMBOLS_MIN}' "
                f"must be <= '{ParamPath.EXCHANGE_SYMBOLS_MAX}'"
            )

        symbols_count = len(config.exchange.symbols)
        if symbols_count < config.exchange.symbols_min:
            self._errors.append(
                f"Exchange symbols count ({symbols_count}) "
                f"is less than minimum ({config.exchange.symbols_min})"
            )

        if symbols_count > config.exchange.symbols_max:
            self._errors.append(
                f"Exchange symbols count ({symbols_count}) "
                f"exceeds maximum ({config.exchange.symbols_max})"
            )

        # Note: symbols can be empty initially - they will be loaded from BingX API at runtime
        # This validation only runs if symbols are explicitly provided

        # Scoring parameters sum validation
        total_max_score = (
            config.scoring.lower_wick_quality.max_score
            + config.scoring.candle_confirmation.max_score
        )
        if total_max_score > config.scoring.maximum_score:
            self._errors.append(
                f"Sum of scoring parameter max_scores ({total_max_score}) "
                f"exceeds maximum_score ({config.scoring.maximum_score})"
            )

        # Strategy validation
        for strategy_id in config.strategy.active:
            if strategy_id not in config.strategy.strategies:
                self._errors.append(
                    f"Active strategy '{strategy_id}' not found in strategy configurations"
                )

        # Risk validation
        if config.risk.take_profit_percent <= 0:
            self._errors.append(f"Parameter '{ParamPath.RISK_TAKE_PROFIT}' must be > 0")
        if config.risk.stop_loss_percent >= 0:
            self._errors.append(f"Parameter '{ParamPath.RISK_STOP_LOSS}' must be < 0")

    def _validate_dependencies(self, config: AppConfig) -> None:
        """Validate parameter dependencies."""

        # Telegram channel requires bot_token and chat_id
        if "telegram" in config.notification.channels:
            if not config.notification.telegram.bot_token:
                self._errors.append(
                    f"Parameter '{ParamPath.NOTIFICATION_TELEGRAM_BOT_TOKEN}' "
                    "is required when 'telegram' is in notification.channels"
                )
            if not config.notification.telegram.chat_id:
                self._errors.append(
                    f"Parameter '{ParamPath.NOTIFICATION_TELEGRAM_CHAT_ID}' "
                    "is required when 'telegram' is in notification.channels"
                )

        # Active scoring parameters must be in parameters_active
        for param_name in (
            ScoringParameter.LOWER_WICK_QUALITY.value,
            ScoringParameter.CANDLE_CONFIRMATION.value,
        ):
            param_config = getattr(config.scoring, param_name)
            if param_config.enabled and param_name not in config.scoring.parameters_active:
                self._errors.append(
                    f"Scoring parameter '{param_name}' is enabled but not in "
                    f"'{ParamPath.SCORE_PARAMETERS_ACTIVE}'"
                )

    def _check_type(
        self, config: AppConfig, path: str, expected_type: type | tuple[type, ...], type_name: str
    ) -> None:
        """Check that a parameter has the correct type."""
        value = self._get_nested_value(config, path)
        if value is not None and not isinstance(value, expected_type):
            self._errors.append(
                f"Parameter '{path}' has invalid type. "
                f"Expected {type_name}, got {type(value).__name__}"
            )

    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get a nested configuration value by dot-separated path."""
        current: Any = obj
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            if current is None:
                return None
        return current