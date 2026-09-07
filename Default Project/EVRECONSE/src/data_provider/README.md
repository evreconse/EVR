# Data Provider Module

Market data provider abstraction with Bybit implementation.

## Files

| File | Purpose |
|------|---------|
| `provider.py` | MarketDataProvider abstract interface |
| `bybit_provider.py` | Bybit implementation |
| `websocket_client.py` | Generic WebSocket client |
| `rest_client.py` | REST API client |
| `internal_models.py` | Exchange-specific data models |
| `rate_limiter.py` | Rate limiting |
| `reconnect_strategy.py` | Reconnection with exponential backoff |
| `heartbeat.py` | Heartbeat monitoring |
| `exceptions.py` | Exception hierarchy |
| `__init__.py` | Public API exports |
| `README.md` | This file |

## Architecture

```
MarketDataProvider (interface)
    └── BybitDataProvider (implementation)
        ├── WebSocketClient (real-time data)
        ├── RestClient (snapshots/history)
        ├── ReconnectStrategy (exponential backoff)
        ├── HeartbeatMonitor (connection health)
        └── RateLimiter (request throttling)
```

## Usage

```python
from src.data_provider import BybitDataProvider

provider = BybitDataProvider(
    api_key="your_key",
    api_secret="your_secret",
    testnet=True,
)

await provider.connect()

# Subscribe to real-time data
await provider.subscribe_symbols(["BTCUSDT", "ETHUSDT"], "15m")

# Get historical snapshot
candles = provider.get_snapshot("BTCUSDT", "15m", limit=100)

# Stream real-time events
async for event in provider.stream():
    print(f"Signal: {event.symbol} {event.score}")

await provider.disconnect()
```

## Features

- **WebSocket**: Real-time candle, trade, liquidation streams
- **REST API**: Snapshots, orderbook, ticker, trades
- **Auto-reconnect**: Exponential backoff with jitter
- **Heartbeat**: Ping/pong monitoring with timeout
- **Rate limiting**: Sliding window (second/minute/hour)
- **Fail-fast**: Immediate errors with specific exceptions

## Extending

Add new exchanges by implementing `MarketDataProvider`:

```python
class BinanceDataProvider(MarketDataProvider):
    async def connect(self): ...
    async def disconnect(self): ...
    # ... implement all abstract methods
```