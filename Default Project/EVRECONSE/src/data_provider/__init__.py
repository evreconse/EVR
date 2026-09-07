"""
EVRECONSE Data Provider Module.

Market data provider abstraction with Bybit implementation.
"""

from .bybit_provider import BybitDataProvider, BybitDataProviderConfig
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
    Liquidation,
    LiquidationSide,
    MarketDataMessage,
    MarketDataType,
    OrderBookLevel,
    OrderBookSnapshot,
    OrderSide,
    Ticker,
    Trade,
)
from .provider import MarketDataProvider

DataProvider = MarketDataProvider
from .rate_limiter import RateLimitConfig, RateLimiter
from .reconnect_strategy import ReconnectConfig, ReconnectStrategy
from .rest_client import RestClient, RestConfig
from .websocket_client import WebSocketClient

__all__ = [
    # Main interface
    "MarketDataProvider",
    "DataProvider",
    "BybitDataProvider",
    "BybitDataProviderConfig",
    # WebSocket
    "WebSocketClient",
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
    "Liquidation",
    "OrderBookSnapshot",
    "OrderBookLevel",
    "Ticker",
    "MarketDataMessage",
    "MarketDataType",
    "OrderSide",
    "LiquidationSide",
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