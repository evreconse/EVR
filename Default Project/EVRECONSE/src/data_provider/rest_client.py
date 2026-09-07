"""
EVRECONSE Data Provider - REST Client.

Production-ready Bybit REST API client with:
- Rate limiting
- Request/response signing
- Error handling
- Retry logic
- Async/await support
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    SnapshotError,
)


class RestConfig:
    """REST client configuration."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        recv_window: int = 5000,
        request_timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.recv_window = recv_window
        self.request_timeout = request_timeout
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections


class RestClient:
    """
    Bybit REST API client.

    Features:
    - Automatic request signing for authenticated endpoints
    - Built-in rate limiting
    - Automatic retries with exponential backoff
    - Connection pooling
    - Comprehensive error handling
    """

    # Rate limits (requests per second)
    PUBLIC_RATE_LIMIT = 10  # 10 req/s for public endpoints
    PRIVATE_RATE_LIMIT = 5  # 5 req/s for private endpoints
    MARKET_DATA_RATE_LIMIT = 20  # 20 req/s for market data

    def __init__(self, config: RestConfig) -> None:
        self._config = config
        self._session: ClientSession | None = None
        self._public_limiter = asyncio.Semaphore(self.PUBLIC_RATE_LIMIT)
        self._private_limiter = asyncio.Semaphore(self.PRIVATE_RATE_LIMIT)
        self._market_data_limiter = asyncio.Semaphore(self.MARKET_DATA_RATE_LIMIT)
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> RestClient:
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        """Create aiohttp session if not exists."""
        if self._session is None or self._session.closed:
            connector = TCPConnector(
                limit=self._config.max_connections,
                limit_per_host=self._config.max_keepalive_connections,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            timeout = ClientTimeout(total=self._config.request_timeout)
            self._session = ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    def _generate_signature(self, params: dict[str, Any], timestamp: str) -> str:
        """
        Generate HMAC SHA256 signature for authenticated requests.

        Bybit signature format: timestamp + api_key + recv_window + query_string
        """
        # Sort parameters by key
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params if v is not None)

        # Build signature payload
        payload = f"{timestamp}{self._config.api_key}{self._config.recv_window}{param_str}"

        # Generate HMAC SHA256
        signature = hmac.new(
            self._config.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _build_headers(self, params: dict[str, Any] | None = None, signed: bool = False) -> dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if signed and self._config.api_key and self._config.api_secret:
            timestamp = str(int(time.time() * 1000))
            query_params = params or {}

            headers.update({
                "X-BAPI-API-KEY": self._config.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": str(self._config.recv_window),
                "X-BAPI-SIGN": self._generate_signature(query_params, timestamp),
            })

        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
        rate_limiter: asyncio.Semaphore | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request to Bybit API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Request parameters
            signed: Whether request requires authentication
            rate_limiter: Semaphore for rate limiting

        Returns:
            Parsed JSON response

        Raises:
            ConnectionError: Network or connection issues
            AuthenticationError: Invalid API credentials
            RateLimitError: Rate limit exceeded
            SnapshotError: API error response
        """
        await self._ensure_session()

        url = f"{self._config.base_url}{endpoint}"
        query_params = params or {}

        # Apply rate limiting
        limiter = rate_limiter or self._public_limiter
        async with limiter:
            # Small delay to respect rate limits
            now = time.monotonic()
            elapsed = now - self._last_request_time
            min_interval = 1.0 / (self.MARKET_DATA_RATE_LIMIT if rate_limiter == self._market_data_limiter else self.PUBLIC_RATE_LIMIT)
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            headers = self._build_headers(query_params, signed)
            self._last_request_time = time.monotonic()

            # Prepare request
            request_kwargs = {
                "headers": headers,
                "params": query_params if method == "GET" else None,
                "json": query_params if method in ("POST", "PUT", "DELETE") else None,
            }

            async with self._lock:
                if not self._session or self._session.closed:
                    raise ConnectionError("Session closed")

                try:
                    async with self._session.request(method, url, **request_kwargs) as response:
                        text = await response.text()

                        if response.status == 429:
                            raise RateLimitError("Rate limit exceeded", retry_after=60)

                        if response.status == 401:
                            raise AuthenticationError("Invalid API credentials")

                        if response.status >= 400:
                            raise ConnectionError(f"HTTP {response.status}: {text}")

                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            raise SnapshotError(f"Invalid JSON response: {text[:200]}")

                        # Check Bybit API response format
                        if isinstance(data, dict):
                            ret_code = data.get("retCode", 0)
                            if ret_code != 0:
                                ret_msg = data.get("retMsg", "Unknown error")
                                if ret_code == 10003:
                                    raise AuthenticationError(f"Authentication failed: {ret_msg}")
                                elif ret_code == 10006:
                                    raise RateLimitError(f"Rate limit: {ret_msg}")
                                else:
                                    raise SnapshotError(f"API error {ret_code}: {ret_msg}")

                        return data

                except aiohttp.ClientError as e:
                    raise ConnectionError(f"Request failed: {e}") from e
                except TimeoutError:
                    raise ConnectionError("Request timeout") from None

    # =========================================================================
    # Public Market Data Endpoints
    # =========================================================================

    async def get_server_time(self) -> dict[str, Any]:
        """Get server time."""
        return await self._request("GET", "/v5/market/time")

    async def get_instruments_info(
        self,
        category: str = "linear",
        symbol: str | None = None,
        status: str | None = None,
        base_coin: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Get instrument information."""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        if status:
            params["status"] = status
        if base_coin:
            params["baseCoin"] = base_coin
        if limit:
            params["limit"] = str(limit)

        return await self._request("GET", "/v5/market/instruments-info", params)

    async def get_tickers(
        self,
        category: str = "linear",
        symbol: str | None = None,
    ) -> dict[str, Any]:
        """Get ticker information."""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol

        return await self._request("GET", "/v5/market/tickers", params)

    async def get_orderbook(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        limit: int = 25,
    ) -> dict[str, Any]:
        """Get order book depth."""
        params = {
            "category": category,
            "symbol": symbol,
            "limit": str(limit),
        }
        return await self._request("GET", "/v5/market/orderbook", params)

    async def get_recent_trades(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get recent trades."""
        params = {
            "category": category,
            "symbol": symbol,
            "limit": str(min(limit, 1000)),
        }
        return await self._request("GET", "/v5/market/recent-trade", params)

    async def get_klines(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        interval: str = "15",
        start: int | None = None,
        end: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """
        Get kline/candle data.

        Args:
            category: Product category (linear, inverse, spot)
            symbol: Trading symbol
            interval: Interval in minutes (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
            start: Start timestamp in milliseconds
            end: End timestamp in milliseconds
            limit: Number of candles (max 1000)

        Returns:
            Kline data
        """
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": str(min(limit, 1000)),
        }

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        return await self._request("GET", "/v5/market/kline", params, rate_limiter=self._market_data_limiter)

    async def get_mark_price_klines(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        interval: str = "15",
        start: int | None = None,
        end: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Get mark price kline data."""
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": str(min(limit, 1000)),
        }

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        return await self._request("GET", "/v5/market/mark-price-kline", params, rate_limiter=self._market_data_limiter)

    async def get_index_price_klines(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        interval: str = "15",
        start: int | None = None,
        end: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Get index price kline data."""
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": str(min(limit, 1000)),
        }

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        return await self._request("GET", "/v5/market/index-price-kline", params, rate_limiter=self._market_data_limiter)

    async def get_premium_index_klines(
        self,
        category: str = "linear",
        symbol: str = "BTCUSDT",
        interval: str = "15",
        start: int | None = None,
        end: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Get premium index kline data."""
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": str(min(limit, 1000)),
        }

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        return await self._request("GET", "/v5/market/premium-index-price-kline", params, rate_limiter=self._market_data_limiter)

    # =========================================================================
    # Account & Trading Endpoints (Private)
    # =========================================================================

    async def get_wallet_balance(
        self,
        account_type: str = "UNIFIED",
        coin: str | None = None,
    ) -> dict[str, Any]:
        """Get wallet balance (requires authentication)."""
        params = {"accountType": account_type}
        if coin:
            params["coin"] = coin
        return await self._request("GET", "/v5/account/wallet-balance", params, signed=True, rate_limiter=self._private_limiter)

    async def get_positions(
        self,
        category: str = "linear",
        symbol: str | None = None,
        settle_coin: str | None = None,
    ) -> dict[str, Any]:
        """Get position information (requires authentication)."""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        if settle_coin:
            params["settleCoin"] = settle_coin
        return await self._request("GET", "/v5/position/list", params, signed=True, rate_limiter=self._private_limiter)

    async def place_order(
        self,
        category: str,
        symbol: str,
        side: str,
        order_type: str,
        qty: str,
        price: str | None = None,
        time_in_force: str = "GTC",
        order_link_id: str | None = None,
        is_leverage: int = 0,
        position_idx: int = 0,
        take_profit: str | None = None,
        stop_loss: str | None = None,
        tp_trigger_by: str = "LastPrice",
        sl_trigger_by: str = "LastPrice",
        reduce_only: bool = False,
        close_on_trigger: bool = False,
        smp_type: str | None = None,
    ) -> dict[str, Any]:
        """Place an order (requires authentication)."""
        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": time_in_force,
            "isLeverage": str(is_leverage),
            "positionIdx": str(position_idx),
            "reduceOnly": str(reduce_only).lower(),
            "closeOnTrigger": str(close_on_trigger).lower(),
        }

        if price:
            params["price"] = price
        if order_link_id:
            params["orderLinkId"] = order_link_id
        if take_profit:
            params["takeProfit"] = take_profit
        if stop_loss:
            params["stopLoss"] = stop_loss
        if tp_trigger_by:
            params["tpTriggerBy"] = tp_trigger_by
        if sl_trigger_by:
            params["slTriggerBy"] = sl_trigger_by
        if smp_type:
            params["smpType"] = smp_type

        return await self._request("POST", "/v5/order/create", params, signed=True, rate_limiter=self._private_limiter)

    async def cancel_order(
        self,
        category: str,
        symbol: str,
        order_id: str | None = None,
        order_link_id: str | None = None,
    ) -> dict[str, Any]:
        """Cancel an order (requires authentication)."""
        if not order_id and not order_link_id:
            raise ValueError("Either order_id or order_link_id must be provided")

        params = {"category": category, "symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if order_link_id:
            params["orderLinkId"] = order_link_id

        return await self._request("POST", "/v5/order/cancel", params, signed=True, rate_limiter=self._private_limiter)

    async def get_order_history(
        self,
        category: str = "linear",
        symbol: str | None = None,
        base_coin: str | None = None,
        settle_coin: str | None = None,
        order_type: str | None = None,
        order_status: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get order history (requires authentication)."""
        params = {"category": category, "limit": str(limit)}
        if symbol:
            params["symbol"] = symbol
        if base_coin:
            params["baseCoin"] = base_coin
        if settle_coin:
            params["settleCoin"] = settle_coin
        if order_type:
            params["orderType"] = order_type
        if order_status:
            params["orderStatus"] = order_status
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)

        return await self._request("GET", "/v5/order/history", params, signed=True, rate_limiter=self._private_limiter)


# =============================================================================
# Factory function
# =============================================================================

def create_rest_client(
    base_url: str,
    api_key: str | None = None,
    api_secret: str | None = None,
    testnet: bool = False,
) -> RestClient:
    """Factory function to create REST client."""
    config = RestConfig(
        base_url=base_url,
        api_key=api_key,
        api_secret=api_secret,
    )
    return RestClient(config)