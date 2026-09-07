# EVRECONSE Project Structure

## Module Overview

| Folder | Module | Purpose | Architecture Document |
|--------|--------|---------|----------------------|
| `core/` | Core Infrastructure | Shared utilities, base classes, exceptions, constants | SYSTEM_ARCHITECTURE.md, CONFIGURATION_SYSTEM.md |
| `providers/` | Data Provider | WebSocket connection to exchange, market data validation & normalization | DATA_PROVIDER_ARCHITECTURE.md |
| `strategies/` | Strategy Engine | Strategy registry, market data delegation, qualified event creation | STRATEGY_ENGINE.md, LW-001.md |
| `scoring/` | Scoring Engine | Confidence score calculation, parameter evaluation, explainability | SCORING.md |
| `notifications/` | Notification Service | Threshold comparison, alert dispatch (Telegram MVP) | EVENT_ENGINE.md |
| `storage/` | Storage Service | Event persistence (Market Events, Signals, Outcomes) | MARKET_EVENT_SCHEMA.md |
| `outcome/` | Outcome Tracker | TP/SL monitoring, result recording | SYSTEM_ARCHITECTURE.md §3.6 |
| `config/` | Configuration Manager | Config loading, validation, hot-reload, secrets | CONFIGURATION_SYSTEM.md |
| `models/` | Data Models | Event schemas, DTOs, field definitions | MARKET_EVENT_SCHEMA.md |
| `utils/` | Utilities | Logging, time, validation helpers | — |

---

## Module Interactions (Data Flow)

```
Data Provider (providers/)
    │
    ▼ (raw market data: closed M15 candles + liquidations)
Strategy Engine (strategies/)
    │
    ├── creates Market Event for every closed candle
    ├── delegates to each active Strategy (LW-001, ...)
    │   └── Strategy returns: confirmed / not confirmed + metrics
    │
    ▼ (Qualified Events)
Scoring Engine (scoring/)
    │
    ▼ (Confidence Score + Breakdown)
Notification Service (notifications/)
    │
    ├── Score >= Threshold → Signal + Telegram
    │
    ▼ (Signal)
Outcome Tracker (outcome/)
    │
    ▼ (price monitoring → Outcome: TP / SL / Expired)
Storage Service (storage/) ← async copy at every stage
    │
    ▼
    Persisted: Market Events, Qualified Events, Signals, Outcomes
```

**Configuration Manager (config/)** provides parameters to all modules.

---

## Document-to-Module Mapping

| Document | Primary Module(s) |
|----------|-------------------|
| CORE_SPECIFICATION.md | All (principles) |
| SCORING.md | `scoring/` |
| LW-001.md | `strategies/` |
| SYSTEM_ARCHITECTURE.md | All (architecture overview) |
| EVENT_ENGINE.md | `strategies/`, `scoring/`, `notifications/`, `outcome/`, `storage/`, `models/` |
| MARKET_EVENT_SCHEMA.md | `models/`, `storage/` |
| DATA_PROVIDER_ARCHITECTURE.md | `providers/` |
| CONFIGURATION_SYSTEM.md | `config/`, all (consumption) |
| STRATEGY_ENGINE.md | `strategies/` |

---

## Self Review

### ✅ Corresponds to Architecture

- Every module from SYSTEM_ARCHITECTURE.md (after EVENT_ENGINE.md improvements) has a folder:
  - Data Provider → `providers/`
  - Strategy Engine (was Pattern Detector) → `strategies/`
  - Scoring Engine → `scoring/`
  - Notification Service → `notifications/`
  - Outcome Tracker → `outcome/`
  - Storage Service → `storage/`
  - Configuration Manager → `config/`
- Additional supporting modules: `core/`, `models/`, `utils/`

### ⚠️ Missing / To Be Implemented Later

| Item | Reason |
|------|--------|
| `src/main.py` / entry point | Not in scope — only structure created |
| `configs/` folder with config files | Configuration files not created (only module exists) |
| `.env.example` | Created at root earlier, but not in `src/` |
| Tests (`tests/`) | Separate from `src/`, not created |
| Logging configuration | In `utils/` but not implemented |
| Data Provider implementation | Bybit-specific adapter not created (as required) |
| Telegram adapter | Not created (as required) |
| Database/Storage backend | Not created (as required) |
| Strategy LW-001 implementation | Not created (as required) |
| Scoring parameters implementation | Not created (as required) |

### ✅ Constraints Followed

- No classes created
- No functions created
- No business logic
- No Bybit connection code
- No Telegram integration
- No external dependencies added
- Only `__init__.py`, `README.md`, and `PROJECT_STRUCTURE.md` created