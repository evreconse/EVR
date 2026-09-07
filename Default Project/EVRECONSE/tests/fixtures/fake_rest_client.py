"""
Fake REST Client for testing.

Provides a MagicMock-based fake RestClient that does not make real API calls.
"""

from __future__ import annotations

from typing import Any


class FakeRestClient:
    """Fake REST client for unit tests."""

    def __init__(self) -> None:
        self._session_open = False
        self._calls: list[tuple[str, str, dict[str, Any]]] = []

    async def __aenter__(self) -> FakeRestClient:
        self._session_open = True
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._session_open = False

    async def close(self) -> None:
        self._session_open = False

    async def get_server_time(self) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/time", {}))
        return {"result": {"time": "2026-01-01T00:00:00Z"}}

    async def get_instruments_info(self, category: str = "linear", symbol: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/instruments-info", {"category": category, "symbol": symbol}))
        return {"result": {"list": []}}

    async def get_tickers(self, category: str = "linear", symbol: str | None = None) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/tickers", {"category": category}))
        return {"result": {"list": []}}

    async def get_orderbook(self, category: str = "linear", symbol: str = "BTCUSDT", limit: int = 25) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/orderbook", {"symbol": symbol}))
        return {"result": {"bids": [], "asks": []}}

    async def get_recent_trades(self, category: str = "linear", symbol: str = "BTCUSDT", limit: int = 100) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/recent-trade", {"symbol": symbol}))
        return {"result": {"list": []}}

    async def get_klines(self, category: str = "linear", symbol: str = "BTCUSDT", interval: str = "15", start: int | None = None, end: int | None = None, limit: int = 200) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/market/kline", {"symbol": symbol, "interval": interval}))
        return {"result": {"list": []}}

    async def get_mark_price_klines(self, **kwargs: Any) -> dict[str, Any]:
        return {"result": {"list": []}}

    async def get_index_price_klines(self, **kwargs: Any) -> dict[str, Any]:
        return {"result": {"list": []}}

    async def get_premium_index_klines(self, **kwargs: Any) -> dict[str, Any]:
        return {"result": {"list": []}}

    async def get_wallet_balance(self, account_type: str = "UNIFIED", coin: str | None = None) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/account/wallet-balance", {"account_type": account_type}))
        return {"result": {"list": []}}

    async def get_positions(self, category: str = "linear", symbol: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/position/list", {"category": category}))
        return {"result": {"list": []}}

    async def place_order(self, category: str = "", symbol: str = "", side: str = "", order_type: str = "", qty: str = "", **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("POST", "/v5/order/create", {"symbol": symbol, "side": side}))
        return {"result": {"orderId": "test-order-id"}}

    async def cancel_order(self, category: str = "", symbol: str = "", order_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("POST", "/v5/order/cancel", {"symbol": symbol}))
        return {"result": {}}

    async def get_order_history(self, category: str = "linear", symbol: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("GET", "/v5/order/history", {}))
        return {"result": {"list": []}}

    def get_calls(self) -> list[tuple[str, str, dict[str, Any]]]:
        return list(self._calls)


def create_fake_rest_client() -> FakeRestClient:
    """Factory function to create a fake REST client."""
    return FakeRestClient()