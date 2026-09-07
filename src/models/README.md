# Models Module

Core domain models for EVRECONSE.

## Files

| File | Purpose |
|------|---------|
| `enums.py` | Domain enumerations (EventStatus, EventOutcome, Exchange, Timeframe, etc.) |
| `identifiers.py` | Type-safe EventID, SignalID (UUID wrappers) |
| `market_event.py` | Main MarketEvent with nested dataclasses and factory methods |
| `exceptions.py` | ModelValidationError, InvalidTransitionError, InvariantViolationError |
| `__init__.py` | Public API exports |

## Architecture Compliance

- **Immutable**: All dataclasses `frozen=True, slots=True`
- **Type-safe**: Full type hints, no `Any` in public API
- **State machine**: Factory methods enforce valid lifecycle transitions
- **SRP**: Each nested dataclass = one logical data group
- **No business logic**: Only data structure + safe transitions
- **Strategy-agnostic**: No LW-001 or any strategy-specific logic
- **Timezone-aware**: All datetime use UTC timezone-aware objects
- **Immutable transition map**: `_TransitionMap` with immutable `frozenset` transitions

## Corresponding Documents

- MARKET_EVENT_SCHEMA.md
- EVENT_ENGINE.md
- SYSTEM_ARCHITECTURE.md

## Factory Methods (ONLY way to create MarketEvent)

```python
MarketEvent.new(...)              # NEW
event.qualified(...)              # QUALIFIED
event.scored(...)                 # SCORED
event.notified(...)               # SIGNAL
event.dismissed(...)              # DISMISSED
event.monitoring(...)             # MONITORING
event.completed(...)              # COMPLETED
event.expired(...)                # EXPIRED
```

## Serialization

```python
event.to_dict()   # -> dict (JSON-serializable)
MarketEvent.from_dict(data)  # -> MarketEvent (validated)
```

Round-trip: `event == MarketEvent.from_dict(event.to_dict())` ✓