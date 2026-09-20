"""
CoinMarketCap API Fetcher for EVRECONSE

Fetches cryptocurrency rankings from CoinMarketCap API.
"""

import asyncio
import aiohttp
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class CMCAsset:
    """CoinMarketCap asset data."""
    cmc_id: int
    cmc_rank: int
    symbol: str
    name: str
    slug: str
    is_active: int
    platform: Optional[Dict[str, Any]] = None


class CoinMarketCapFetcher:
    """
    CoinMarketCap API client for fetching cryptocurrency rankings.
    
    Uses CoinMarketCap Pro API v1.
    API Documentation: https://coinmarketcap.com/api/documentation/v1/
    """
    
    BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    
    def __init__(self, api_key: str = None):
        """
        Initialize CoinMarketCap fetcher.
        
        Args:
            api_key: CMC Pro API key (from .env if not provided)
        """
        self.api_key = api_key or os.environ.get("EVRECONSE_CMC_API_KEY", "")
        
        if not self.api_key:
            raise ValueError(
                "CoinMarketCap API key not provided. "
                "Set EVRECONSE_CMC_API_KEY in .env file or environment variables."
            )
    
    async def fetch_rankings(
        self,
        start: int = 1,
        limit: int = 250,
        convert: str = "USD",
        sort: str = "market_cap"
    ) -> List[Dict[str, Any]]:
        """
        Fetch cryptocurrency rankings from CoinMarketCap API.
        
        Args:
            start: Starting rank (1-based)
            limit: Number of results (max 5000)
            convert: Currency to convert prices to
            sort: Sort field (market_cap, name, symbol, etc.)
            
        Returns:
            List of asset data dictionaries
        """
        if not self.api_key:
            raise ValueError("CoinMarketCap API key not configured")
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        
        headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json"
        }
        
        params = {
            "start": start,
            "limit": limit,
            "convert": convert,
            "sort": "market_cap"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"CMC API error: HTTP {resp.status}: {text}")
                
                data = await resp.json()
                
                if data.get("status", {}).get("error_code", 0) != 0:
                    error_msg = data.get("status", {}).get("error_message", "Unknown error")
                    raise Exception(f"CMC API error: {error_msg}")
                
                return data.get("data", [])
    
    async def fetch_target_universe(self) -> List[Dict[str, Any]]:
        """
        Fetch the target universe (CMC ranks 1-500 inclusive).
        
        Returns:
            List of 500 assets with ranks 1-500
        """
        # Fetch all 500 assets (ranks 1-500)
        all_assets = await self.fetch_rankings(start=1, limit=500)
        
        # Filter to ranks 1-500 inclusive (500 assets)
        target_assets = [
            asset for asset in all_assets
            if 1 <= asset.get("cmc_rank", 0) <= 500
        ]
        
        if len(target_assets) != 500:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Expected 500 assets in rank 1-500, got {len(target_assets)}. "
                "Proceeding with available assets."
            )
        
        return target_assets
    
    async def get_symbols(self) -> List[str]:
        """
        Get CMC symbols for target universe in BingX format.
        
        Returns:
            List of symbols in BASE-USDT format (e.g., "BTC-USDT")
        """
        assets = await self.fetch_target_universe()
        symbols = [f"{asset['symbol']}-USDT" for asset in all_assets]
        return symbols


if __name__ == "__main__":
    async def main():
        # Test the fetcher
        api_key = os.environ.get("EVRECONSE_CMC_API_KEY")
        if not api_key:
            print("Set EVRECONSE_CMC_API_KEY environment variable")
            return
        
        fetcher = CoinMarketCapFetcher()
        assets = await fetcher.fetch_target_universe()
        print(f"Fetched {len(assets)} assets (ranks 20-250)")
        for asset in assets[:5]:
            print(f"  {asset['cmc_rank']}: {asset['symbol']} - {asset['name']}")
    
    asyncio.run(main())