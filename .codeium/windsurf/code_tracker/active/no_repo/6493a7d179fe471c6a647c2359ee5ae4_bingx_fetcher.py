õ@"""
BingX API Fetcher for EVRECONSE

Handles authentication, kline data fetching, and symbol listing for BingX perpetual futures.
"""
import asyncio
import aiohttp
import hashlib
import hmac
import time
from datetime import UTC, datetime
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
        # Try to load from .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        
        self.api_key = api_key or os.environ.get("EVRECONSE_EXCHANGE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("EVRECONSE_EXCHANGE_API_SECRET", "")
        
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
            
            if start_time:
                params["startTime"] = start_time
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
• *cascade08•⁄ *cascade08⁄Ï*cascade08ÏÑ *cascade08Ñò *cascade08òè*cascade08èÕ *cascade08ÕŒ *cascade08Œ Ω% *cascade08Ω%’%*cascade08’%°' *cascade08°'≠'*cascade08≠'Õ( *cascade08Õ(◊(*cascade08◊(⁄( *cascade08⁄(ﬂ(*cascade08ﬂ(·( *cascade08·(‚(*cascade08‚(Ê( *cascade08Ê(Ï(*cascade08Ï(Ó( *cascade08Ó(Ô(*cascade08Ô(Û( *cascade08Û(˘(*cascade08˘(˚( *cascade08˚(¸(*cascade08¸(ˇ( *cascade08ˇ(Ö)*cascade08Ö)á) *cascade08á)à)*cascade08à)ç) *cascade08ç)ì)*cascade08ì)ï) *cascade08ï)ñ)*cascade08ñ)ú) *cascade08ú)û)*cascade08û)†) *cascade08†)£)*cascade08£)∏) *cascade08∏)ÿ) *cascade08ÿ)€)*cascade08€)ﬁ) *cascade08ﬁ)·)*cascade08·)¬* *cascade08¬*Õ* *cascade08Õ*—**cascade08—*Ô* *cascade08Ô*Û**cascade08Û*°+ *cascade08°+•+*cascade08•+≤+ *cascade08≤+√+*cascade08√+»+ *cascade08»+◊+*cascade08◊+ÿ+ *cascade08ÿ+Á+*cascade08Á+È+ *cascade08È+Í+*cascade08Í+Ú+ *cascade08Ú+ı+*cascade08ı+ˇ+ *cascade08ˇ+É,*cascade08É,Ñ, *cascade08Ñ,Ö,*cascade08Ö,ç, *cascade08ç,ê,*cascade08ê,ì, *cascade08ì,ò, *cascade08ò,ù,*cascade08ù,´, *cascade08´,Ø,*cascade08Ø,≈, *cascade08≈, , *cascade08 ,œ,*cascade08œ,ÿ, *cascade08ÿ,‹,*cascade08‹,ﬂ, *cascade08ﬂ,„,*cascade08„,Ê, *cascade08Ê,Á,*cascade08Á,Ë, *cascade08Ë,Í,*cascade08Í,Ï, *cascade08Ï,,*cascade08,ê- *cascade08ê-î-*cascade08î-ñ- *cascade08ñ-ó-*cascade08ó-ô- *cascade08ô-õ-*cascade08õ-§- *cascade08§-®-*cascade08®-©- *cascade08©-≠-*cascade08≠-à. *cascade08à.å.*cascade08å.ç. *cascade08ç.ë.*cascade08ë.õ. *cascade08õ.à/*cascade08à/ë/ *cascade08ë/ï/*cascade08ï/Æ/ *cascade08Æ/∑/*cascade08∑/≈/ *cascade08≈/…/ *cascade08…/“0*cascade08“0Ë0 *cascade08Ë0Ò0*cascade08Ò0™1 *cascade08™1¨1 *cascade08¨1∞1*cascade08∞1±1 *cascade08±1ı1*cascade08ı1ˆ1 *cascade08ˆ1ê2*cascade08ê2ë2 *cascade08ë2ø2 *cascade08ø2¬2*cascade08¬2Ã2 *cascade08Ã2Õ2 *cascade08Õ2–2*cascade08–2—2 *cascade08—2ﬁ2 *cascade08ﬁ2·2*cascade08·2Á2 *cascade08Á2Ë2 *cascade08Ë2Ú2 *cascade08Ú2Û2*cascade08Û2á3 *cascade08á3â3 *cascade08â3ã3*cascade08ã3å3 *cascade08å3ç3*cascade08ç3è3 *cascade08è3ë3*cascade08ë3í3 *cascade08í3ì3*cascade08ì3ò3 *cascade08ò3ù3*cascade08ù3û3 *cascade08û3ü3*cascade08ü3†3 *cascade08†3¢3*cascade08¢3£3 *cascade08£3®3*cascade08®3™3 *cascade08™3´3*cascade08´3¨3 *cascade08¨3≤3*cascade08≤3≥3 *cascade08≥3∑3*cascade08∑3∏3 *cascade08∏3ø3*cascade08ø3¿3 *cascade08¿3¡3*cascade08¡3“3 *cascade08“3’3*cascade08’3‰3 *cascade08‰3Â3*cascade08Â3Ö4 *cascade08Ö4à4*cascade08à4¨4 *cascade08¨4Ø4*cascade08Ø4∞4*cascade08∞4±4 *cascade08±4Ω4 *cascade08Ω4¿4*cascade08¿4¡4*cascade08¡4¬4 *cascade08¬4Ç5 *cascade08Ç5Ö5*cascade08Ö5ì5 *cascade08ì5ñ5*cascade08ñ5ù5 *cascade08ù5°5 *cascade08°5¢5 *cascade08¢5®5*cascade08®5∞5 *cascade08∞5µ5*cascade08µ5∑5 *cascade08∑5∏5*cascade08∏5π5 *cascade08π5∫5 *cascade08∫5Ω5*cascade08Ω5¿5 *cascade08¿5√5*cascade08√5À5 *cascade08À5Ã5*cascade08Ã5â6 *cascade08â6é6*cascade08é6ß6 *cascade08ß6¨6*cascade08¨6∑6 *cascade08∑6π6 *cascade08π6ª6*cascade08ª6º6 *cascade08º6æ6 *cascade08æ6≈6*cascade08≈6Ó6 *cascade08Ó6Ô6 *cascade08Ô6ç8*cascade08ç8é8 *cascade08é8î8*cascade08î8ï8 *cascade08ï8˙8*cascade08˙8õ@ *cascade082Yfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/exchange/bingx_fetcher.py