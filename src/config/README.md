# Config Module

Configuration Manager — single source of configuration for all modules.

Loads configuration via pluggable loaders, validates, provides typed access.

## Files

| File | Purpose |
|------|---------|
| `config_manager.py` | ConfigurationManager - main entry point |
| `validator.py` | ConfigValidator - validation logic (SRP) |
| `loader.py` | ConfigLoader - abstract loader interface for future YAML/.env/JSON |
| `types.py` | Dataclasses, enums, constants, parameter paths |
| `exceptions.py` | Configuration exceptions |

## Architecture

- **ConfigurationManager**: Single responsibility - loads, stores, provides access
- **ConfigValidator**: Single responsibility - validates configuration
- **ConfigLoader**: Interface for future loaders (YAML, .env, JSON)
- **Types**: All dataclasses, constants, parameter paths

## Corresponding Documents

- CONFIGURATION_SYSTEM.md
- SYSTEM_ARCHITECTURE.md (section 3.8)