# ruff: noqa
# mypy: ignore-errors
"""
BingX API Fetcher for EVRECONSE

Handles authentication, kline data fetching, symbol listing, and trading operations for BingX perpetual futures.
"""
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception
import hashlib
import hmac
import time
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, cast
import os
from pathlib import Path

from .bingx_rate_limiter import (
    BingXRateLimiter,
    BingXAPIError,
    BingXRateLimitError,
    BingXOfflineSymbolError,
    is_rate_limit_error,
    is_offline_symbol_error,
    classify_bingx_error,
)


class BingXFetcher:
    """
    BingX API client for perpetual futures data.

    API Documentation: https://bingx-api.github.io/docs/swap/

    Rate Limits (Official): 500 requests per 10 seconds per IP for market data endpoints
    Conservative limit used: 450 requests per 10 seconds
    """

    BASE_URL = "https://open-api.bingx.com"

    # Class-level rate limiter shared across all instances
    _rate_limiter: Optional[BingXRateLimiter] = None

    @classmethod
    def get_rate_limiter(cls) -> BingXRateLimiter:
        """Get or create the shared rate limiter."""
        if cls._rate_limiter is None:
            cls._rate_limiter = BingXRateLimiter(
                max_requests=450,  # 500 limit with 10% margin
                window_seconds=10.0,
                safety_margin=1.0
            )
        return cls._rate_limiter

    @classmethod
    def reset_rate_limiter(cls):
        """Reset the shared rate limiter (for testing)."""
        cls._rate_limiter = None

    def __init__(self, api_key: str = None, api_secret: str = None, rate_limiter: Optional[BingXRateLimiter] = None):
        """
        Initialize BingX fetcher with credentials.

        Args:
            api_key: BingX API key (from .env if not provided)
            api_secret: BingX API secret (from .env if not provided)
            rate_limiter: Optional custom rate limiter (uses shared if not provided)
        """
        # Try to load from .env file using dotenv
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"Loaded .env from {env_path}")
        else:
            print(f"Warning: .env file not found at {env_path}")

        self.api_key = api_key or os.environ.get("EVRECONSE_EXCHANGE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("EVRECONSE_EXCHANGE_API_SECRET", "")

        if not self.api_key or not self.api_secret:
            raise ValueError("BingX API credentials not provided. Set EVRECONSE_EXCHANGE_API_KEY and EVRECONSE_EXCHANGE_API_SECRET in .env file or environment variables.")

        # Use provided rate limiter or shared one
        self.rate_limiter = rate_limiter or self.get_rate_limiter()

        # Statistics
        self._stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "rate_limit_hits": 0,
            "rate_limit_retries": 0,
            "offline_symbols": 0,
            "other_errors": 0,
        }

    def _generate_signature(self, timestamp: str, params: str) -> str:
        """Generate HMAC SHA256 signature for BingX API."""
        signature_string = timestamp + params
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_timestamp(self) -> str:
        """Get current timestamp in milliseconds."""
        return str(int(time.time() * 1000))

    def _check_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error that should be retried."""
        msg = str(error).lower()
        return (
            "rate limit" in msg or
            "请稍后重试" in msg or
            "please try again later" in msg or
            "too many requests" in msg or
            "100401" in msg or
            "429" in msg
        )

    def _check_offline_symbol(self, error: Exception) -> bool:
        """Check if error indicates symbol is offline."""
        msg = str(error).lower()
        return (
            "offline currently" in msg or
            "is offline" in msg or
            "delisted" in msg or
            "100402" in msg
        )

    async def _request_with_rate_limit(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to BingX API with rate limiting and retries.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET/POST)
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            BingXRateLimitError: If rate limit is hit and retries exhausted
            BingXOfflineSymbolError: If symbol is offline
            BingXAPIError: For other API errors
        """
        if params is None:
            params = {}

        max_retries = 5
        base_wait = 1.0
        max_wait = 30.0

        for attempt in range(max_retries):
            # Acquire rate limit permission
            wait_time = await self.rate_limiter.acquire()
            if wait_time > 0:
                self._stats["rate_limit_hits"] += 1

            try:
                # Add required timestamp
                timestamp = str(int(time.time() * 1000))
                params = params or {}
                params["timestamp"] = str(int(time.time() * 1000))

                # Build query string
                query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])

                # Generate signature
                signature = self._generate_signature(timestamp, query_string)

                # Build full URL
                url = f"{self.BASE_URL}{endpoint}?{query_string}"

                headers = {
                    "X-BX-APIKEY": self.api_key,
                    "Content-Type": "application/json",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, headers=headers) as resp:
                        text = await resp.text()

                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}: {text}")

                        try:
                            import json
                            text = text.replace('\x00', '')
                            data = json.loads(text)
                        except Exception as e:
                            raise Exception(f"JSON decode error: {e}")

                        # BingX returns {code: 0, msg: "success", data: {...}} or {code: xxx, msg: "error"}
                        code = data.get("code", 0)
                        msg = data.get("msg", "Unknown error")

                        if code == 0:
                            return data.get("data", {})

                        # Handle specific error codes
                        error_msg = f"API Error (code={code}): {msg}"

                        # Check for rate limit
                        if code in (100401, 429) or "请稍后重试" in msg or "rate limit" in msg.lower():
                            raise BingXRateLimitError(error_msg, code=code)

                        # Check for offline symbol
                        if code == 100402 or "offline currently" in msg or "is offline" in msg.lower():
                            raise BingXOfflineSymbolError(error_msg, code=code)

                        # Other API errors
                        raise Exception(error_msg)

            except BingXRateLimitError:
                # Rate limit error - will retry
                self._stats["rate_limit_retries"] += 1
                raise
            except BingXOfflineSymbolError:
                # Offline symbol - don't retry
                self._stats["offline_symbols"] += 1
                raise
            except Exception as e:
                # Other errors - may retry depending on type
                if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                    raise
                raise

            # If we get here, it was a successful request
            break

        # This shouldn't be reached due to reraise
        raise Exception("Max retries exceeded")

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make request with retry logic for rate limits.

        Uses exponential backoff with jitter for rate limit errors.
        """
        max_retries = 5
        base_wait = 1.0
        max_wait = 30.0

        last_exception = None

        for attempt in range(max_retries):
            try:
                result = await self._request_with_rate_limit(endpoint, method, params)
                self._stats["requests_success"] += 1
                return result
            except BingXRateLimitError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait = min(2 ** attempt * 1.0 + (attempt * 0.1), 30.0)
                    import random
                    wait += random.uniform(0, 0.5)  # jitter
                    self._stats["rate_limit_retries"] += 1
                    await asyncio.sleep(wait)
                    continue
                raise
            except BingXOfflineSymbolError:
                self._stats["offline_symbols"] += 1
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait = min(2 ** attempt * 1.0, 10.0)
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception as e:
                # Non-retryable error
                self._stats["other_errors"] += 1
                raise

        raise last_exception or Exception("Max retries exceeded")

    def _generate_signature(self, timestamp: str, params: str) -> str:
        """Generate HMAC SHA256 signature for BingX API."""
        signature_string = timestamp + params
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_timestamp(self) -> str:
        """Get current timestamp in milliseconds."""
        return str(int(time.time() * 1000))

    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Legacy method for backward compatibility - uses new rate-limited request."""
        return await self._make_request(endpoint, method, params)

    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        stats = self._stats.copy()
        stats.update(self.rate_limiter.get_stats())
        return stats

    def reset_stats(self):
        """Reset statistics."""
        self._stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "rate_limit_hits": 0,
            "rate_limit_retries": 0,
            "offline_symbols": 0,
            "other_errors": 0,
        }
        self.rate_limiter.reset_stats()

    # ==================== PUBLIC API METHODS ====================

    async def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch kline/candlestick data with pagination support.

        Args:
            symbol: Trading pair in BASE-QUOTE format (e.g., BTC-USDT)
            interval: Kline interval (1m/5m/15m/30m/1h/4h/1d)
            limit: Number of candles (max 1440 per request)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of dicts: {'time': ms, 'open': str, 'high': str, 'low': str, 'close': str, 'volume': str}
        """
        all_klines: List[Dict[str, Any]] = []
        current_end = end_time
        max_per_request = 1000  # BingX max limit

        while True:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(max_per_request, limit) if limit else max_per_request,
            }

            # Only use endTime for pagination, not startTime
            if current_end:
                params["endTime"] = current_end

            data = await self._make_request("/openApi/swap/v3/quote/klines", "GET", params)

            # BingX returns array of dicts
            if isinstance(data, list) and data:
                data_reversed = list(reversed(data))
                all_klines.extend(data_reversed)

                if len(data) < 1000:
                    break

                first_item = data[0]
                if isinstance(first_item, dict):
                    first_time = int(first_item.get("time", 0))
                else:
                    first_time = int(first_item[0])
                current_end = first_time - 1

                if start_time and current_end <= start_time:
                    break

                if limit and len(all_klines) >= limit:
                    all_klines = all_klines[:limit]
                    break
            else:
                break

        return all_klines

    async def get_contracts(self) -> List[Dict[str, Any]]:
        """Fetch all perpetual contract specifications."""
        data = await self._make_request("/openApi/swap/v2/quote/contracts", "GET")
        if isinstance(data, list):
            return data
        return []

    async def get_usdt_perpetual_symbols(self) -> List[str]:
        """Get all USDT perpetual trading pairs."""
        contracts = await self.get_contracts()
        symbols = []
        for contract in contracts:
            symbol = contract.get("symbol", "")
            if symbol.endswith("-USDT"):
                symbols.append(symbol)
        return symbols

    # ==================== ACCOUNT & SYMBOL INFO METHODS ====================

    async def get_account_info(self) -> Dict[str, Any]:
        data = await self._make_request("/openApi/swap/v2/user/account", "GET")
        return data

    async def get_balance(self, asset: str = "USDT") -> Optional[float]:
        try:
            data = await self._make_request("/openApi/swap/v2/user/balance", "GET")
            if data.get("code") == 0:
                balances = data.get("data", {}).get("balance", [])
                if isinstance(balances, list):
                    for balance in balances:
                        if balance.get("asset") == asset:
                            return float(balance.get("availableMargin", 0))
                elif isinstance(balances, dict):
                    if balances.get("asset") == asset:
                        return float(balances.get("availableMargin", 0))
            return None
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return await self._make_request("/openApi/swap/v2/trade/order", "GET", params)

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        contracts = await self.get_contracts()
        for contract in contracts:
            if contract.get("symbol") == symbol:
                return contract
        return None

    async def get_all_symbol_infos(self) -> Dict[str, Dict[str, Any]]:
        contracts = await self.get_contracts()
        result = {}
        for contract in contracts:
            symbol = contract.get("symbol", "")
            if symbol.endswith("-USDT"):
                result[symbol] = contract
        return result

    async def set_margin_type(self, symbol: str, margin_type: str = "CROSS") -> bool:
        params = {"symbol": symbol, "marginType": margin_type}
        data = await self._make_request("/openApi/swap/v2/trade/marginType", "POST", params)
        return data.get("code") == 0

    async def set_position_mode(self, position_mode: str = "HEDGE") -> bool:
        params = {"dualSidePosition": "true" if position_mode == "HEDGE" else "false"}
        data = await self._make_request("/openApi/swap/v2/trade/positionSide", "POST", params)
        return data.get("code") == 0

    async def get_position_mode(self) -> Optional[str]:
        try:
            account = await self.get_account_info()
            dual_side = account.get("dualSidePosition", "false")
            return "HEDGE" if dual_side == "true" else "ONE_WAY"
        except Exception as e:
            print(f"Error getting position mode: {e}")
            return None

    async def set_leverage(self, symbol: str, leverage: int, side: str = "LONG") -> bool:
        params = {"symbol": symbol, "leverage": leverage, "side": side}
        data = await self._make_request("/openApi/swap/v2/trade/leverage", "POST", params)
        return data.get("code") == 0

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            data = await self._make_request("/openApi/swap/v2/user/positions", "GET")
            if isinstance(data, list):
                return cast(List[Dict[str, Any]], data)
            return []
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        contracts = await self.get_contracts()
        for contract in contracts:
            if contract.get("symbol") == symbol:
                return contract
        return None

    async def get_all_symbol_infos(self) -> Dict[str, Dict[str, Any]]:
        contracts = await self.get_contracts()
        result = {}
        for contract in contracts:
            symbol = contract.get("symbol", "")
            if symbol.endswith("-USDT"):
                result[symbol] = contract
        return result

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        try:
            data = await self._make_request("/openApi/swap/v2/trade/openOrders", "GET", {"symbol": symbol})
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return data.get("data", {}).get("orders", [])
            return []
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return []

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            data = await self._make_request("/openApi/swap/v2/user/positions", "GET")
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    # ==================== SYMBOL SPECIFICATIONS ====================

    async def refresh_symbol_specs(self) -> Dict[str, Dict[str, Any]]:
        contracts = await self.get_contracts()
        specs = {}
        for contract in contracts:
            symbol = contract.get("symbol", "")
            if symbol.endswith("-USDT"):
                specs[symbol] = {
                    "qtyStep": float(contract.get("qtyStep", "0.001")),
                    "minQty": float(contract.get("minQty", "0.001")),
                    "maxQty": float(contract.get("maxQty", "1000000")),
                    "minNotional": float(contract.get("minNotional", "5")),
                    "pricePrecision": int(contract.get("pricePrecision", "2")),
                    "quantityPrecision": int(contract.get("quantityPrecision", "3")),
                    "baseAsset": contract.get("baseAsset", ""),
                    "quoteAsset": contract.get("quoteAsset", "USDT"),
                }
        return specs

    # ==================== HELPER METHODS ====================

    @staticmethod
    def round_to_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        return math.floor(value / step) * step

    @staticmethod
    def round_up_to_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        return math.ceil(value / step) * step

    @staticmethod
    def round_to_precision(value: float, precision: int) -> float:
        if precision < 0:
            return value
        factor = 10 ** precision
        return round(value * factor) / factor

    @staticmethod
    def calculate_quantity_for_notional(
        notional_usdt: float,
        entry_price: float,
        qty_step: float,
        min_qty: float,
        min_notional: float,
        leverage: int = 20
    ) -> Tuple[float, str]:
        if entry_price <= 0:
            return 0.0, "Invalid entry price"
        raw_qty = notional_usdt / entry_price
        qty = BingXFetcher.round_up_to_step(raw_qty, qty_step)
        if qty < min_qty:
            return 0.0, f"Quantity {qty} below minQty {min_qty}"
        notional = qty * entry_price
        if notional < min_notional:
            return 0.0, f"Notional {notional} below minNotional {min_notional}"
        return qty, ""

    @staticmethod
    def calculate_tp_price(entry_price: float, position_side: str, tp_pct: float = 5.0) -> float:
        if position_side == "LONG":
            return entry_price * (1 + tp_pct / 100)
        else:
            return entry_price * (1 - tp_pct / 100)

    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        stats = {
            "requests_success": getattr(self, '_stats', {}).get("requests_success", 0),
            "rate_limit_hits": self.rate_limiter.get_stats().get("rate_limit_hits", 0),
            "rate_limit_retries": getattr(self, '_stats', {}).get("rate_limit_retries", 0),
            "offline_symbols": getattr(self, '_stats', {}).get("offline_symbols", 0),
            "other_errors": getattr(self, '_stats', {}).get("other_errors", 0),
        }
        return stats

    def reset_stats(self):
        """Reset statistics."""
        if hasattr(self, '_stats'):
            self._stats = {
                "requests_total": 0,
                "requests_success": 0,
                "requests_failed": 0,
                "rate_limit_hits": 0,
                "rate_limit_retries": 0,
                "offline_symbols": 0,
                "other_errors": 0,
            }
        if self.rate_limiter:
            self.rate_limiter.reset_stats()
