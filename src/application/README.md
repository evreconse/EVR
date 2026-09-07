# EVRECONSE Application Layer

The Application Layer is the top-level composition layer that assembles all lower layers into a cohesive trading bot application.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ Application  │  │ Lifecycle   │  │ ServiceContainer │   │
│  │ (Facade)     │  │ Manager     │  │ (DI)             │   │
│  └──────┬───────┘  └──────┬──────┘  └────────┬─────────┘   │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Bootstrap                           │    │
│  │  Creates and wires all components in dependency order│    │
│  └─────────────────────────────────────────────────────┘    │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌─────────┐    ┌───────────────┐    ┌─────────────────┐  │
│  │ Config  │    │   Storage     │    │  Data Provider  │  │
│  │ Manager │    │   Engine      │    │  (Bybit)        │  │
│  └────┬────┘    └───────┬───────┘    └────────┬────────┘  │
│       │                 │                     │            │
│       └─────────────────┼─────────────────────┘            │
│                         ▼                                   │
│               ┌───────────────────┐                         │
│               │  Strategy Engine  │                         │
│               └─────────┬─────────┘                         │
│                         ▼                                   │
│               ┌───────────────────┐                         │
│               │  Scoring Engine   │                         │
│               └─────────┬─────────┘                         │
│                         ▼                                   │
│               ┌───────────────────┐                         │
│               │  Notification     │                         │
│               └─────────┬─────────┘                         │
│                         ▼                                   │
│               ┌───────────────────┐                         │
│               │  Event Engine     │                         │
│               └───────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Initialization Order

Components are initialized in strict dependency order:

1. **Configuration** - No dependencies
2. **Storage** - Depends on config
3. **Data Provider** - Depends on config
4. **Strategy Engine** - Depends on config + data provider
5. **Scoring Engine** - Depends on config
6. **Notification** - Depends on config
7. **Event Engine** - Depends on config

Shutdown occurs in reverse order.

## Quick Start

```python
from application import Application, create_application

# Simple usage with auto-start
app = await create_application(config_path="config.yaml", auto_start=True)

# Or manual control
app = Application(config_path="config.yaml")
app.initialize()
await app.start()

# Health check
report = await app.health_check()
print(f"Status: {report.status.value}")

# Graceful shutdown
await app.stop()
```

## Public API

### Application (Main Facade)

```python
from application import Application

app = Application(config_path="config.yaml")

# Lifecycle (idempotent)
app.initialize()          # Initialize all components
await app.start()         # Start all components
await app.stop()          # Graceful shutdown
await app.shutdown()      # Alias for stop()
await app.reload()        # Reload config + restart

# Component Access (explicit, no Service Locator)
config = app.get_config()
storage = app.get_storage()
provider = app.get_data_provider()
strategies = app.get_strategy_engine()
scoring = app.get_scoring_engine()
notifications = app.get_notification_engine()
events = app.get_event_engine()

# Health
report = await app.health_check()
component = await app.health_check("data_provider")

# State
print(app.state)           # ApplicationState
print(app.is_running)      # bool
print(app.info)            # ApplicationInfo
print(app.metrics)         # LifecycleMetrics
```

### Lifecycle Manager (Internal)

```python
from application import LifecycleManager, ApplicationState

manager = LifecycleManager(config_path="config.yaml")
context = manager.initialize()
await manager.start()
await manager.stop(timeout=30.0)
await manager.reload()

# State tracking
print(manager.state)       # ApplicationState
print(manager.metrics)     # LifecycleMetrics
```

### Service Container (DI)

```python
from application import ServiceContainer, get_container

# Explicit registration (no auto-wiring)
container = ServiceContainer()
container.register_singleton(Config, lambda: AppConfig(...))
container.register_instance(Logger, my_logger)
container.register_transient(RequestHandler, lambda: RequestHandler(...))

# Resolution
config = container.resolve(Config)
handler = container.resolve(RequestHandler)

# Global container (for cross-cutting concerns)
get_container()
set_container(my_container)  # testing
reset_container()             # testing
```

### Health Checks

```python
from application import (
    HealthChecker,
    HealthReport,
    ComponentHealth,
    HealthStatus,
    create_standard_health_checker,
)

checker = HealthChecker()

# Register custom check
checker.register("my_service", lambda: check_my_service())

# Run checks
report = await checker.check_all()
print(report.is_healthy)  # bool
print(report.to_dict())   # dict

# Single component
health = await checker.check_component("data_provider")

# Standard checker with all components
checker = create_standard_health_checker(
    data_provider=provider,
    storage=storage,
    strategy_engine=strategies,
    scoring_engine=scoring,
    notification_engine=notifications,
    event_engine=events,
)
```

## Exceptions

```python
from application import (
    ApplicationError,
    BootstrapError,
    ServiceRegistrationError,
    ServiceNotFoundError,
    LifecycleError,
    HealthCheckError,
    StartupError,
    ShutdownError,
    ReloadError,
    ConfigurationError,
    DependencyError,
)
```

All exceptions inherit from `ApplicationError` and include:
- `component` - Which component failed
- `reason` - Detailed failure reason
- `operation` - Which operation (startup/shutdown/reload)

## Thread Safety

- `Application`: Thread-safe for all public methods
- `LifecycleManager`: Thread-safe with RLock
- `ServiceContainer`: Thread-safe with RLock
- `HealthChecker`: Async-safe with asyncio.Lock
- All dataclasses are frozen/immutable (`frozen=True, slots=True`)

## Configuration

Configuration is loaded from YAML file via `ConfigurationManager`:

```yaml
# config.yaml
system:
  max_concurrent_events: 10
  execution_timeout_seconds: 30
  enable_metrics: true

storage:
  base_path: "./data"
  max_file_size_mb: 100
  retention_days: 30

exchange:
  api_key: "your_key"
  api_secret: "your_secret"
  testnet: false

strategy:
  default_timeframe: "15m"
  max_concurrent_strategies: 5

scoring:
  default_threshold: 80.0
  min_confidence: 50.0

notification:
  telegram:
    bot_token: "token"
    chat_id: "chat_id"
```

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **SRP** | Each class has single responsibility |
| **OCP** | Extension via protocols/factories |
| **LSP** | All implementations honor contracts |
| **ISP** | Fine-grained protocols for DI |
| **DIP** | Application depends on abstractions |

## No Circular Dependencies

```
Application Layer
       │
       ├── Config (no deps)
       ├── Storage (depends on Config)
       ├── Data Provider (depends on Config)
       ├── Strategy Engine (depends on Config, Data Provider)
       ├── Scoring Engine (depends on Config)
       ├── Notification (depends on Config)
       └── Event Engine (depends on Config)
```

## Production Requirements Met

- ✅ Timezone-aware datetime
- ✅ `time.monotonic()` for measurements
- ✅ Immutable dataclasses (`frozen=True, slots=True`)
- ✅ Full type annotations
- ✅ Protocol-based DI
- ✅ Zero mutable shared state
- ✅ No global singletons (except explicit container)
- ✅ Fail-fast with specialized exceptions
- ✅ Graceful shutdown with timeout
- ✅ Idempotent lifecycle operations
- ✅ Comprehensive health checking