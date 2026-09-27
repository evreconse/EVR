"""
BingX API Fetcher for EVRECONSE

Handles authentication, kline data fetching, and symbol listing for BingX perpetual futures.
"""
import asyncio
import aiohttp
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
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
