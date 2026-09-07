# Storage Module

File-based event storage with atomic writes, indexing, and thread safety.

## Files

| File | Purpose |
|------|---------|
| `repository.py` | StorageRepository interface + FileStorageRepository implementation |
| `serializers.py` | Centralized serialization using MarketEvent.to_dict()/from_dict() |
| `exceptions.py` | Storage-specific exception hierarchy |
| `__init__.py` | Public API exports |
| `README.md` | This file |

## Architecture

```
StorageEngine (future) → StorageRepository (interface) → FileStorageRepository (implementation)
```

- **StorageRepository**: Abstract interface defining all storage operations
- **FileStorageRepository**: File-based implementation with atomic writes, indexing, thread safety
- **Serializers**: Centralized serialization using MarketEvent.to_dict()/from_dict()

## Usage

```python
from src.storage import FileStorageRepository, EventID
from src.models import MarketEvent

# Initialize repository
repo = FileStorageRepository("./data/events")

# Save event
event = MarketEvent.new(...)
repo.save_event(event)

# Load event
event = repo.load_event(event_id)

# Query events
events = repo.find_by_status(EventStatus.SIGNAL)
events = repo.find_by_symbol("BTCUSDT")
events = repo.find_by_strategy("LW-001")
active = repo.find_active()

# Update event
repo.update_event(event)

# Delete event
repo.delete_event(event_id)

# Close when done
repo.close()
```

## Features

- **Atomic Writes**: Temp file + atomic rename (no partial writes)
- **Thread Safety**: All operations protected by RLock
- **Incremental Index**: Built once at startup, updated incrementally
- **Path Safety**: Only EventID used as filename; path traversal prevented
- **Fail Fast**: Invalid data raises immediately with specific exceptions
- **Atomic Writes**: Temp file + os.replace() ensures no partial writes
- **Fail Fast**: Invalid data raises immediately with specific exceptions

## Exceptions

- `StorageError` - Base exception
- `StorageReadError` - Read failures
- `StorageWriteError` - Write failures
- `StorageSerializationError` - Serialization/deserialization failures
- `StorageCorruptedError` - Data corruption detected
- `RepositoryError` - Base for repository operations
- `EventNotFoundError` - Event not found
- `EventAlreadyExistsError` - Duplicate event ID
- `IndexCorruptedError` - Index corruption detected

## Thread Safety

All public methods are thread-safe using `threading.RLock`.
Multiple threads can safely read/write concurrently.