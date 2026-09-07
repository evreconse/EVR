"""
EVRECONSE Data Provider - Provider Interface.

Abstract interface for market data providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from models import MarketEvent


class MarketDataProvider(ABC):
    """
    Abstract interface for market data providers.

    All exchange implementations must implement this interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the exchange."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to exchange."""
        ...

    @abstractmethod
    async def reconnect(self) -> None:
        """Reconnect to exchange."""
        ...

    @abstractmethod
    async def subscribe_symbols(self, symbols: list[str], timeframe: str) -> None:
        """
        Subscribe to market data for symbols.

        Args:
            symbols: List of trading symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframe: Candle timeframe (e.g., "15m")

        Raises:
            SubscriptionError: If subscription fails.
        """
        ...

    @abstractmethod
    async def unsubscribe_symbols(self, symbols: list[str]) -> None:
        """Unsubscribe from market data for symbols."""
        ...

    @abstractmethod
    async def subscribe_timeframe(self, timeframe: str) -> None:
        """
        Subscribe to a new timeframe.

        Args:
            timeframe: Timeframe to subscribe to (e.g., "15m")

        Raises:
            SubscriptionError: If subscription fails.
        """
        ...

    @abstractmethod
    def get_snapshot(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1,
    ) -> list[dict]:
        """
        Get historical snapshot of candles.

        Args:
            symbol: Trading symbol.
            timeframe: Timeframe for candles.
            limit: Number of candles to retrieve.

        Returns:
            List of candle data dictionaries.
        """
        ...

    @abstractmethod
    async def stream(self) -> AsyncGenerator[MarketEvent, None]:
        """
        Stream market events in real-time.

        Yields:
            MarketEvent objects as they are generated.
        """
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """
        Ping the exchange to check connectivity.

        Returns:
            True if ping successful, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """Get the exchange name."""
        ...

    @property
    @abstractmethod
    def supported_timeframes(self) -> list[str]:
        """Get list of supported timeframes."""
        ...

    @property
    @abstractmethod
    def supported_symbols(self) -> list[str]:
        """Get list of supported trading symbols."""
        ...