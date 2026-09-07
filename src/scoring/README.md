# Scoring Module

Scoring engine, parameter registry, and parameter implementations.

## Files

| File | Purpose |
|------|---------|
| `context.py` | ScoringContext, ScoringConfig, ScoringResult, ScoreContribution, Penalty |
| `parameter.py` | ScoringParameter abstract interface |
| `scoring_engine.py` | ScoringEngine - execution engine |
| `registry.py` | ScoringParameterRegistry - thread-safe registry |
| `parameters/` | Parameter implementations |
| `exceptions.py` | Scoring exceptions |
| `__init__.py` | Public API exports |
| `README.md` | This file |

## Architecture

```
ScoringEngine (execution) 
    ↓ uses
ScoringParameterRegistry (registry)
    ↓ manages
ScoringParameter (abstract interface)
    ↓ implemented by
LowerWickQualityScore, LiquidationStrengthScore, CandleConfirmationScore, ...
    ↓ uses
ScoringContext (immutable input)
    ↓ returns
ScoringResult (immutable output)
```

## Core Components

### ScoringParameter (Abstract Base)

All scoring parameters must implement:
- `parameter_id` - Unique identifier
- `name`, `version`, `description` - Metadata
- `max_score` - Maximum possible score
- `weight` - Weight in final score (0.0 to 1.0)
- `min_score` - Minimum score (usually 0.0)
- `supports(context)` - Quick compatibility check
- `validate_config(config)` - Config validation
- `evaluate(context)` - Core evaluation logic (async)
- `initialize(config)` - One-time setup
- `shutdown()` - Cleanup

### ScoringEngine

Execution engine with:
- Concurrent parameter evaluation
- Timeout protection (default 5s)
- Error isolation
- Metrics collection

```python
engine = ScoringEngine(
    config=ScoringEngineConfig(
        max_concurrent_parameters=10,
        execution_timeout=5.0,
    ),
    registry=registry,
)

result = await engine.evaluate(scoring_context)
```

### ScoringParameterRegistry

Thread-safe registry with:
- Registration/unregistration
- Enable/disable parameters
- Config management
- Thread-safe lookups

```python
registry = get_registry()
registry.register(lower_wick_param, config)
registry.enable("lower_wick_quality")
param = registry.get("lower_wick_quality")
```

### Parameter Implementations

| Parameter | Max Score | Weight | Description |
|-----------|-----------|--------|-------------|
| LowerWickQualityScore | 40 | 40% | Wick-to-body ratio quality |
| LiquidationStrengthScore | 35 | 35% | Liquidation volume vs average |
| CandleConfirmationScore | 25 | 25% | Candle body confirmation |

**Total: 100 points max**

### ScoringContext / ScoringResult

```python
# Create context
context = ScoringContext(
    market_event=event,
    config=scoring_config,
    data_provider=provider,
    storage=storage,
)

# Evaluate
result = await engine.evaluate(context)

# Check result
if result.qualified:
    print(f"Score: {result.final_score}/{result.max_score}")
    print(f"Explanation: {result.explanation}")
```

## Configuration

```python
scoring_config = ScoringConfig(
    scoring_id="lw_001_scoring",
    version="1.0",
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
```

## Extending with New Parameters

```python
class MyCustomScore:
    @property
    def parameter_id(self) -> str:
        return "my_custom"
    
    @property
    def max_score(self) -> float:
        return 20.0
    
    @property
    def weight(self) -> float:
        return 0.2
    
    @property
    def min_score(self) -> float:
        return 0.0
    
    def supports(self, context: ScoringContext) -> bool:
        return True
    
    def validate_config(self, config: ScoringConfig) -> None:
        pass
    
    async def evaluate(self, context: ScoringContext) -> tuple[float, list[Penalty], str]:
        # Your evaluation logic
        return 10.0, [], "Custom explanation"
    
    def initialize(self, config: ScoringConfig) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass

# Register
registry.register(MyCustomScore(), config)
```