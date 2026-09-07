"""
EVRECONSE Application Layer - Service Container.

Lightweight Dependency Injection Container with singleton and factory support.
Thread-safe, no Service Locator anti-pattern.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, get_type_hints

from core import get_logger

from .exceptions import ServiceNotFoundError, ServiceRegistrationError

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ServiceRegistration(Generic[T]):
    """Immutable service registration record."""
    service_type: type[T]
    factory: Callable[[], T] | None
    instance: T | None
    is_singleton: bool
    dependencies: tuple[type, ...]


class ServiceContainer:
    """
    Lightweight thread-safe DI container.

    Supports:
    - Singleton registration (instance or factory)
    - Factory registration (new instance each time)
    - Type-based resolution
    - Dependency auto-resolution via type hints
    - No Service Locator pattern - explicit registration only

    Example:
        container = ServiceContainer()
        container.register_singleton(Config, lambda: load_config())
        container.register_factory(Database, lambda: Database(container.get(Config)))
        db = container.get(Database)
    """

    def __init__(self) -> None:
        self._services: dict[type, ServiceRegistration] = {}
        self._lock = threading.RLock()
        self._resolving: set[type] = set()  # For circular dependency detection

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """
        Register a singleton instance.

        Args:
            service_type: Service type (interface or class)
            instance: Pre-created instance

        Raises:
            ServiceRegistrationError: If already registered
        """
        with self._lock:
            if service_type in self._services:
                raise ServiceRegistrationError(
                    "Service already registered",
                    service_type=service_type,
                    reason="Use unregister() first",
                )

            reg = ServiceRegistration(
                service_type=service_type,
                factory=None,
                instance=instance,
                is_singleton=True,
                dependencies=(),
            )
            self._services[service_type] = reg
            logger.debug("Registered singleton instance: %s", service_type.__name__)

    def register_singleton(
        self,
        service_type: type[T],
        factory: Callable[[], T] | None = None,
    ) -> None:
        """
        Register a singleton with optional factory.

        Args:
            service_type: Service type
            factory: Factory function (called once on first get)

        Raises:
            ServiceRegistrationError: If already registered
        """
        with self._lock:
            if service_type in self._services:
                raise ServiceRegistrationError(
                    "Service already registered",
                    service_type=service_type,
                    reason="Use unregister() first",
                )

            # Auto-detect dependencies from factory signature
            deps = ()
            if factory:
                deps = self._extract_dependencies(factory)

            reg = ServiceRegistration(
                service_type=service_type,
                factory=factory,
                instance=None,
                is_singleton=True,
                dependencies=deps,
            )
            self._services[service_type] = reg
            logger.debug("Registered singleton factory: %s", service_type.__name__)

    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[[], T],
    ) -> None:
        """
        Register a factory (new instance each get).

        Args:
            service_type: Service type
            factory: Factory function

        Raises:
            ServiceRegistrationError: If already registered
        """
        with self._lock:
            if service_type in self._services:
                raise ServiceRegistrationError(
                    "Service already registered",
                    service_type=service_type,
                    reason="Use unregister() first",
                )

            deps = self._extract_dependencies(factory)

            reg = ServiceRegistration(
                service_type=service_type,
                factory=factory,
                instance=None,
                is_singleton=False,
                dependencies=deps,
            )
            self._services[service_type] = reg
            logger.debug("Registered factory: %s", service_type.__name__)

    def _extract_dependencies(self, factory: Callable) -> tuple[type, ...]:
        """Extract parameter types from factory signature."""
        try:
            hints = get_type_hints(factory)
            # Return all parameter types except return type
            return tuple(h for h in hints.values() if h != "return")
        except Exception:
            return ()

    def unregister(self, service_type: type) -> bool:
        """
        Unregister a service.

        Args:
            service_type: Service type to remove

        Returns:
            True if was registered, False otherwise
        """
        with self._lock:
            if service_type in self._services:
                del self._services[service_type]
                logger.debug("Unregistered service: %s", service_type.__name__)
                return True
            return False

    def get(self, service_type: type[T]) -> T:
        """
        Resolve and return service instance.

        Args:
            service_type: Service type to resolve

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If not registered
            ServiceRegistrationError: If circular dependency detected
        """
        with self._lock:
            if service_type not in self._services:
                raise ServiceNotFoundError(service_type)

            reg = self._services[service_type]

            # Circular dependency detection
            if service_type in self._resolving:
                cycle = " -> ".join(t.__name__ for t in self._resolving) + f" -> {service_type.__name__}"
                raise ServiceRegistrationError(
                    "Circular dependency detected",
                    service_type=service_type,
                    reason=f"Cycle: {cycle}",
                )

            self._resolving.add(service_type)

        try:
            if reg.instance is not None:
                return reg.instance

            if reg.factory is None:
                raise ServiceRegistrationError(
                    "No factory for service",
                    service_type=service_type,
                    reason="Singleton without instance or factory",
                )

            # Resolve dependencies and call factory
            kwargs = {}
            for dep_type in reg.dependencies:
                kwargs[dep_type.__name__] = self.get(dep_type)

            instance = reg.factory(**kwargs) if kwargs else reg.factory()

            if reg.is_singleton:
                with self._lock:
                    # Double-check pattern
                    if self._services[service_type].instance is None:
                        self._services[service_type] = ServiceRegistration(
                            service_type=reg.service_type,
                            factory=reg.factory,
                            instance=instance,
                            is_singleton=reg.is_singleton,
                            dependencies=reg.dependencies,
                        )

            return instance

        finally:
            with self._lock:
                self._resolving.discard(service_type)

    def get_optional(self, service_type: type[T]) -> T | None:
        """
        Resolve service or return None if not registered.

        Args:
            service_type: Service type to resolve

        Returns:
            Service instance or None
        """
        try:
            return self.get(service_type)
        except ServiceNotFoundError:
            return None

    def has(self, service_type: type) -> bool:
        """Check if service is registered."""
        with self._lock:
            return service_type in self._services

    def get_all(self) -> dict[type, ServiceRegistration]:
        """Get all registrations (for debugging/inspection)."""
        with self._lock:
            return dict(self._services)

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        with self._lock:
            self._services.clear()
            self._resolving.clear()


# Global container instance (explicitly managed, not singleton pattern)
_global_container: ServiceContainer | None = None
_container_lock = threading.Lock()


def get_container() -> ServiceContainer:
    """Get global container (lazy initialization)."""
    global _global_container
    with _container_lock:
        if _global_container is None:
            _global_container = ServiceContainer()
        return _global_container


def set_container(container: ServiceContainer) -> None:
    """Set global container (for testing/initialization)."""
    global _global_container
    with _container_lock:
        _global_container = container


def reset_container() -> None:
    """Reset global container (for testing)."""
    global _global_container
    with _container_lock:
        _global_container = None