# Event Engine Module

Core orchestration engine for event processing pipeline.

## Architecture

```
EventEngine (orchestration)
    ↓ uses
EventPipeline (pipeline execution)
    ↓ uses
EventRegistry (state management)
EventScheduler (time-based operations)
EventDispatcher (internal events)
EventFactory (event creation)
StateMachine (state transitions)
TransitionGuard (transition validation)
Metrics (observability)
```

## Components

| Component | Purpose |
|-----------|---------|
| `EventEngine` | Main orchestration engine |
| `EventPipeline` | Sequential stage execution |
| `EventRegistry` | Thread-safe event registry with indices |
| `EventScheduler` | Priority queue scheduler with cron-like tasks |
| `EventDispatcher` | Pub/sub with filters, priorities, once |
| `EventFactory` | MarketEvent creation via Model factory methods |
| `StateMachine` | State transitions with centralized guards |
| `TransitionGuard` | Centralized transition validation |
| `MetricsCollector` | Counters, gauges, histograms |

## Usage

```python
from src.event_engine import EventEngine, EngineConfig

# Create engine
engine = EventEngine(config={
    "max_concurrent_events": 10,
    "execution_timeout": 30.0,
    "enable_metrics": True,
})

# Initialize components
engine.initialize()

# Start engine
engine.start()

# Process market data
result = engine.process_market_data(
    symbol="BTCUSDT",
    exchange="bybit",
    timeframe="15m",
    event_time=datetime.now(timezone.utc),
    open_price=50000.0,
    high_price=50100.0,
    low_price=49900.0,
    close_price=50050.0,
    volume=100.5,
)

# Get stats
stats = engine.get_stats()

# Shutdown
engine.stop()
```

## Architecture

```
EventEngine (orchestration)
    ↓ uses
EventPipeline (pipeline execution)
    ↓ uses
EventRegistry (state management)
EventScheduler (time-based operations)
EventDispatcher (internal events)
EventFactory (event creation)
StateMachine (state transitions)
TransitionGuard (transition validation)
Metrics (observability)
```

## Pipeline Stages

1. **Validator** - Validates event before processing
2. **Strategy** - Strategy evaluation
3. **Scorer** - Confidence scoring
4. **Notifier** - Notification delivery
5. **OutcomeTracker** - TP/SL tracking
6. **Storage** - Persistence

## State Machine

```
NEW → QUALIFIED → SCORED → SIGNAL → MONITORING → COMPLETED
                    ↓              ↓
               DISMISSED       EXPIRED/FAILED/COMPLETED
```

## Usage

```python
from src.event_engine import EventEngine, EngineConfig

engine = EventEngine(config={
    "max_concurrent_events": 10,
    "execution_timeout": 30.0,
    "enable_metrics": True,
})

engine.initialize()
engine.start()

result = engine.process_market_data(
    symbol="BTCUSDT",
    exchange="bybit",
    timeframe="15m",
    event_time=datetime.now(timezone.utc),
    open_price=50000.0,
    high_price=50100.0,
    low_price=49900.0,
    close_price=50050.0,
    volume=100.5,
)

print(f"Event: {result['event_id']}, Status: {result['final_status']}")

engine.stop()
```