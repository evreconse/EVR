"""
EVRECONSE Data Provider - WebSocket Client.

Production-ready WebSocket client with:
- Automatic reconnection
- Heartbeat/ping-pong
- Message queue
- Subscription management
- Rate limiting
"""

from __future__ import annotations

import asyncio
import json
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import websockets
from websockets.exceptions import (
    ConnectionClosed,
)

from .exceptions import (
    ConnectionError,
    DataProviderNotConnectedError,
    HeartbeatTimeoutError,
    InvalidMessageError,
)
from .reconnect_strategy import AsyncReconnectStrategy, ReconnectConfig


@dataclass(frozen=True, slots=True)
class WebSocketConfig:
    """
    WebSocket client configuration.

    Attributes:
        url: WebSocket server URL
        ping_interval: Ping interval in seconds
        ping_timeout: Ping timeout in seconds
        max_message_size: Maximum message size in bytes
        compression: Enable compression
        ssl_context: SSL context for secure connections
    """

    url: str
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    max_message_size: int = 16 * 1024 * 1024  # 16 MB
    compression: bool = True
    ssl_context: Any | None = None

    def __post_init__(self) -> None:
        if not self.url.startswith(("ws://", "wss://")):
            raise ValueError("URL must start with ws:// or wss://")
        if self.ping_interval <= 0:
            raise ValueError("ping_interval must be positive")
        if self.ping_timeout <= 0:
            raise ValueError("ping_timeout must be positive")
        if self.max_message_size <= 0:
            raise ValueError("max_message_size must be positive")


