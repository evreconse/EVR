"""
EVRECONSE Data Provider - Bybit Provider.

Bybit implementation of the MarketDataProvider interface.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from models import MarketEvent
from models.enums import Exchange, Timeframe as TimeframeEnum
from .exceptions import (
    ConnectionError,
    DataProviderNotConnectedError,
    ReconnectError,
)
from .internal_models import Candle
from .reconnect_strategy import ReconnectConfig, ReconnectStrategy
from .rest_client import RestClient, RestConfig
from .websocket_client import WebSocketClient, WebSocketConfig


@dataclass(frozen=True, slots=True)
class BybitDataProviderConfig:
    """Bybit data provider configuration."""

    api_key: str | None = None
    api_secret: str | None = None
    testnet: bool = False
    recv_window: int = 5000
    rate_limit_requests: int = 10
    rate_limit_window_seconds: float = 1.0
    websocket_ping_interval: float = 20.0
    websocket_ping_timeout: float = 10.0
    max_reconnect_attempts: int = 0
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    connection_timeout: float = 30.0
    connection_heartbeat_interval: float = 30.0


class BybitDataProvider:
    """
    Bybit market data provider implementation.

    Provides real-time market data from Bybit exchange via WebSocket and REST API.
    """

    _TIMEFRAME_MAP = {
        "1m": "M1",
        "5m": "M5",
        "15m": "M15",
        "30m": "M30",
        "1h": "H1",
        "4h": "H4",
        "1d": "D1",
        "M1": "M1",
        "M5": "M5",
        "M15": "M15",
        "M30": "M30",
        "H1": "H1",
        "H4": "H4",
        "D1": "D1",
    }

    _WS_TIMEFRAME_MAP = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",
        "1d": "D",
        "M1": "1",
        "M5": "5",
        "M15": "15",
        "M30": "30",
        "H1": "60",
        "H4": "240",
        "D1": "D",
    }

    def __init__(
        self,
        config: BybitDataProviderConfig,
    ) -> None:
        """
        Initialize Bybit data provider.

        Args:
            config: Bybit data provider configuration
        """
        self._config = config
        self._testnet = config.testnet
        self._api_key = config.api_key
        self._api_secret = config.api_secret

        # Configuration
        self._ws_url = (
            "wss://stream-testnet.bybit.com/v5/public/linear" if self._testnet else "wss://stream.bybit.com/v5/public/linear"
        )
        self._rest_url = (
            "https://api-testnet.bybit.com" if self._testnet else "https://api.bybit.com"
        )

        # Components
        self._ws_client: WebSocketClient | None = None
        self._rest_client: RestClient | None = None
        self._reconnect_strategy = ReconnectStrategy(ReconnectConfig(
            max_attempts=config.max_reconnect_attempts,
            initial_delay=config.reconnect_base_delay,
            max_delay=config.reconnect_max_delay,
        ))

        # State
        self._lock = threading.RLock()
        self._connected = False
        self._subscribed_symbols: set[tuple[str, str]] = set()
        self._subscribed_symbols_list: list[str] = []
        self._timeframe: str = "15m"
        self._on_market_event: Callable[[MarketEvent], None] | None = None
        self._on_connect: Callable[[], None] | None = None
        self._on_disconnect: Callable[[Exception | None], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

    def _normalize_timeframe(self, timeframe: str) -> str:
        """Convert exchange timeframe to internal Timeframe enum value."""
        return self._TIMEFRAME_MAP.get(timeframe.lower(), timeframe)

    @property
    def supported_timeframes(self) -> list[str]:
        return ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "M1", "M5", "M15", "M30", "H1", "H4", "D1"]

    # =========================================================================
    # Public API
    # =========================================================================

    def set_market_event_handler(self, handler: Callable[[MarketEvent], None]) -> None:
        """Set callback for market events."""
        self._on_market_event = handler

    def set_connect_handler(self, handler: Callable[[], None]) -> None:
        """Set callback for successful connection."""
        self._on_connect = handler

    def set_disconnect_handler(self, handler: Callable[[Exception | None], None]) -> None:
        """Set callback for disconnection."""
        self._on_disconnect = handler

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Set callback for errors."""
        self._on_error = handler

    async def connect(self) -> None:
        """Establish connection to Bybit."""
        with self._lock:
            if self._connected:
                return

            # Initialize REST client
            self._rest_client = RestClient(RestConfig(
                base_url=self._rest_url,
                api_key=self._api_key,
                api_secret=self._api_secret,
            ))

            # Initialize WebSocket client
            ws_config = WebSocketConfig(
                url=self._ws_url,
                ping_interval=self._config.websocket_ping_interval,
                ping_timeout=self._config.websocket_ping_timeout,
            )
            ws_reconnect_config = ReconnectConfig(
                max_attempts=self._config.max_reconnect_attempts,
                initial_delay=self._config.reconnect_base_delay,
                max_delay=self._config.reconnect_max_delay,
            )
            self._ws_client = WebSocketClient(ws_config, ws_reconnect_config)
            self._ws_client.set_message_handler(self._handle_ws_message)
            self._ws_client.set_connect_handler(self._on_ws_connect)
            self._ws_client.set_disconnect_handler(self._on_ws_disconnect)
            self._ws_client.set_error_handler(self._on_ws_error)

            try:
                self._ws_client.connect()
            except Exception as e:
                await self.disconnect()
                raise ConnectionError(f"Failed to connect to Bybit: {e}") from e

            self._connected = True

            if self._on_connect:
                self._on_connect()

    async def disconnect(self) -> None:
        """Disconnect from Bybit."""
        with self._lock:
            if not self._connected:
                return

            self._connected = False

            if self._ws_client:
                self._ws_client.disconnect()
                self._ws_client = None

            if self._rest_client:
                await self._rest_client.close()
                self._rest_client = None

            self._subscribed_symbols.clear()
            self._subscribed_symbols_list.clear()

        if self._on_disconnect:
            self._on_disconnect(None)

    async def subscribe_symbols(self, symbols: list[str], timeframe: str) -> None:
        """
        Subscribe to market data for symbols.

        Args:
            symbols: List of trading symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframe: Timeframe for candles (e.g., "15m")

        Raises:
            SubscriptionError: If subscription fails.
        """
        if not self._connected:
            raise DataProviderNotConnectedError()

        with self._lock:
            self._timeframe = timeframe
            self._subscribed_symbols_list = symbols[:]

            for symbol in symbols:
                self._subscribed_symbols.add((symbol, timeframe))

        # Send subscription message via WebSocket (on background thread)
        args = [f"kline.{self._WS_TIMEFRAME_MAP.get(timeframe, timeframe)}.{symbol}" for symbol in symbols]
        if self._ws_client and self._ws_client._loop:
            await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(
                    self._ws_client.send_json({
                        "op": "subscribe",
                        "args": args,
                    }),
                    self._ws_client._loop,
                )
            )

    async def unsubscribe_symbols(self, symbols: list[str]) -> None:
        """Unsubscribe from market data for symbols."""
        if not self._connected:
            return

        with self._lock:
            for symbol in symbols:
                self._subscribed_symbols.discard((symbol, self._timeframe))
                if symbol in self._subscribed_symbols_list:
                    self._subscribed_symbols_list.remove(symbol)

            args = [f"kline.{self._WS_TIMEFRAME_MAP.get(self._timeframe, self._timeframe)}.{symbol}" for symbol in symbols]
            if self._ws_client and self._ws_client._loop:
                await asyncio.wrap_future(
                    asyncio.run_coroutine_threadsafe(
                        self._ws_client.send_json({
                            "op": "unsubscribe",
                            "args": args,
                        }),
                        self._ws_client._loop,
                    )
                )

    async def subscribe_timeframe(self, timeframe: str) -> None:
        """Subscribe to a new timeframe."""
        if timeframe not in self.supported_timeframes:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        with self._lock:
            old_timeframe = self._timeframe
            self._timeframe = timeframe

            # Resubscribe all symbols with new timeframe
            symbols = self._subscribed_symbols_list[:]

        if symbols:
            await self.unsubscribe_symbols(symbols)
            await self.subscribe_symbols(symbols, timeframe)

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1,
    ) -> list[dict]:
        """Get historical klines via REST API."""
        if not self._rest_client:
            raise DataProviderNotConnectedError()

        # Convert timeframe to Bybit interval format
        ws_tf = self._WS_TIMEFRAME_MAP.get(timeframe, timeframe)
        interval = ws_tf
        response = await self._rest_client.get_klines(
            symbol=symbol, interval=interval, limit=limit
        )
        return response.get("result", {}).get("list", [])

    # Backward-compatible alias
    def get_snapshot(self, symbol: str, timeframe: str, limit: int = 1) -> list[dict]:
        """Get historical snapshot via REST API (synchronous wrapper)."""
        return asyncio.run(self.get_klines(symbol, timeframe, limit))

    async def stream(self) -> AsyncGenerator[MarketEvent, None]:
        """Stream market events in real-time."""
        if not self._connected:
            raise DataProviderNotConnectedError()

        # Events are delivered via _on_market_event callback
        # This stream method exists for API compatibility
        raise NotImplementedError("Use set_market_event_handler for event delivery")

    async def ping(self) -> bool:
        """Ping the exchange."""
        if not self._ws_client or not self._ws_client.is_connected:
            return False

        try:
            if self._ws_client._loop:
                await asyncio.wrap_future(
                    asyncio.run_coroutine_threadsafe(self._ws_client.ping(), self._ws_client._loop)
                )
            return True
        except Exception:
            return False

    def is_connected(self) -> bool:
        """Check if connected to exchange."""
        return self._connected and self._ws_client is not None and self._ws_client.is_connected

    # =========================================================================
    # Internal Callbacks
    # =========================================================================

    def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket message."""
        try:
            # Parse message
            topic = data.get("topic", "")
            data_list = data.get("data", [])

            if "kline" in topic:
                self._handle_kline_data(data)
            elif "trade" in topic:
                self._handle_trade_data(data)
            elif "liquidation" in topic:
                self._handle_liquidation_data(data)
        except Exception as e:
            if self._on_error:
                self._on_error(e)

    def _handle_kline_data(self, data: dict) -> None:
        """Handle kline/candle data."""
        _Timeframe = TimeframeEnum
        logger = logging.getLogger(__name__)
        try:
            topic = data.get("topic", "")
            parts = topic.split(".")
            if len(parts) >= 3:
                ws_timeframe = parts[1]
                symbol = parts[2]

                for kline_data in data.get("data", []):
                    if not kline_data.get("confirm", False):
                        continue  # Only process closed candles

                    required_fields = ["start", "end", "open", "high", "low", "close", "volume", "turnover"]
                    for field in required_fields:
                        if field not in kline_data:
                            raise ValueError(f"Missing required field: {field}")

                    candle = Candle(
                        symbol=symbol,
                        exchange="bybit",
                        timeframe=self._timeframe,
                        open_time=datetime.fromtimestamp(kline_data["start"] / 1000, tz=UTC),
                        close_time=datetime.fromtimestamp(kline_data["end"] / 1000, tz=UTC),
                        open_price=float(kline_data["open"]),
                        high_price=float(kline_data["high"]),
                        low_price=float(kline_data["low"]),
                        close_price=float(kline_data["close"]),
                        volume=float(kline_data["volume"]),
                        quote_volume=float(kline_data["turnover"]),
                        trades_count=0,
                        taker_buy_volume=0.0,
                        taker_buy_quote_volume=0.0,
                        is_closed=True,
                    )

                    # Create market event - use local _Timeframe reference
                    try:
                        normalized_tf = self._normalize_timeframe(candle.timeframe)
                        print(f"DEBUG: normalized_tf={normalized_tf!r}, type={type(normalized_tf)}")
                        print(f"DEBUG: _Timeframe={_Timeframe}, type={type(_Timeframe)}, callable={callable(_Timeframe)}")
                        tf_enum = _Timeframe(normalized_tf)
                        print(f"DEBUG: tf_enum={tf_enum}, type={type(tf_enum)}")
                    except Exception as tf_err:
                        logger.error(f"Timeframe conversion failed: {tf_err}", exc_info=True)
                        raise

                    # Create market event
                    print(f"DEBUG: About to call MarketEvent.new")
                    event = MarketEvent.new(
                        symbol=candle.symbol,
                        exchange=Exchange(candle.exchange),
                        timeframe=tf_enum,
                        event_time=candle.close_time,
                        open_price=candle.open_price,
                        high_price=candle.high_price,
                        low_price=candle.low_price,
                        close_price=candle.close_price,
                        volume=candle.volume,
                    )
                    print(f"DEBUG: MarketEvent.new returned: {event}")

                    if self._on_market_event:
                        self._on_market_event(event)
        except Exception as e:
            logger.error(f"Error handling kline data: {e}", exc_info=True)
            if self._on_error:
                self._on_error(e)

    def _handle_trade_data(self, data: dict) -> None:
        """Handle trade data."""
        pass

    def _handle_liquidation_data(self, data: dict) -> None:
        """Handle liquidation data."""
        pass

    def _on_ws_connect(self) -> None:
        if self._on_connect:
            self._on_connect()

    def _on_ws_disconnect(self, error: Exception | None) -> None:
        self._connected = False
        if self._on_disconnect:
            self._on_disconnect(error)

    def _on_ws_error(self, error: Exception) -> None:
        if self._on_error:
            self._on_error(error)

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self) -> BybitDataProvider:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()