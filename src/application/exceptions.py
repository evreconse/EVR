"""
EVRECONSE Application Layer - Exceptions.

Application-specific exception hierarchy.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Base exception for application layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class BootstrapError(ApplicationError):
    """Raised when application bootstrap fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.component = component
        self.reason = reason
        msg = message
        if component:
            msg = f"[{component}] {message}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class ServiceRegistrationError(ApplicationError):
    """Raised when service registration fails."""

    def __init__(
        self,
        message: str,
        service_type: type | None = None,
        reason: str | None = None,
    ) -> None:
        self.service_type = service_type
        self.reason = reason
        msg = message
        if service_type:
            msg = f"[{service_type.__name__}] {message}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class ServiceNotFoundError(ApplicationError):
    """Raised when requested service is not registered."""

    def __init__(self, service_type: type, message: str | None = None) -> None:
        self.service_type = service_type
        msg = message or f"Service not found: {service_type.__name__}"
        super().__init__(msg)


class LifecycleError(ApplicationError):
    """Raised when lifecycle operation fails."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.operation = operation
        self.component = component
        self.reason = reason
        msg = message
        if operation:
            msg = f"[{operation}] {message}"
        if component:
            msg = f"[{component}] {msg}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class HealthCheckError(ApplicationError):
    """Raised when health check fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.component = component
        self.reason = reason
        msg = message
        if component:
            msg = f"[{component}] {message}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StartupError(LifecycleError):
    """Raised when startup fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, operation="startup", component=component, reason=reason)


class ShutdownError(LifecycleError):
    """Raised when shutdown fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, operation="shutdown", component=component, reason=reason)


class ReloadError(LifecycleError):
    """Raised when reload fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, operation="reload", component=component, reason=reason)


class DependencyError(ApplicationError):
    """Raised when dependency resolution fails."""

    def __init__(
        self,
        message: str,
        dependency: str | None = None,
    ) -> None:
        self.dependency = dependency
        msg = message
        if dependency:
            msg = f"[{dependency}] {message}"
        super().__init__(msg)