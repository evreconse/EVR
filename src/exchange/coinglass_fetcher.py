"""
CoinGlass API client for fetching liquidation data.

API Documentation: https://open-api-v4.coinglass.com/api/futures/liquidation/history
"""

import os
import aiohttp
from datetime import UTC, datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class CoinGlassFetcher:
    """Fetch liquidation data from CoinGlass API."""
    
    def __init__(self):
        self.api_key = os.getenv("EVRECONSE_COINGLASS_API_KEY")
        if not self.api_key:
            raise ValueError("EVRECONSE_COINGLASS_API_KEY not found in .env")
        
        self.base_url = "https://open-api-v4.coinglass.com/api/futures/liquidation/history"
    
    async def get_liquidation_history(
        self,
        symbol: str,
        exchange: str = "BingX",
        interval: str = "15m",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[dict]:
        """
        Fetch liquidation history from CoinGlass.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            exchange: Exchange name (default: "BingX")
            interval: Time interval (default: "15m")
            limit: Number of records to fetch (default: 100)
            start_time: Start timestamp in milliseconds (optional)
            end_time: End timestamp in milliseconds (optional)
        
        Returns:
            List of liquidation records with timestamps and liquidation amounts.
        """
        params = {
            "exchange": exchange,
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        headers = {
            "CG-API-KEY": self.api_key,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"CoinGlass API error: {response.status} - {error_text}")
                
                data = await response.json()
                
                if data.get("code") != 0:
                    raise Exception(f"CoinGlass API error: {data.get('msg', 'Unknown error')}")
                
                return data.get("data", [])
    
    async def get_liquidation_for_candle(
        self,
        symbol: str,
        candle_time_ms: int,
    ) -> Optional[dict]:
        """
        Get liquidation data for a specific M15 candle.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            candle_time_ms: Candle timestamp in milliseconds
        
        Returns:
            Dict with long_liquidation_usd and short_liquidation_usd, or None if not found.
        """
        # Fetch data around the candle time (±2 hours to be safe)
        start_time = candle_time_ms - (2 * 60 * 60 * 1000)  # 2 hours before
        end_time = candle_time_ms + (2 * 60 * 60 * 1000)  # 2 hours after
        
        records = await self.get_liquidation_history(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )
        
        # Find the record matching the candle timestamp
        for record in records:
            record_time = record.get("time")
            if record_time == candle_time_ms:
                return {
                    "long_liquidation_usd": record.get("longLiquidation", 0),
                    "short_liquidation_usd": record.get("shortLiquidation", 0),
                    "timestamp": record_time,
                }
        
        return None
