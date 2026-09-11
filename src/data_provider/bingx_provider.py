"""
EVRECONSE Data Provider - BingX Implementation.

Production-ready BingX data provider implementing MarketDataProvider interface.
Uses BingX REST API for historical data and WebSocket for real-time streaming.
Includes heartbeat monitoring, health checks, and auto-reconnection.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from src.core import get_logger

from .exceptions import (
    ConnectionError,
    DataProviderError,
    DataProviderNotConnectedError,
    DataProviderNotInitializedError,
    RateLimitError,
    SnapshotError,
    SubscriptionError,
)
from .internal_models import Candle, MarketDataMessage, MarketDataType
from .provider import MarketDataProvider
from .rate_limiter import RateLimitConfig, RateLimiter
from .reconnect_strategy import ReconnectConfig, ReconnectStrategy

# Import BingX fetcher
from src.exchange import BingXFetcher

logger = get_logger(__name__)


class BingXDataProvider(MarketDataProvider):
    """
    BingX Market Data Provider.
    
    Implements MarketDataProvider interface for BingX exchange.
    Uses BingX REST API for historical data and WebSocket for real-time streaming.
    Includes heartbeat monitoring, health checks, and auto-reconnection.
    """
    
    # Rate limits for BingX API
    PUBLIC_RATE_LIMIT = 20      # requests per second for public endpoints
    MARKET_DATA_RATE_LIMIT = 50 # requests per second for market data
    
    # Health monitoring
    HEARTBEAT_INTERVAL = 60.0   # seconds between heartbeats
    WS_HEALTH_CHECK_INTERVAL = 30.0  # seconds between WS health checks
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        recv_window: int = 5000,
        rate_limit_requests: int = 10,
        rate_limit_window_seconds: float = 1.0,
        websocket_ping_interval: float = 20.0,
        websocket_ping_timeout: float = 10.0,
        max_reconnect_attempts: int = 0,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._recv_window = recv_window
        
        # Internal state
        self._connected = False
        self._initialized = False
        self._subscribed_symbols: set[str] = set()
        self._subscribed_timeframe: str = "15m"
        
        # BingX fetcher for REST API
        self._fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
        
        # Rate limiters
        self._public_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=self.PUBLIC_RATE_LIMIT,
            burst_size=self.PUBLIC_RATE_LIMIT,
        ))
        self._market_data_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=self.MARKET_DATA_RATE_LIMIT,
            burst_size=self.MARKET_DATA_RATE_LIMIT,
        ))
        
        # Reconnect strategy
        self._reconnect_strategy = ReconnectStrategy(ReconnectConfig(
            max_attempts=max_reconnect_attempts if max_reconnect_attempts > 0 else None,
            initial_delay=reconnect_base_delay,
            max_delay=reconnect_max_delay,
            jitter=0.1,
        ))
        
        # Callbacks for real-time streaming
        self._candle_callback: Any = None
        
        # Health monitoring
        self._heartbeat_task: asyncio.Task | None = None
        self._ws_health_task: asyncio.Task | None = None
        self._ws_client: Any = None
        self._last_ws_message: datetime | None = None
        self._health_check_callback: Any = None
        
    @property
    def exchange_name(self) -> str:
        return "bingx"
    
    @property
    def supported_timeframes(self) -> list[str]:
        return ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    @property
    def supported_symbols(self) -> list[str]:
        # This would be populated from contracts API
        return []
    
    def set_market_event_handler(self, handler) -> None:
        """Set callback for market events from WebSocket stream."""
        self._candle_callback = handler
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def initialize(self) -> None:
        """Initialize the data provider."""
        if self._initialized:
            return
        
        # Test connection by fetching contracts
        try:
            await self._fetcher.get_usdt_perpetual_symbols()
            self._initialized = True
            logger.info("BingXDataProvider initialized successfully")
        except Exception as e:
            logger.error(f"BingXDataProvider initialization failed: {e}")
            raise ConnectionError(f"Failed to initialize BingX provider: {e}") from e
    
    async def connect(self) -> None:
        """Establish connection to BingX."""
        if self._connected:
            return
        
        if not self._initialized:
            await self.initialize()
        
        # BingX REST API doesn't require persistent connection
        # WebSocket connection will be established on subscribe
        self._connected = True
        logger.info("BingXDataProvider connected")
    
    async def disconnect(self) -> None:
        """Disconnect from BingX."""
        self._connected = False
        self._subscribed_symbols.clear()
        logger.info("BingXDataProvider disconnected")
    
    async def reconnect(self) -> None:
        """Reconnect to BingX."""
        await self.disconnect()
        await self.connect()
    
    async def subscribe_symbols(self, symbols: list[str], timeframe: str) -> None:
        """
        Subscribe to market data for symbols.
        
        Args:
            symbols: List of trading symbols (e.g., ["BTC-USDT", "ETH-USDT"])
            timeframe: Candle timeframe (e.g., "15m")
        
        Raises:
            SubscriptionError: If subscription fails
        """
        if not self._connected:
            raise DataProviderNotConnectedError("Not connected to BingX")
        
        # Validate timeframe
        if timeframe not in self.supported_timeframes:
            raise SubscriptionError(f"Unsupported timeframe: {timeframe}")
        
        self._subscribed_symbols.update(symbols)
        self._subscribed_timeframe = timeframe
        logger.info(f"Subscribed to {len(symbols)} symbols on {timeframe}")
    
    async def unsubscribe_symbols(self, symbols: list[str]) -> None:
        """Unsubscribe from market data for symbols."""
        self._subscribed_symbols.difference_update(symbols)
        logger.info(f"Unsubscribed from {len(symbols)} symbols")
    
    async def subscribe_timeframe(self, timeframe: str) -> None:
        """Subscribe to a new timeframe."""
        if timeframe not in self.supported_timeframes:
            raise SubscriptionError(f"Unsupported timeframe: {timeframe}")
        self._subscribed_timeframe = timeframe
        logger.info(f"Subscribed to timeframe: {timeframe}")
    
    def get_snapshot(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1,
    ) -> list[dict]:
        """
        Get historical snapshot of candles.
        
        This is a synchronous method for compatibility. Use async version for production.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for candles
            limit: Number of candles to retrieve
        
        Returns:
            List of candle data dictionaries
        """
        # Run async internally
        try:
            loop = asyncio.get_running_loop()
            # Can't run async in running loop, return empty for sync compatibility
            logger.warning("get_snapshot called in async context, use async_get_snapshot instead")
            return []
        except RuntimeError:
            # No running loop, safe to run
            return asyncio.run(self.async_get_snapshot(symbol, timeframe, limit))
    
    async def async_get_snapshot(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1,
    ) -> list[dict]:
        """
        Get historical snapshot of candles (async).
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USDT")
            timeframe: Timeframe for candles (e.g., "15m")
            limit: Number of candles to retrieve
        
        Returns:
            List of candle data dictionaries with keys: time, open, high, low, close, volume
        """
        await self._market_data_limiter.acquire()
        
        try:
            klines = await self._fetcher.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=limit,
            )
            
            # Convert to standard format
            candles = []
            for k in klines:
                candles.append({
                    "time": k["time"],
                    "open": float(k["open"]),
                    "high": float(k["high"]),
                    "low": float(k["low"]),
                    "close": float(k["close"]),
                    "volume": float(k["volume"]),
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Failed to get snapshot for {symbol}: {e}")
            raise SnapshotError(f"Snapshot failed for {symbol}: {e}") from e
    
    async def get_snapshot_with_volumes(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get historical candles including enough previous candles for volume ratio calculation.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for candles
            limit: Number of recent candles to retrieve (plus 20 for volume reference)
        
        Returns:
            List of candle data dictionaries
        """
        # Fetch limit + 20 to have previous 20 for volume ratio
        total_limit = limit + 20
        return await self.async_get_snapshot(symbol, timeframe, total_limit)
    
    async def stream(self) -> AsyncGenerator[MarketDataMessage, None]:
        """
        Stream market events in real-time.
        
        Yields:
            MarketEvent objects as they are generated
        """
        if not self._connected:
            raise DataProviderNotConnectedError("Not connected to BingX")
        
        # For BingX, we implement WebSocket streaming
        # This is a simplified implementation - production would use BingX WebSocket API
        logger.info("Starting BingX market data stream")
        
        # Subscribe to WebSocket
        from .websocket_client import BingXWebSocketClient
        
        ws_client = BingXWebSocketClient(
            symbols=list(self._subscribed_symbols),
            timeframe=self._subscribed_timeframe,
        )
        
        await ws_client.connect()
        
        try:
            async for message in ws_client.stream():
                if message.type == MarketDataType.KLINE:
                    # Convert to MarketDataMessage
                    yield self._convert_kline_to_message(message)
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise
        finally:
            await ws_client.disconnect()
    
    def _convert_kline_to_message(self, kline_data: dict) -> MarketDataMessage:
        """Convert BingX kline to MarketDataMessage."""
        return MarketDataMessage(
            type=MarketDataType.KLINE,
            symbol=kline_data["symbol"],
            timeframe=kline_data["timeframe"],
            timestamp=datetime.fromtimestamp(kline_data["time"] / 1000, tz=UTC),
            data=Candle(
                open=kline_data["open"],
                high=kline_data["high"],
                low=kline_data["low"],
                close=kline_data["close"],
                volume=kline_data["volume"],
                timestamp=datetime.fromtimestamp(kline_data["time"] / 1000, tz=UTC),
            ),
        )
    
    async def ping(self) -> bool:
        """Ping the exchange to check connectivity."""
        try:
            symbols = await self._fetcher.get_usdt_perpetual_symbols()
            return len(symbols) > 0
        except Exception:
            return False
    
    async def get_symbols(self) -> list[str]:
        """Get all available USDT perpetual symbols."""
        return await self._fetcher.get_usdt_perpetual_symbols()
    
    async def get_klines_with_volumes(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 50,
    ) -> list[dict]:
        """
        Get klines with enough history for volume ratio calculation.
        
        Returns:
            List of dicts with time, open, high, low, close, volume
        """
        # Need limit + 20 for volume reference
        return await self.async_get_snapshot(symbol, timeframe, limit + 20)

    # =========================================================================
    # Health Monitoring & Heartbeat
    # =========================================================================
    
    def set_health_check_callback(self, callback) -> None:
        """Set callback for health check notifications."""
        self._health_check_callback = callback
    
    async def start_heartbeat(self) -> None:
        """Start heartbeat monitoring task."""
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            return
        
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("BingXDataProvider heartbeat monitoring started")
    
    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring task."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("BingXDataProvider heartbeat monitoring stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to check connectivity and log status."""
        while self._connected:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if not self._connected:
                    break
                
                # Ping REST API to check connectivity
                healthy = await self.ping()
                if not healthy:
                    logger.warning("BingXDataProvider heartbeat failed - REST API unreachable")
                    if self._health_check_callback:
                        await self._health_check_callback(False, "REST API unreachable")
                else:
                    # Log heartbeat every 60s
                    logger.info("BingXDataProvider heartbeat OK - REST API reachable")
                    if self._health_check_callback:
                        await self._health_check_callback(True, "OK")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    async def start_ws_health_monitor(self) -> None:
        """Start WebSocket health monitoring task."""
        if self._ws_health_task is not None and not self._ws_health_task.done():
            return
        
        self._ws_health_task = asyncio.create_task(self._ws_health_loop())
        logger.info("BingXDataProvider WebSocket health monitoring started")
    
    async def stop_ws_health_monitor(self) -> None:
        """Stop WebSocket health monitoring task."""
        if self._ws_health_task is not None:
            self._ws_health_task.cancel()
            try:
                await self._ws_health_task
            except asyncio.CancelledError:
                pass
            self._ws_health_task = None
            logger.info("BingXDataProvider WebSocket health monitoring stopped")
    
    async def _ws_health_loop(self) -> None:
        """Monitor WebSocket connection health."""
        while self._connected:
            try:
                await asyncio.sleep(self.WS_HEALTH_CHECK_INTERVAL)
                if not self._connected:
                    break
                
                # Check if we've received a message recently
                if self._last_ws_message is not None:
                    time_since_last = (datetime.now(UTC) - self._last_ws_message).total_seconds()
                    if time_since_last > self.WS_HEALTH_CHECK_INTERVAL * 3:
                        logger.warning(f"No WebSocket message for {time_since_last:.0f}s, connection may be stale")
                        if self._health_check_callback:
                            await self._health_check_callback(False, f"No WS message for {time_since_last:.0f}s")
                        # Trigger reconnection
                        await self._handle_ws_failure()
                    else:
                        logger.debug(f"WebSocket health OK - last message {time_since_last:.0f}s ago")
                else:
                    # No message ever received
                    logger.warning("No WebSocket message received yet")
                    if self._health_check_callback:
                        await self._health_check_callback(False, "No WS message received yet")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WS health check error: {e}")
    
    async def _handle_ws_failure(self) -> None:
        """Handle WebSocket failure - attempt reconnection."""
        logger.warning("WebSocket failure detected, attempting reconnection...")
        if self._health_check_callback:
            await self._health_check_callback(False, "WebSocket failure, reconnecting")
        
        try:
            # Stop current WS tasks
            if self._ws_health_task:
                self._ws_health_task.cancel()
                try:
                    await self._ws_health_task
                except asyncio.CancelledError:
                    pass
            
            # Reconnect WebSocket
            await self.reconnect_ws()
            
        except Exception as e:
            logger.error(f"WS reconnection failed: {e}")
    
    async def reconnect_ws(self) -> None:
        """Reconnect WebSocket with exponential backoff."""
        logger.info("Reconnecting WebSocket...")
        
        # Stop existing WS client
        if self._ws_client:
            try:
                await self._ws_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting old WS client: {e}")
            self._ws_client = None
        
        # Use reconnect strategy
        await self._reconnect_strategy.wait()
        
        # Create new WS client and reconnect
        from .websocket_client import BingXWebSocketClient
        
        self._ws_client = BingXWebSocketClient(
            symbols=list(self._subscribed_symbols),
            timeframe=self._subscribed_timeframe,
        )
        
        # Set up message handler
        self._ws_client.set_message_handler(self._on_ws_message)
        
        await self._ws_client.connect()
        self._last_ws_message = datetime.now(UTC)
        
        # Restart health monitor
        await self.start_ws_health_monitor()
        
        logger.info("WebSocket reconnected successfully")
    
    def _on_ws_message(self, message: dict) -> None:
        """Handle incoming WebSocket message."""
        self._last_ws_message = datetime.now(UTC)
        
        if message.get("type") == "kline" or message.get("topic", "").startswith("kline"):
            if self._candle_callback:
                try:
                    message_obj = self._convert_kline_to_message(message)
                    asyncio.create_task(self._candle_callback(message_obj))
                except Exception as e:
                    logger.error(f"Error processing kline message: {e}")
    
    async def health_check(self) -> bool:
        """Comprehensive health check."""
        try:
            # Check REST API
            rest_ok = await self.ping()
            
            # Check WebSocket
            ws_ok = self._connected and self._ws_client is not None
            
            # Check recent message
            msg_recent = False
            if self._last_ws_message:
                elapsed = (datetime.now(UTC) - self._last_ws_message).total_seconds()
                msg_recent = elapsed < self.WS_HEALTH_CHECK_INTERVAL * 3
            
            healthy = rest_ok and ws_ok and msg_recent
            
            if self._health_check_callback:
                await self._health_check_callback(healthy, "Health check completed")
            
            return healthy
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def update_last_ws_message(self) -> None:
        """Update last WebSocket message timestamp."""
        self._last_ws_message = datetime.now(UTC)
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        await self.stop_heartbeat()
        await self.stop_ws_health_monitor()
        
        if self._ws_client:
            try:
                await self._ws_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting WS client: {e}")
            self._ws_client = None
        
        self._connected = False
        self._initialized = False
        logger.info("BingXDataProvider cleaned up")


def create_bingx_data_provider(
    api_key: str,
    api_secret: str,
    testnet: bool = False,
    recv_window: int = 5000,
    rate_limit_requests: int = 10,
    rate_limit_window_seconds: float = 1.0,
    websocket_ping_interval: float = 20.0,
    websocket_ping_timeout: float = 10.0,
    max_reconnect_attempts: int = 0,
    reconnect_base_delay: float = 1.0,
    reconnect_max_delay: float = 60.0,
) -> BingXDataProvider:
    """Factory function to create a BingXDataProvider instance."""
    return BingXDataProvider(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        recv_window=recv_window,
        rate_limit_requests=rate_limit_requests,
        rate_limit_window_seconds=rate_limit_window_seconds,
        websocket_ping_interval=websocket_ping_interval,
        websocket_ping_timeout=websocket_ping_timeout,
        max_reconnect_attempts=max_reconnect_attempts,
        reconnect_base_delay=reconnect_base_delay,
        reconnect_max_delay=reconnect_max_delay,
    )