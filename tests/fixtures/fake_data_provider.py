"""
Fake MarketDataProvider for testing.

Provides a MagicMock-based fake that implements the MarketDataProvider interface
without making real network calls.
"""

from __future__ import annotations

from typing import Any


class FakeDataProvider:
    """Fake MarketDataProvider for unit tests."""

    def __init__(self) -> None:
        self.exchange_name = "bybit"
        self.supported_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.supported_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self._connected = False
        self._subscribed_symbols: list[str] = []
        self._subscribed_timeframe = "15m"
        self._on_market_event: Any = None
        self._on_connect: Any = None
        self._on_disconnect: Any = None
        self._on_error: Any = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True
        if self._on_connect:
            self._on_connect()

    async def disconnect(self) -> None:
        self._connected = False
        if self._on_disconnect:
            self._on_disconnect(None)

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def subscribe_symbols(self, symbols: list[str], timeframe: str) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")
        self._subscribed_symbols = list(symbols)
        self._subscribed_timeframe = timeframe

    async def unsubscribe_symbols(self, symbols: list[str]) -> None:
        for symbol in symbols:
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)

    async def subscribe_timeframe(self, timeframe: str) -> None:
        self._subscribed_timeframe = timeframe

    def get_snapshot(self, symbol: str, timeframe: str, limit: int = 1) -> list[dict]:
        return [
            {
                "open": 50000.0,
                "high": 50100.0,
                "low": 49900.0,
                "close": 50050.0,
                "volume": 100.5,
                "timestamp": 1700000000000,
            }
        ]

    async def stream(self) -> Any:
        raise NotImplementedError("Use set_market_event_handler for event delivery")

    async def ping(self) -> bool:
        return self._connected

    def set_market_event_handler(self, handler: Any) -> None:
        self._on_market_event = handler

    def set_connect_handler(self, handler: Any) -> None:
        self._on_connect = handler

    def set_disconnect_handler(self, handler: Any) -> None:
        self._on_disconnect = handler

    def set_error_handler(self, handler: Any) -> None:
        self._on_error = handler

    def emit_market_event(self, event: Any) -> None:
        """Simulate receiving a market event."""
        if self._on_market_event:
            self._on_market_event(event)


def create_fake_data_provider() -> FakeDataProvider:
    """Factory function to create a fake data provider."""
    return FakeDataProvider()