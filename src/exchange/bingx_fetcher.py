"""
BingX API Fetcher for EVRECONSE

Handles authentication, kline data fetching, symbol listing, and trading operations for BingX perpetual futures.
"""
import asyncio
import aiohttp
import hashlib
import hmac
import time
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import os
from pathlib import Path


class BingXFetcher:
    """
    BingX API client for perpetual futures data.
    
    API Documentation: https://bingx-api.github.io/docs/swap/
    """
    
    BASE_URL = "https://open-api.bingx.com"
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize BingX fetcher with credentials.
        
        Args:
            api_key: BingX API key (from .env if not provided)
            api_secret: BingX API secret (from .env if not provided)
        """
        # Try to load from .env file using dotenv
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"Loaded .env from {env_path}")
            # Debug: print all env vars starting with EVRECONSE
            for key, value in os.environ.items():
                if key.startswith("EVRECONSE"):
                    print(f"  {key}: {value[:20]}..." if len(value) > 20 else f"  {key}: {value}")
        else:
            print(f"Warning: .env file not found at {env_path}")
        
        self.api_key = api_key or os.environ.get("EVRECONSE_EXCHANGE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("EVRECONSE_EXCHANGE_API_SECRET", "")
        
        print(f"DEBUG: API_KEY exists: {bool(self.api_key)}, API_SECRET exists: {bool(self.api_secret)}")
        print(f"DEBUG: API_KEY length: {len(self.api_key) if self.api_key else 0}, API_SECRET length: {len(self.api_secret) if self.api_secret else 0}")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("BingX API credentials not provided. Set EVRECONSE_EXCHANGE_API_KEY and EVRECONSE_EXCHANGE_API_SECRET in .env file or environment variables.")
    
    def _generate_signature(self, timestamp: str, params: str) -> str:
        """
        Generate HMAC SHA256 signature for BingX API.
        
        Args:
            timestamp: Request timestamp in milliseconds
            params: Query parameters string
            
        Returns:
            Hex-encoded signature
        """
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
        """
        Make authenticated request to BingX API.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET)
            params: Query parameters
            
        Returns:
            Response JSON data
        """
        if params is None:
            params = {}
        
        # Add required timestamp
        timestamp = self._get_timestamp()
        params["timestamp"] = timestamp
        
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
                    # Handle potential null characters in response
                    text = text.replace('\x00', '')
                    data = json.loads(text)
                except Exception as e:
                    print(f"JSON decode error: {e}")
                    print(f"Response text (first 500 chars): {text[:500]}")
                    raise Exception(f"JSON decode error: {e}")
                
                # BingX returns {code: 0, msg: "success", data: {...}} or {code: xxx, msg: "error"}
                if data.get("code") != 0:
                    raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")
                
                return data.get("data", {})
    
    async def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 500,
        start_time: int = None,
        end_time: int = None
    ) -> List[List]:
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
        all_klines = []
        current_end = end_time
        max_per_request = 1000  # BingX max limit
        
        while True:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(max_per_request, limit) if limit else max_per_request,
            }
            
            # Only use endTime for pagination, not startTime
            # This allows working backwards from the most recent data
            if current_end:
                params["endTime"] = current_end
            
            data = await self._request("/openApi/swap/v3/quote/klines", "GET", params)
            
            # BingX returns array of dicts: {'time': ms, 'open': str, 'high': str, 'low': str, 'close': str, 'volume': str}
            if isinstance(data, list) and data:
                # BingX returns data in reverse order (newest first), so reverse it
                data_reversed = list(reversed(data))
                all_klines.extend(data_reversed)
                
                # If we got less than requested, we've reached the end
                if len(data) < max_per_request:
                    break
                
                # Update end_time for next request (use first candle's time - 1)
                # Since data is newest first, the first item is the newest
                first_item = data[0]
                if isinstance(first_item, dict):
                    first_time = int(first_item.get("time", 0))
                else:
                    first_time = int(first_item[0])
                current_end = first_time - 1
                
                # Check if we've reached start_time
                if start_time and current_end <= start_time:
                    break
                
                # Check if we've reached limit
                if limit and len(all_klines) >= limit:
                    all_klines = all_klines[:limit]
                    break
            else:
                break
        
        return all_klines
    
    async def get_contracts(self) -> List[Dict[str, Any]]:
        """
        Fetch all perpetual contract specifications.
        
        BingX API returns all contracts in a single response regardless of pagination parameters.
        
        Returns:
            List of contract info dictionaries
        """
        data = await self._request("/openApi/swap/v2/quote/contracts", "GET")
        
        if isinstance(data, list):
            return data
        return []
    
    async def get_usdt_perpetual_symbols(self) -> List[str]:
        """
        Get all USDT perpetual trading pairs.
        
        Returns:
            List of symbol names (e.g., ["BTC-USDT", "ETH-USDT"])
        """
        contracts = await self.get_contracts()
        
        symbols = []
        for contract in contracts:
            symbol = contract.get("symbol", "")
            # Filter for USDT perpetual contracts
            if symbol.endswith("-USDT"):
                symbols.append(symbol)
        
        return symbols

    # ==================== ACCOUNT & SYMBOL INFO METHODS ====================

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information including margin mode, position mode, and leverage.
        
        Returns:
            Dictionary with account information
        """
        data = await self._request("/openApi/swap/v2/user/account", "GET")
        return data

    async def get_balance(self, asset: str = "USDT") -> Optional[float]:
        """
        Get available balance for a specific asset.
        
        Args:
            asset: Asset symbol (e.g., USDT)
            
        Returns:
            Available balance or None if error
        """
        try:
            data = await self._request("/openApi/swap/v2/user/balance", "GET")
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
        """
        Get order status by order ID.
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order status information
        """
        params = {
            "symbol": symbol,
            "orderId": order_id,
        }
        data = await self._request("/openApi/swap/v2/trade/order", "GET", params)
        return data

    async def wait_for_order_fill(
        self, 
        symbol: str, 
        order_id: str, 
        timeout: int = 30,
        poll_interval: float = 0.5
    ) -> Optional[float]:
        """
        Wait for an order to be filled and return the average fill price.
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Average fill price or None if not filled/timeout/error
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                order_status = await self.get_order_status(symbol, order_id)
                if order_status.get("code") == 0:
                    order_data = order_status.get("data", {}).get("order", {})
                    status = order_data.get("status")
                    if status == "FILLED":
                        avg_price = order_data.get("avgPrice")
                        if avg_price:
                            return float(avg_price)
                    elif status in ["CANCELED", "REJECTED", "EXPIRED", "FAILED"]:
                        return None
            except Exception as e:
                print(f"[WARNING] Error checking order status: {e}")
            
            await asyncio.sleep(poll_interval)
        
        return None  # Timeout

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed contract specifications for a symbol.
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            
        Returns:
            Dictionary with symbol specifications including:
            - qtyStep: minimum quantity step
            - minQty: minimum order quantity
            - maxQty: maximum order quantity
            - minNotional: minimum notional value
            - pricePrecision: price decimal precision
            - quantityPrecision: quantity decimal precision
        """
        contracts = await self.get_contracts()
        for contract in contracts:
            if contract.get("symbol") == symbol:
                return contract
        return None

    async def get_all_symbol_infos(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all symbol infos as a dictionary keyed by symbol.
        
        Returns:
            Dictionary mapping symbol to its contract info
        """
        contracts = await self.get_contracts()
        result = {}
        for contract in contracts:
            symbol = contract.get("symbol", "")
            if symbol.endswith("-USDT"):
                result[symbol] = contract
        return result

    async def set_margin_type(self, symbol: str, margin_type: str = "CROSS") -> bool:
        """
        Set margin type for a symbol.
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            margin_type: "CROSS" or "ISOLATED"
            
        Returns:
            True if successful
        """
        params = {
            "symbol": symbol,
            "marginType": margin_type,
        }
        data = await self._request("/openApi/swap/v2/trade/marginType", "POST", params)
        return data.get("code") == 0

    async def get_margin_type(self, symbol: str) -> Optional[str]:
        """
        Get current margin type for a symbol.
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            
        Returns:
            Margin type string or None if not found
        """
        try:
            positions = await self.get_positions()
            for pos in positions:
                if pos.get("symbol") == symbol:
                    return pos.get("marginType")
        except Exception as e:
            print(f"Error getting margin type: {e}")
        return None

    async def set_position_mode(self, position_mode: str = "HEDGE") -> bool:
        """
        Set position mode (Hedge Mode or One-way Mode).
        
        Args:
            position_mode: "HEDGE" or "ONE_WAY"
            
        Returns:
            True if successful
        """
        params = {
            "dualSidePosition": "true" if position_mode == "HEDGE" else "false"
        }
        data = await self._request("/openApi/swap/v2/trade/positionSide", "POST", params)
        return data.get("code") == 0

    async def get_position_mode(self) -> Optional[str]:
        """
        Get current position mode.
        
        Returns:
            "HEDGE" or "ONE_WAY" or None if not found
        """
        try:
            account = await self.get_account_info()
            dual_side = account.get("dualSidePosition", "false")
            return "HEDGE" if dual_side == "true" else "ONE_WAY"
        except Exception as e:
            print(f"Error getting position mode: {e}")
            return None

    async def set_leverage(self, symbol: str, leverage: int, side: str = "LONG") -> bool:
        """
        Set leverage for a symbol with cross margin mode.
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            leverage: Leverage value (e.g., 20)
            side: "LONG" or "SHORT" (required for Hedge Mode)
            
        Returns:
            True if successful
        """
        params = {
            "symbol": symbol,
            "leverage": leverage,
            "side": side,
        }
        data = await self._request("/openApi/swap/v2/trade/leverage", "POST", params)
        return data.get("code") == 0

    async def get_leverage(self, symbol: str, side: str = "LONG") -> Optional[int]:
        """
        Get current leverage for a symbol.
        
        Args:
            symbol: Trading pair
            side: "LONG" or "SHORT"
            
        Returns:
            Leverage value or None
        """
        try:
            positions = await self.get_positions()
            for pos in positions:
                if pos.get("symbol") == symbol and pos.get("positionSide") == side:
                    return int(pos.get("leverage", 0))
        except Exception as e:
            print(f"Error getting leverage: {e}")
        return None

    # ==================== SYMBOL SPECIFICATIONS ====================

    async def refresh_symbol_specs(self) -> Dict[str, Dict[str, Any]]:
        """
        Refresh and return all symbol specifications.
        
        Returns:
            Dictionary mapping symbol to its specifications
        """
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

    # ==================== ORDER PLACEMENT METHODS ====================

    async def place_order_with_tp(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        position_side: str,  # "LONG" or "SHORT"
        quantity: float,
        tp_price: float,
        leverage: int = 20,
        price_precision: int = 2,
    ) -> Dict[str, Any]:
        """
        Place a market order with take profit price.
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            side: "BUY" for LONG, "SELL" for SHORT
            position_side: "LONG" or "SHORT"
            quantity: Order quantity in base currency
            tp_price: Take profit price (calculated from actual entry price)
            leverage: Leverage to set (default 20x)
            price_precision: Price decimal precision for rounding
            
        Returns:
            Order result dictionary
        """
        # Round TP price to pricePrecision
        tp_price_rounded = round(tp_price, price_precision)
        
        params = {
            "symbol": symbol,
            "side": side,
            "positionSide": position_side,
            "type": "MARKET",
            "quantity": f"{quantity:.8f}".rstrip('0').rstrip('.'),
            "tpPrice": str(tp_price_rounded),
        }
        
        data = await self._request("/openApi/swap/v2/trade/order", "POST", params)
        return data

    async def place_tp_order(
        self,
        symbol: str,
        side: str,  # "BUY" to close SHORT, "SELL" to close LONG
        position_side: str,  # "LONG" or "SHORT"
        quantity: float,
        tp_price: float,
        price_precision: int = 2,
    ) -> Dict[str, Any]:
        """
        Place a separate take profit order (TAKE_PROFIT_MARKET).
        
        Args:
            symbol: Trading pair (e.g., BTC-USDT)
            side: "BUY" to close SHORT, "SELL" to close LONG
            position_side: "LONG" or "SHORT"
            quantity: Order quantity in base currency
            tp_price: Take profit price
            price_precision: Price decimal precision for rounding
            
        Returns:
            Order result dictionary
        """
        tp_price_rounded = round(tp_price, price_precision)
        
        params = {
            "symbol": symbol,
            "side": side,
            "positionSide": position_side,
            "type": "TAKE_PROFIT_MARKET",
            "quantity": f"{quantity:.8f}".rstrip('0').rstrip('.'),
            "stopPrice": str(tp_price_rounded),
            "reduceOnly": "true",
        }
        
        data = await self._request("/openApi/swap/v2/trade/order", "POST", params)
        return data

    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status by order ID.
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order status information
        """
        params = {
            "symbol": symbol,
            "orderId": order_id,
        }
        data = await self._request("/openApi/swap/v2/trade/order", "GET", params)
        return data

    async def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position info for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Position info or None if no position
        """
        positions = await self.get_positions()
        for pos in positions:
            if pos.get("symbol") == symbol:
                return pos
        return None

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        try:
            data = await self._request("/openApi/swap/v2/user/positions", "GET")
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get open orders for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            List of open orders
        """
        try:
            data = await self._request("/openApi/swap/v2/trade/openOrders", "GET", {"symbol": symbol})
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return data.get("data", {}).get("orders", [])
            return []
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return []

    # ==================== HELPER METHODS ====================

    @staticmethod
    def round_to_step(value: float, step: float) -> float:
        """Round value to nearest step."""
        if step <= 0:
            return value
        return math.floor(value / step) * step

    @staticmethod
    def round_up_to_step(value: float, step: float) -> float:
        """Round value up to nearest step."""
        if step <= 0:
            return value
        return math.ceil(value / step) * step

    @staticmethod
    def round_to_precision(value: float, precision: int) -> float:
        """Round value to specified decimal precision."""
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
        """
        Calculate order quantity for target notional value.
        
        Args:
            notional_usdt: Target notional in USDT (e.g., 200 for 10 USDT margin at 20x)
            entry_price: Current price for quantity calculation
            qty_step: Minimum quantity step from symbol specs
            min_qty: Minimum order quantity
            min_notional: Minimum notional value
            leverage: Leverage multiplier
            
        Returns:
            Tuple of (quantity, error_message) - error_message is empty if successful
        """
        if entry_price <= 0:
            return 0.0, "Invalid entry price"
        
        # Calculate raw quantity
        raw_qty = notional_usdt / entry_price
        
        # Round to qtyStep
        qty = BingXFetcher.round_up_to_step(raw_qty, qty_step)
        
        # Check minimum quantity
        if qty < min_qty:
            return 0.0, f"Quantity {qty} below minQty {min_qty}"
        
        # Check minimum notional
        notional = qty * entry_price
        if notional < min_notional:
            return 0.0, f"Notional {notional} below minNotional {min_notional}"
        
        return qty, ""

    @staticmethod
    def calculate_tp_price(entry_price: float, position_side: str, tp_pct: float = 5.0) -> float:
        """
        Calculate take profit price based on entry price and position side.
        
        Args:
            entry_price: Actual entry price from filled order
            position_side: "LONG" or "SHORT"
            tp_pct: Take profit percentage (default 5%)
            
        Returns:
            Take profit price
        """
        if position_side == "LONG":
            return entry_price * (1 + tp_pct / 100)
        else:  # SHORT
            return entry_price * (1 - tp_pct / 100)