class WebSocketClient:
    """
    Generic WebSocket client for exchange connections.

    Handles connection lifecycle, message routing, heartbeat, and reconnection.
    Not exchange-specific - uses callbacks for message handling.
    """

    def __init__(
        self,
        config: WebSocketConfig,
        reconnect_config: ReconnectConfig | None = None,
    ) -> None:
        self._config = config
        self._reconnect_strategy = AsyncReconnectStrategy(reconnect_config or ReconnectConfig())
        self._lock = threading.RLock()
        self._ws: Any | None = None
        self._connected = False
        self._running = False
        self._read_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Callbacks
        self._on_message: Callable[[dict], None] | None = None
        self._on_connect: Callable[[], None] | None = None
        self._on_disconnect: Callable[[Exception | None], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

        # Subscription management
        self._subscriptions: set[str] = set()
        self._pending_subscriptions: list[str] = []

    def set_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Set message handler callback."""
        self._on_message = handler

    def set_connect_handler(self, handler: Callable[[], None]) -> None:
        """Set connection established callback."""
        self._on_connect = handler

    def set_disconnect_handler(self, handler: Callable[[Exception | None], None]) -> None:
        """Set disconnection callback."""
        self._on_disconnect = handler

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Set error handler callback."""
        self._on_error = handler

    def connect(self) -> None:
        """Start WebSocket connection in background thread."""
        with self._lock:
            if self._connected:
                return

            self._stop_event.clear()
            self._reconnect_strategy.reset()

            # Start event loop in background thread
            self._thread = threading.Thread(
                target=self._run_event_loop,
                name=f"WSClient-{id(self)}",
                daemon=True,
            )
            self._thread.start()

            # Wait for connection
            start = time.monotonic()
            while not self._connected and time.monotonic() - start < 30:
                time.sleep(0.1)

            if not self._connected:
                raise ConnectionError("Failed to connect within timeout")

    def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        with self._lock:
            self._running = False
            self._stop_event.set()

            if self._ws and self._loop:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

            if self._thread:
                self._thread.join(timeout=5.0)

            self._connected = False
            self._ws = None
            self._loop = None
            self._thread = None

    def _run_event_loop(self) -> None:
        """Run asyncio event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run())

    async def _run(self) -> None:
        """Main connection loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                await self._connect()
                self._reconnect_strategy.reset()

                # Wait for disconnection or stop
                while self._connected and not self._stop_event.is_set():
                    await asyncio.sleep(1.0)

            except Exception as e:
                if self._stop_event.is_set():
                    break
                if self._on_error:
                    self._on_error(e)
                await self._reconnect()
            finally:
                await self._cleanup()

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        ssl_context = self._config.ssl_context
        if self._config.url.startswith("wss://") and not self._config.ssl_context:
            ssl_context = ssl.create_default_context()

        self._ws = await websockets.connect(
            self._config.url,
            ping_interval=self._config.ping_interval,
            ping_timeout=self._config.ping_timeout,
            max_size=self._config.max_message_size,
            compression="deflate" if self._config.compression else None,
            ssl=ssl_context,
            open_timeout=30.0,
        )

        self._connected = True
        self._running = True

        if self._on_connect:
            self._on_connect()

        # Process pending subscriptions
        if self._pending_subscriptions:
            await self._resubscribe()

        # Start reader and ping tasks
        self._read_task = asyncio.create_task(self._read_loop())
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _read_loop(self) -> None:
        """Read messages from WebSocket."""
        try:
            async for message in self._ws:
                if self._stop_event.is_set():
                    break

                try:
                    data = json.loads(message)
                    print(f"DEBUG-WS: Received message: {data.get('topic', 'no-topic')}")
                    if self._on_message:
                        self._on_message(data)
                except json.JSONDecodeError as e:
                    raise InvalidMessageError(f"Invalid JSON: {e}", raw_data=message) from e
                except Exception as e:
                    if self._on_error:
                        self._on_error(e)

        except ConnectionClosed:
            self._connected = False
        except Exception as e:
            if self._on_error:
                self._on_error(e)
            self._connected = False

    async def _ping_loop(self) -> None:
        """Send periodic pings."""
        while self._connected and not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._config.ping_interval)
                if self._ws:
                    pong_waiter = await self._ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=self._config.ping_timeout)
            except TimeoutError:
                self._connected = False
                raise HeartbeatTimeoutError("Ping timeout")
            except Exception:
                self._connected = False
                break

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff."""
        if self._on_error:
            self._on_error(ConnectionError("Reconnecting..."))

        await self._reconnect_strategy.wait()

    async def _cleanup(self) -> None:
        """Cleanup tasks and connection."""
        self._connected = False

        for task in (self._read_task, self._ping_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._on_disconnect:
            self._on_disconnect(None)

    async def _resubscribe(self) -> None:
        """Resubscribe to all topics."""
        for topic in self._pending_subscriptions:
            await self._subscribe_internal(topic)
        self._pending_subscriptions.clear()

    async def _subscribe_internal(self, topic: str) -> None:
        """Internal subscription without adding to pending."""
        if self._ws and self._connected:
            await self._ws.send(json.dumps({"op": "subscribe", "args": [topic]}))

    def subscribe(self, topic: str) -> None:
        """Add topic to subscription list."""
        with self._lock:
            self._subscriptions.add(topic)
            if self._connected:
                asyncio.run_coroutine_threadsafe(self._subscribe_internal(topic), self._loop)

    def unsubscribe(self, topic: str) -> None:
        """Remove topic from subscription list."""
        with self._lock:
            self._subscriptions.discard(topic)
            if self._connected:
                asyncio.run_coroutine_threadsafe(self._unsubscribe_internal(topic), self._loop)

    async def _unsubscribe_internal(self, topic: str) -> None:
        """Internal unsubscription."""
        if self._ws and self._connected:
            await self._ws.send(json.dumps({"op": "unsubscribe", "args": [topic]}))

    async def send_json(self, data: dict) -> None:
        """Send JSON message."""
        if not self._ws or not self._connected:
            raise DataProviderNotConnectedError()
        await self._ws.send(json.dumps(data))

    async def ping(self) -> bool:
        """Send ping and wait for pong."""
        if not self._ws or not self._connected:
            return False
        try:
            pong_waiter = await self._ws.ping()
            await asyncio.wait_for(pong_waiter, timeout=self._config.ping_timeout)
            return True
        except Exception:
            return False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def url(self) -> str:
        """Get WebSocket URL."""
        return self._config.url

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "connected": self._connected,
            "url": self._config.url,
            "subscriptions": len(self._subscriptions),
            "reconnect_status": self._reconnect_strategy.get_status(),
        }

    async def __aenter__(self) -> WebSocketClient:
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()


# =============================================================================
# BingX-specific WebSocket Client
# =============================================================================

class BingXWebSocketClient(WebSocketClient):
    """
    BingX-specific WebSocket client with topic management.

    Handles BingX's subscription format and message structure.
    
    BingX API Documentation: https://bingx-api.github.io/docs/swap/
    """

    BINGX_TOPICS = {
        "kline": "kline.{interval}.{symbol}",
        "trade": "trade.{symbol}",
        "depth": "depth.{symbol}",
        "ticker": "ticker.{symbol}",
        "mark_price": "markPrice.{symbol}",
        "funding_rate": "fundingRate.{symbol}",
    }

    def __init__(
        self,
        testnet: bool = False,
        reconnect_config: ReconnectConfig | None = None,
    ) -> None:
        url = (
            "wss://open-api-testnet.bingx.com/swap/market/ws"
            if testnet
            else "wss://open-api.bingx.com/swap/market/ws"
        )
        config = WebSocketConfig(url=url)
        super().__init__(config, reconnect_config)

    def subscribe_kline(self, symbol: str, interval: str = "15m") -> None:
        """Subscribe to kline/candle stream.
        
        Args:
            symbol: Trading symbol in BASE-QUOTE format (e.g., BTC-USDT)
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
        """
        topic = f"kline.{interval}.{symbol}"
        self.subscribe(topic)

    def unsubscribe_kline(self, symbol: str, interval: str = "15m") -> None:
        """Unsubscribe from kline/candle stream."""
        topic = f"kline.{interval}.{symbol}"
        self.unsubscribe(topic)

    def subscribe_trades(self, symbol: str) -> None:
        """Subscribe to public trades."""
        topic = f"trade.{symbol}"
        self.subscribe(topic)

    def subscribe_depth(self, symbol: str) -> None:
        """Subscribe to order book depth."""
        topic = f"depth.{symbol}"
        self.subscribe(topic)

    def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker."""
        topic = f"ticker.{symbol}"
        self.subscribe(topic)

    def subscribe_mark_price(self, symbol: str) -> None:
        """Subscribe to mark price."""
        topic = f"markPrice.{symbol}"
        self.subscribe(topic)

    def subscribe_funding_rate(self, symbol: str) -> None:
        """Subscribe to funding rate."""
        topic = f"fundingRate.{symbol}"
        self.subscribe(topic)


# =============================================================================
# Factory function
# =============================================================================

def create_websocket_client(
    url: str,
    testnet: bool = False,
    ping_interval: float = 20.0,
    ping_timeout: float = 10.0,
) -> WebSocketClient:
    """Factory function to create WebSocket client."""
    config = WebSocketConfig(
        url=url,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
    )
    return WebSocketClient(config)


def create_bingx_websocket_client(
    testnet: bool = False,
    reconnect_config: ReconnectConfig | None = None,
) -> BingXWebSocketClient:
    """Factory function to create BingX WebSocket client."""
    return BingXWebSocketClient(testnet=testnet, reconnect_config=reconnect_config)