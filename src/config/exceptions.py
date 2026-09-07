"""
Configuration exceptions for EVRECONSE.

All configuration-related exceptions are defined here.
"""

from __future__ import annotations


class ConfigurationError(Exception):
    """Base exception for configuration errors."""

    def __init__(self, message: str, parameter_path: str | None = None) -> None:
        self.parameter_path = parameter_path
        super().__init__(message)


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        parameter_path: str | None = None,
        expected_type: str | None = None,
        actual_value: object | None = None,
    ) -> None:
        self.expected_type = expected_type
        self.actual_value = actual_value
        super().__init__(message, parameter_path)


class MissingRequiredParameterError(ConfigurationError):
    """Raised when a required parameter is missing."""

    def __init__(self, parameter_path: str) -> None:
        message = f"Required parameter '{parameter_path}' is missing"
        super().__init__(message, parameter_path)


class InvalidParameterTypeError(ValidationError):
    """Raised when a parameter has an invalid type."""

    def __init__(
        self, parameter_path: str, expected_type: str, actual_value: object
    ) -> None:
        message = (
            f"Parameter '{parameter_path}' has invalid type. "
            f"Expected {expected_type}, got {type(actual_value).__name__}"
        )
        super().__init__(message, parameter_path, expected_type, actual_value)


class ParameterOutOfRangeError(ValidationError):
    """Raised when a parameter value is out of allowed range."""

    def __init__(
        self,
        parameter_path: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        if min_value is not None and max_value is not None:
            message = f"Parameter '{parameter_path}' must be between {min_value} and {max_value}"
        elif min_value is not None:
            message = f"Parameter '{parameter_path}' must be >= {min_value}"
        elif max_value is not None:
            message = f"Parameter '{parameter_path}' must be <= {max_value}"
        else:
            message = f"Parameter '{parameter_path}' is out of allowed range"
        super().__init__(message, parameter_path)


class DependencyValidationError(ConfigurationError):
    """Raised when parameter dependencies are violated."""

    def __init__(self, message: str, parameter_path: str | None = None) -> None:
        super().__init__(message, parameter_path)


class ConfigurationVersionError(ConfigurationError):
    """Raised when configuration schema version is incompatible."""

    def __init__(self, current_version: str, required_version: str) -> None:
        message = (
            f"Configuration version mismatch: current {current_version}, "
            f"required {required_version}. Major version mismatch - "
            "configuration is incompatible."
        )
        super().__init__(message)


class InvalidParameterError(ValidationError):
    """Raised when a parameter value is invalid for other reasons."""

    def __init__(self, parameter_path: str, reason: str) -> None:
        message = f"Parameter '{parameter_path}' is invalid: {reason}"
        super().__init__(message, parameter_path)


class ConfigurationNotInitializedError(ConfigurationError):
    """Raised when accessing configuration before initialization."""

    def __init__(self) -> None:
        super().__init__("ConfigurationManager is not initialized")


class HotReloadError(ConfigurationError):
    """Raised when hot reload of configuration fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SecretsNotFoundError(ConfigurationError):
    """Raised when required secrets are not found in environment variables."""

    def __init__(self, missing_secrets: list[str]) -> None:
        message = f"Missing required secrets: {', '.join(missing_secrets)}"
        super().__init__(message)
        self.missing_secrets = missing_secrets