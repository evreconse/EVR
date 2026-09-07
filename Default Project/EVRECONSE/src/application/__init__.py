"""
EVRECONSE Application Layer.

Top-level application composition and lifecycle management.
"""

from .application import (
    Application,
    ApplicationInfo,
    create_application,
)
from .bootstrap import (
    BootstrapContext,
    bootstrap,
    shutdown,
)
from .exceptions import (
    ApplicationError,
    BootstrapError,
    DependencyError,
    HealthCheckError,
    LifecycleError,
    ReloadError,
    ServiceNotFoundError,
    ServiceRegistrationError,
    ShutdownError,
    StartupError,
)
from .health import (
    ComponentHealth,
    HealthChecker,
    HealthReport,
    HealthStatus,
    create_standard_health_checker,
)
from .lifecycle import (
    ApplicationState,
    LifecycleManager,
    LifecycleMetrics,
)
from .service_container import (
    ServiceContainer,
    get_container,
    reset_container,
    set_container,
)

__all__ = [
    # Main Application
    "Application",
    "ApplicationInfo",
    "create_application",
    # Bootstrap
    "BootstrapContext",
    "bootstrap",
    "shutdown",
    # Lifecycle
    "LifecycleManager",
    "ApplicationState",
    "LifecycleMetrics",
    # DI Container
    "ServiceContainer",
    "get_container",
    "set_container",
    "reset_container",
    # Health
    "HealthChecker",
    "HealthReport",
    "ComponentHealth",
    "HealthStatus",
    "create_standard_health_checker",
    # Exceptions
    "ApplicationError",
    "BootstrapError",
    "ServiceRegistrationError",
    "ServiceNotFoundError",
    "LifecycleError",
    "HealthCheckError",
    "StartupError",
    "ShutdownError",
    "ReloadError",
    "DependencyError",
]