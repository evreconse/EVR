"""
EVRECONSE Data Provider Module.

Market data provider abstraction with BingX implementation.
"""

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    DataProviderError,
    DataProviderNotConnectedError,
    DataProviderNotInitializedError,
    HeartbeatTimeoutError,
    InvalidMessageError,
    RateLimitError,
    ReconnectError,
    SnapshotError,
    SubscriptionError,
)
from .heartbeat import HeartbeatConfig, HeartbeatMonitor
from .internal_models import (
    Candle,
    MarketDataMessage,
    MarketDataType,
    OrderBookLevel,
    OrderBookSnapshot,
    OrderSide,
    Ticker,
    Trade,
)
from .provider import MarketDataProvider
from .bingx_provider import BingXDataProvider, create_bingx_data_provider

DataProvider = MarketDataProvider
from .rate_limiter import RateLimitConfig, RateLimiter
from .reconnect_strategy import ReconnectConfig, ReconnectStrategy
from .rest_client import RestClient, RestConfig
from .websocket_client import WebSocketClient, BingXWebSocketClient, create_bingx_websocket_client

__all__ = [
    # Main interface
    "MarketDataProvider",
    "DataProvider",
    "BingXDataProvider",
    "create_bingx_data_provider",
    # WebSocket
    "WebSocketClient",
    "BingXWebSocketClient",
    "create_bingx_websocket_client",
    # REST
    "RestClient",
    "RestConfig",
    # Components
    "RateLimiter",
    "RateLimitConfig",
    "ReconnectStrategy",
    "ReconnectConfig",
    "HeartbeatMonitor",
    "HeartbeatConfig",
    # Internal models
    "Candle",
    "Trade",
    "OrderBookSnapshot",
    "OrderBookLevel",
    "Ticker",
    "MarketDataMessage",
    "MarketDataType",
    "OrderSide",
    # Exceptions
    "DataProviderError",
    "ConnectionError",
    "AuthenticationError",
    "SubscriptionError",
    "RateLimitError",
    "ReconnectError",
    "HeartbeatTimeoutError",
    "InvalidMessageError",
    "SnapshotError",
    "DataProviderNotInitializedError",
    "DataProviderNotConnectedError",
]