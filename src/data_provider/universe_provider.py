"""
CMC Universe Provider - Unified interface for dynamic universe.

This module provides the main interface for getting the current LW-001 universe.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.exchange.coinmarketcap_fetcher import CoinMarketCapFetcher
from src.data_provider.cmc_universe_cache import CMCUniverseCache, get_universe_cache
from src.data_provider.bingx_mapping import map_cmc_to_bingx, BingXContractRegistry
from src.exchange.bingx_fetcher import BingXFetcher

logger = logging.getLogger(__name__)


@dataclass
class UniverseMetadata:
    """Metadata about the current universe."""
    total_cmc: int = 0
    valid_cmc: int = 0
    excluded_stablecoins: int = 0
    excluded_wrapped: int = 0
    excluded_leveraged: int = 0
    bingx_active: int = 0
    exact_matches: int = 0
    base_asset_matches: int = 0
    ambiguous: int = 0
    no_match: int = 0
    final_universe_count: int = 0
    last_refresh: Optional[str] = None
    cache_age_hours: float = 0.0
    validation_status: str = "UNKNOWN"
    snapshot_age_hours: float = 0.0


class UniverseProvider:
    """
    Unified provider for LW-001 trading universe.
    
    Handles the complete pipeline:
    CMC fetch -> validation -> filtering -> BingX mapping -> validation -> universe
    """
    
    def __init__(
        self,
        cmc_api_key: str = None,
        bingx_api_key: str = None,
        bingx_api_secret: str = None,
        cmc_refresh_cron: str = "0 0 * * *",  # Daily at 00:00 UTC
        cache_db_path: str = "/home/evreconse/cmc_universe.db",
        fallback_file: str = "/home/evreconse/last_good_universe.json",
    ):
        self._cmc_fetcher = CoinMarketCapFetcher()
        self._bingx_fetcher = BingXFetcher()
        self._cache = CMCUniverseCache()
        self._universe: List[Dict[str, Any]] = []
        self._metadata: Dict = {}
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the universe provider."""
        logger.info("Initializing CMC Universe Provider...")
        
        # Initialize cache
        cache = get_universe_cache()
        
        # Try to load existing cache
        meta = cache.get_active_snapshot_meta()
        if meta:
            logger.info(f"Loaded cached universe: {meta['final_count']} symbols, age: {meta.get('age_hours', 0):.1f}h")
        else:
            logger.info("No cached universe found, will build on first refresh")
    
    async def get_universe(self) -> List[str]:
        """
        Get the current active universe symbols.
        
        Returns:
            List of BingX symbols (e.g., ["BTC-USDT", "ETH-USDT", ...])
        """
        cache = get_universe_cache()
        
        # Try to get from active cache
        universe = cache.get_active_universe()
        if universe:
            return [u["bingx_symbol"] for u in universe]
        
        # Try fallback
        fallback = cache.load_fallback()
        if fallback:
            logger.warning("Using fallback universe (cache miss)")
            return [u["bingx_symbol"] for u in fallback.get("universe", [])]
        
        # No universe available
        logger.warning("No universe available")
        return []
    
    async def get_universe_with_metadata(self) -> tuple[List[str], Dict[str, Any]]:
        """
        Get universe symbols with full metadata.
        
        Returns:
            (symbols_list, metadata_dict)
        """
        cache = get_universe_cache()
        meta = cache.get_active_snapshot_meta()
        
        if not meta:
            return [], {"error": "No universe available"}
        
        universe = cache.get_active_universe() or []
        symbols = [u["symbol"] for u in universe]
        
        metadata = {
            "total_cmc": meta.get("target_count", 0),
            "valid_cmc": meta.get("eligible_count", 0),
            "excluded_stablecoins": meta.get("filtered_stablecoin", 0),
            "excluded_wrapped": meta.get("filtered_wrapped", 0),
            "excluded_leveraged": meta.get("filtered_leveraged", 0),
            "bingx_active": meta.get("bingx_active_contracts", 0),
            "exact_matches": meta.get("exact_matches", 0),
            "base_asset_matches": meta.get("base_asset_matches", 0),
            "ambiguous": meta.get("ambiguous_count", 0),
            "no_match": meta.get("no_match_count", 0),
            "final_universe_count": meta.get("final_count", 0),
            "last_refresh": meta.get("fetched_at"),
            "cache_age_hours": self._get_cache_age_hours(),
            "validation_status": meta.get("validation_status", "UNKNOWN"),
        }
        
        return [u["symbol"] for u in json.loads(meta["universe_json"])], metadata
    
    def _get_cache_age_hours(self) -> float:
        """Get age of current snapshot in hours."""
        cache = get_universe_cache()
        meta = cache.get_active_snapshot_meta()
        if not meta or not meta.get("fetched_at"):
            return 0.0
        
        fetched_at = datetime.fromisoformat(meta["fetched_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        return age
    
    async def refresh(self, force: bool = False) -> bool:
        """
        Refresh the universe from CMC and BingX.
        
        Args:
            force: Force refresh even if cache is fresh
            
        Returns:
            True if refresh succeeded and universe was updated
        """
        logger.info("Starting universe refresh...")
        
        try:
            # 1. Fetch CMC rankings
            logger.info("Fetching CMC rankings...")
            cmc_fetcher = CoinMarketCapFetcher()
            cmc_assets = await cmc_fetcher.fetch_target_universe()  # 231 assets
            
            logger.info(f"CMC target assets: {len(cmc_assets)}")
            
            # 2. Get BingX contracts
            logger.info("Fetching BingX contracts...")
            bingx_fetcher = BingXFetcher()
            contracts = await bingx_fetcher.get_contracts()
            
            logger.info(f"BingX contracts: {len(contracts)}")
            
            # 3. Map and validate
            from src.data_provider.bingx_mapping import map_cmc_to_bingx
            
            final_universe, stats = map_cmc_to_bingx(
                cmc_assets, contracts
            )
            
            logger.info(f"Universe built: {len(final_universe)} symbols")
            logger.info(f"Stats: {stats}")
            
            # 4. Validate and activate - save to cache
            cache = get_universe_cache()
            snapshot_id = cache.save_snapshot(
                universe=final_universe,
                cmc_raw_count=len(cmc_assets),
                target_count=len(cmc_assets),
                filtered_count=stats.get("excluded_stablecoin", 0) + stats.get("excluded_wrapped", 0) + stats.get("excluded_leveraged", 0),
                eligible_count=stats.get("eligible", 0),
                exact_matches=stats.get("exact_match", 0),
                base_asset_matches=stats.get("base_asset_match", 0),
                ambiguous_count=stats.get("ambiguous", 0),
                no_match_count=stats.get("no_match", 0),
                final_count=len(final_universe),
                bingx_active_contracts=len(contracts),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                validation_status="ACCEPT",
                validation_errors=[]
            )
            
            # Activate the snapshot
            cache.activate_snapshot(snapshot_id)
            
            self._last_refresh = datetime.now(timezone.utc)
            logger.info(f"Universe saved to cache: {len(final_universe)} symbols")
            
            return True
            
        except Exception as e:
            logger.error(f"Universe refresh failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status."""
        cache = get_universe_cache()
        status = cache.get_status()
        status["last_refresh"] = self._last_refresh.isoformat() if self._last_refresh else None
        return status


# Global provider instance
_universe_provider: Optional[UniverseProvider] = None


def get_universe_provider() -> UniverseProvider:
    """Get global universe provider instance."""
    global _universe_provider
    if _universe_provider is None:
        _universe_provider = UniverseProvider()
    return _universe_provider


async def get_universe_symbols() -> List[str]:
    """Convenience function to get current universe symbols."""
    provider = get_universe_provider()
    return await provider.get_universe()


if __name__ == "__main__":
    async def main():
        provider = get_universe_provider()
        await provider.initialize()
        
        universe = await provider.get_universe()
        print(f"Universe: {len(universe)} symbols")
        print(universe[:10])
        
        symbols, meta = await provider.get_universe_with_metadata()
        print(f"\nMetadata: {meta}")
    
    asyncio.run(main())