"""
EVRECONSE Data Provider - Internal Models.

Internal immutable models for exchange market data.
These are NOT domain models - they belong to Data Provider only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MarketDataType(str, Enum):
    """Type of market data message."""

    CANDLE = "candle"
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    TICKER = "ticker"


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class Candle:
    """
    Candlestick data.

    Immutable candlestick representation from exchange.
    """

    symbol: str
    exchange: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: float
    trades_count: int
    taker_buy_volume: float
    taker_buy_quote_volume: float
    is_closed: bool

    def __post_init__(self) -> None:
        if self.open_time.tzinfo is None:
            raise ValueError("open_time must be timezone-aware")
        if self.close_time.tzinfo is None:
            raise ValueError("close_time must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Trade:
    """
    Individual trade execution.

    Immutable trade representation from exchange.
    """

    trade_id: str
    symbol: str
    exchange: str
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    timestamp: datetime
    is_buyer_maker: bool

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    """
    Single order book level (price + quantity).
    """

    price: float
    quantity: float


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    """
    Order book snapshot.

    Immutable order book state from exchange.
    """

    symbol: str
    exchange: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    timestamp: datetime
    update_id: int | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Ticker:
    """
    24hr ticker statistics.

    Immutable ticker data from exchange.
    """

    symbol: str
    exchange: str
    last_price: float
    price_change: float
    price_change_percent: float
    high_price: float
    low_price: float
    volume: float
    quote_volume: float
    open_price: float
    high_price_24h: float
    low_price_24h: float
    bid_price: float
    ask_price: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class MarketDataMessage:
    """
    Generic market data message from exchange.

    Wrapper for all types of market data messages.
    """

    data_type: MarketDataType
    symbol: str
    exchange: str
    timestamp: datetime
    data: Any
    raw_message: str | bytes | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")