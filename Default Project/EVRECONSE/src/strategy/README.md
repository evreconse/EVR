# Strategy Module

Strategy management, execution engine, and LW-001 implementation.

## Files

| File | Purpose |
|------|---------|
| `context.py` | StrategyContext, StrategyConfig, StrategyResult, ScoreContribution, Penalty |
| `strategy.py` | Strategy abstract interface |
| `strategy_engine.py` | StrategyEngine - execution engine |
| `registry.py` | StrategyRegistry - thread-safe registry |
| `lw_001.py` | LW-001 Long Lower Wick Reversal implementation |
| `exceptions.py` | Strategy-specific exceptions |
| `__init__.py` | Public API exports |
| `README.md` | This file |

## Architecture

```
StrategyEngine (execution) 
    ↓ uses
StrategyRegistry (registry)
    ↓ manages
Strategy (abstract interface)
    ↓ implemented by
LW001Strategy (concrete)
    ↓ uses
StrategyContext (immutable input)
    ↓ returns
StrategyResult (immutable output)
```

## Core Components

### Strategy (Abstract Base)

All strategies must implement:
- `strategy_id` - Unique identifier
- `name`, `version`, `description` - Metadata
- `supported_markets`, `supported_timeframes` - Compatibility
- `supports(context)` - Quick compatibility check
- `validate_config(config)` - Config validation
- `evaluate(context)` - Core evaluation logic (async)
- `initialize(config)` - One-time setup
- `shutdown()` - Cleanup

### StrategyEngine

Execution engine with:
- Concurrent strategy execution
- Timeout protection (default 5s)
- Error isolation
- Metrics collection

```python
engine = StrategyEngine(
    config=StrategyEngineConfig(
        max_concurrent_strategies=10,
        execution_timeout=5.0,
    ),
    data_provider=provider,
    config_manager=config_manager,
)

engine.register_strategy(lw001, config)
engine.activate_strategy("LW-001")

results = await engine.process_event(market_event)
```

### StrategyRegistry

Thread-safe registry with:
- Registration/unregistration
- Enable/disable strategies
- Config management
- Thread-safe lookups

```python
registry = get_registry()
registry.register(lw001_strategy, config)
registry.enable("LW-001")
strategy = registry.get("LW-001")
```

### LW-001: Long Lower Wick Reversal

Detects bullish reversal patterns with:
- Long lower wick (≥2x body by default)
- Elevated liquidation volume
- Bullish candle confirmation

**Scoring (100 points max):**
| Component | Max Points | Weight |
|-----------|------------|--------|
| Lower Wick Quality | 40 | 40% |
| Liquidation Strength | 35 | 35% |
| Candle Confirmation | 25 | 25% |

**Penalties:**
- Doji candle: -5
- Wick below threshold: -10
- Low liquidation volume: -5
- Bearish close: -10

**Config Parameters:**
```python
config = StrategyConfig(
    strategy_id="LW-001",
    version="1.0.0",
    enabled=True,
    parameters={
        "lower_wick_ratio": 2.0,      # Wick/body ratio threshold
        "liquidation_window": 12,     # Candles for liquidation average
        "min_confidence_score": 80,   # Min score to qualify
        "scoring_weights": {
            "lower_wick_quality": 40,
            "liquidation_strength": 35,
            "candle_confirmation": 25,
        }
    }
)
```

## Integration

```python
from src.strategy import (
    StrategyEngine,
    StrategyEngineConfig,
    LW001Strategy,
    StrategyConfig,
)
from src.data_provider import BybitDataProvider

# Setup
provider = BybitDataProvider(api_key="...", api_secret="...")
config = StrategyEngineConfig(max_concurrent_strategies=10, execution_timeout=5.0)

engine = StrategyEngine(
    config=StrategyEngineConfig(),
    data_provider=provider,
)

# Register strategy
lw001 = LW001Strategy()
config = StrategyConfig(
    strategy_id="LW-001",
    version="1.0.0",
    enabled=True,
    parameters={
        "lower_wick_ratio": 2.0,
        "liquidation_window": 12,
        "min_confidence_score": 80,
        "scoring_weights": {
            "lower_wick_quality": 40,
            "liquidation_strength": 35,
            "candle_confirmation": 25,
        }
    }
)
engine.register_strategy(lw001, config)
engine.activate_strategy("LW-001")

# Connect to data provider
await provider.connect()
await provider.subscribe_symbols(["BTCUSDT", "ETHUSDT"], "15m")

# Process events
async for event in provider.stream():
    results = await engine.process_event(event)
    for result in results:
        if result.qualified:
            print(f"SIGNAL: {result.strategy_id} {result.explanation}")
```

## Extending with New Strategies

```python
class MyCustomStrategy:
    @property
    def strategy_id(self) -> str:
        return "MY-001"
    
    @property
    def name(self) -> str:
        return "My Custom Strategy"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "My custom trading strategy"
    
    @property
    def supported_markets(self) -> list[str]:
        return ["bybit"]
    
    @property
    def supported_timeframes(self) -> list[str]:
        return ["15m", "1h"]
    
    def supports(self, context: StrategyContext) -> bool:
        return True
    
    def validate_config(self, config: StrategyConfig) -> None:
        pass
    
    async def evaluate(self, context: StrategyContext) -> StrategyResult:
        # Your evaluation logic here
        return StrategyResult(
            qualified=False,
            final_score=0,
            max_score=100,
            contributions=(),
            penalties=(),
            strategy_id=self.strategy_id,
            strategy_version=self.version,
            evaluation_id=context.evaluation_id,
            evaluated_at=datetime.now(timezone.utc),
            execution_time_ms=0,
        )
    
    def initialize(self, config: StrategyConfig) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass

# Register
engine.register_strategy(MyCustomStrategy(), config)
```