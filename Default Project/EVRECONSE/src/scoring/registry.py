"""
EVRECONSE Scoring - Parameter Registry.

Thread-safe registry for scoring parameters.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from .context import ScoringConfig
from .exceptions import (
    ParameterAlreadyRegisteredError,
    ParameterNotFoundError,
    ParameterNotRegisteredError,
    ScoringValidationError,
)
from .parameter import ScoringParameter


@dataclass(frozen=True, slots=True)
class ParameterRegistration:
    """Immutable parameter registration record."""

    parameter_id: str
    name: str
    version: str
    parameter_class: type
    config: ScoringConfig
    registered_at: str
    enabled: bool = True


class ScoringParameterRegistry:
    """
    Thread-safe registry for scoring parameters.

    Manages parameter registration, lookup, and lifecycle.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._parameters: dict[str, ScoringParameter] = {}
        self._registrations: dict[str, ParameterRegistration] = {}
        self._enabled: set[str] = set()

    def register(
        self,
        parameter: ScoringParameter,
        config: ScoringConfig,
    ) -> None:
        """
        Register a scoring parameter.

        Args:
            parameter: Parameter instance to register
            parameter to register
            config: Parameter configuration

        Raises:
            ParameterAlreadyRegisteredError: If parameter ID already registered
            ScoringValidationError: If validation fails
        """
        with self._lock:
            parameter_id = parameter.parameter_id

            if parameter_id in self._parameters:
                raise ParameterAlreadyRegisteredError(parameter_id)

            # Validate parameter
            try:
                parameter.validate_config(config)
            except Exception as e:
                raise ScoringValidationError(
                    f"Parameter validation failed: {e}",
                    field="parameter"
                ) from e

            # Initialize parameter
            parameter.initialize(config)

            # Store parameter and registration
            self._parameters[parameter_id] = parameter
            self._registrations[parameter_id] = ParameterRegistration(
                parameter_id=parameter.parameter_id,
                name=parameter.name,
                version=parameter.version,
                parameter_class=type(parameter),
                config=config,
                registered_at=datetime.now(UTC).isoformat(),
                enabled=config.enabled,
            )

            if config.enabled:
                self._enabled.add(parameter_id)

    def unregister(self, parameter_id: str) -> None:
        """
        Unregister a parameter.

        Args:
            parameter_id: Parameter identifier

        Raises:
            ParameterNotRegisteredError: If parameter not found
        """
        with self._lock:
            if parameter_id not in self._parameters:
                raise ParameterNotRegisteredError(parameter_id)

            parameter = self._parameters[parameter_id]

            # Shutdown parameter
            try:
                parameter.shutdown()
            except Exception:
                pass  # Best effort

            # Remove from registry
            del self._parameters[parameter_id]
            del self._registrations[parameter_id]
            self._enabled.discard(parameter_id)

    def get(self, parameter_id: str) -> ScoringParameter:
        """
        Get parameter by ID.

        Args:
            parameter_id: Parameter identifier

        Returns:
            Parameter instance

        Raises:
            ParameterNotFoundError: If parameter not found
        """
        with self._lock:
            if parameter_id not in self._parameters:
                raise ParameterNotFoundError(parameter_id)
            return self._parameters[parameter_id]

    def get_registration(self, parameter_id: str) -> ParameterRegistration:
        """
        Get parameter registration info.

        Args:
            parameter_id: Parameter identifier

        Returns:
            Registration record

        Raises:
            ParameterNotFoundError: If parameter not found
        """
        with self._lock:
            if parameter_id not in self._registrations:
                raise ParameterNotFoundError(parameter_id)
            return self._registrations[parameter_id]

    def list_parameters(self, enabled_only: bool = False) -> list[str]:
        """
        List all registered parameter IDs.

        Args:
            enabled_only: If True, only return enabled parameters

        Returns:
            List of parameter IDs
        """
        with self._lock:
            if enabled_only:
                return list(self._enabled)
            return list(self._parameters.keys())

    def get_enabled(self) -> list[str]:
        """Get list of enabled parameter IDs."""
        with self._lock:
            return list(self._enabled)

    def enable(self, parameter_id: str) -> None:
        """
        Enable a parameter.

        Args:
            parameter_id: Parameter identifier

        Raises:
            ParameterNotFoundError: If parameter not found
        """
        with self._lock:
            if parameter_id not in self._parameters:
                raise ParameterNotFoundError(parameter_id)

            self._enabled.add(parameter_id)
            registration = self._registrations[parameter_id]
            self._registrations[parameter_id] = ParameterRegistration(
                parameter_id=registration.parameter_id,
                name=registration.name,
                version=registration.version,
                parameter_class=registration.parameter_class,
                config=registration.config,
                registered_at=registration.registered_at,
                enabled=True,
            )

            # Re-initialize parameter
            parameter = self._parameters[parameter_id]
            config = registration.config
            config.enabled = True
            parameter.initialize(config)

    def disable(self, parameter_id: str) -> None:
        """
        Disable a parameter.

        Args:
            parameter_id: Parameter identifier

        Raises:
            ParameterNotFoundError: If parameter not found
        """
        with self._lock:
            if parameter_id not in self._parameters:
                raise ParameterNotFoundError(parameter_id)

            self._enabled.discard(parameter_id)
            registration = self._registrations[parameter_id]
            self._registrations[parameter_id] = ParameterRegistration(
                parameter_id=registration.parameter_id,
                name=registration.name,
                version=registration.version,
                parameter_class=registration.parameter_class,
                config=registration.config,
                registered_at=registration.registered_at,
                enabled=False,
            )

    def is_enabled(self, parameter_id: str) -> bool:
        """Check if parameter is enabled."""
        with self._lock:
            return parameter_id in self._enabled

    def get_parameter(self, parameter_id: str) -> ScoringParameter:
        """Get parameter by ID (alias for get)."""
        return self.get(parameter_id)

    def get_config(self, parameter_id: str) -> ScoringConfig | None:
        """Get parameter configuration."""
        with self._lock:
            registration = self._registrations.get(parameter_id)
            return registration.config if registration else None

    def update_config(self, parameter_id: str, config: ScoringConfig) -> None:
        """
        Update parameter configuration.

        Args:
            parameter_id: Parameter identifier
            config: New configuration

        Raises:
            ParameterNotFoundError: If parameter not found
            ScoringValidationError: If validation fails
        """
        with self._lock:
            if parameter_id not in self._parameters:
                raise ParameterNotFoundError(parameter_id)

            parameter = self._parameters[parameter_id]

            # Validate new config
            parameter.validate_config(config)

            # Update registration
            registration = self._registrations[parameter_id]
            self._registrations[parameter_id] = ParameterRegistration(
                parameter_id=registration.parameter_id,
                name=registration.name,
                version=registration.version,
                parameter_class=registration.parameter_class,
                config=config,
                registered_at=registration.registered_at,
                enabled=config.enabled,
            )

            # Re-initialize parameter
            parameter.initialize(config)

            # Update enabled set
            if config.enabled:
                self._enabled.add(parameter_id)
            else:
                self._enabled.discard(parameter_id)

    def get_all_parameters(self) -> list[ScoringParameter]:
        """Get all registered parameters."""
        with self._lock:
            return list(self._parameters.values())

    def get_enabled_parameters(self) -> list[ScoringParameter]:
        """Get all enabled parameters."""
        with self._lock:
            return [self._parameters[pid] for pid in self._enabled]

    def count(self) -> int:
        """Get number of registered parameters."""
        with self._lock:
            return len(self._parameters)

    def clear(self) -> None:
        """Clear all parameters (for testing)."""
        with self._lock:
            for param in self._parameters.values():
                try:
                    param.shutdown()
                except Exception:
                    pass
            self._parameters.clear()
            self._registrations.clear()
            self._enabled.clear()


# Singleton registry instance
_registry: ScoringParameterRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ScoringParameterRegistry:
    """Get the global parameter registry singleton."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ScoringParameterRegistry()
        return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    with _registry_lock:
        if _registry is not None:
            _registry.clear()
            _registry = None