"""
Fake WebSocket Client for testing.

Provides a MagicMock-based fake WebSocketClient that does not make real connections.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FakeWebSocketClient:
    """Fake WebSocket client for unit tests."""

    def __init__(self, url: str = "wss://stream-testnet.bybit.com/v5/public/linear") -> None:
        self.url = url
        self._connected = False
        self._running = False
        self._on_message: Callable[[dict], None] | None = None
        self._on_connect: Callable[[], None] | None = None
        self._on_disconnect: Callable[[Exception | None], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None
        self._subscriptions: set[str] = set()
        self._sent_messages: list[dict[str, Any]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_message_handler(self, handler: Callable[[dict], None]) -> None:
        self._on_message = handler

    def set_connect_handler(self, handler: Callable[[], None]) -> None:
        self._on_connect = handler

    def set_disconnect_handler(self, handler: Callable[[Exception | None], None]) -> None:
        self._on_disconnect = handler

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        self._on_error = handler

    def connect(self) -> None:
        self._connected = True
        self._running = True
        if self._on_connect:
            self._on_connect()

    def disconnect(self) -> None:
        self._connected = False
        self._running = False
        if self._on_disconnect:
            self._on_disconnect(None)

    async def send_json(self, data: dict[str, Any]) -> None:
        self._sent_messages.append(data)

    async def ping(self) -> bool:
        return self._connected

    def subscribe(self, topic: str) -> None:
        self._subscriptions.add(topic)

    def unsubscribe(self, topic: str) -> None:
        self._subscriptions.discard(topic)

    def get_stats(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "url": self.url,
            "subscriptions": len(self._subscriptions),
        }

    def get_sent_messages(self) -> list[dict[str, Any]]:
        return list(self._sent_messages)

    def emit_message(self, data: dict[str, Any]) -> None:
        """Simulate receiving a message from the server."""
        if self._on_message:
            self._on_message(data)

    def emit_error(self, error: Exception) -> None:
        """Simulate an error."""
        if self._on_error:
            self._on_error(error)

    async def __aenter__(self) -> FakeWebSocketClient:
        self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()


def create_fake_websocket_client(url: str | None = None) -> FakeWebSocketClient:
    """Factory function to create a fake WebSocket client."""
    return FakeWebSocketClient(url=url or "wss://test.example.com/ws")