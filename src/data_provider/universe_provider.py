"""
BingX Universe Provider - Unified interface for dynamic universe.

This module provides the main interface for getting the current LW-001 universe.
Fetches ALL active USDT Perpetual contracts from BingX contracts API, applies technical filters.
No TOP-500 limit. Universe refreshes every 24 hours automatically.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.exchange.bingx_fetcher import BingXFetcher
from src.data_provider.cmc_universe_cache import CMCUniverseCache, get_universe_cache

logger = logging.getLogger(__name__)


@dataclass
class UniverseMetadata:
    """Metadata about the current universe."""
    total_bingx_contracts: int = 0
    total_usdt_perpetual: int = 0
    excluded_stablecoins: int = 0
    excluded_wrapped: int = 0
    excluded_leveraged: int = 0
    excluded_synthetic: int = 0
    excluded_non_trading: int = 0
    final_universe_count: int = 0
    last_refresh: Optional[str] = None
    cache_age_hours: float = 0.0
    validation_status: str = "UNKNOWN"


# Stablecoins to exclude
STABLECOINS = frozenset({
    "USDT", "USDC", "USDD", "USDE", "USDe", "USDs",
    "DAI", "FDUSD", "PYUSD", "USDP", "GUSD", "LUSD", "SUSD",
    "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "SUSD",
    "FRAX", "LUSD", "SUSD", "MIM", "FEI", "RAI", "OHM",
    "BUSD", "HUSD", "TUSD", "USDK", "USDN", "USDS",
    "USDX", "USDK", "USDN", "USDS",
    "USDT0", "USDT1", "USDT2", "USDT3", "USDT4", "USDT5",
    "USDT6", "USDT7", "USDT8", "USDT9",
})

# Wrapped tokens
WRAPPED_PREFIXES = frozenset(["w", "w.", "w_"])
WRAPPED_SUFFIXES = frozenset(["w", ".w", "-w", "W", ".W"])

# Leveraged tokens patterns
LEVERAGED_PATTERNS = frozenset([
    "3L", "3S", "2L", "2S", "1L", "1S",
    "UP", "DOWN", "BULL", "BEAR",
    "5L", "5S", "3XL", "3XS", "2XL", "2XS",
])

# Synthetic/tokenized assets (NCSK*, NCCO* prefixes)
SYNTHETIC_PREFIXES = frozenset([
    "NCSK", "NCCO", "NCSIN", "NCSISP", "NCSKNBIS", "NCSKGLW", "NCCO724",
    "NCSKSOXX", "NCSKBTDR", "NCSKAMC", "NCSKMSTR", "NCSKCOST", "NCSKARKK",
    "NCSKCAT", "NCSKLGELE", "NCSKOKTA", "NCSKSNPS", "NCSKTM", "NCSKHIMS",
    "NCSKAMKR", "NCSKGTLB", "NCSKPAYP", "NCSKMETA", "NCSKAMZN", "NCSKHOOD",
    "NCSKCOIN", "NCSKGOOGL", "NCSKNVDA", "NCSKGME", "NCSKAAPL", "NCSKPALLADIUM",
    "NCCO724COPPER", "NCSKNETFLIX", "NCSKANTHROPIC", "NCSKTSLA", "NCSKSOXL",
    "NCSKSPCX", "NCSKSNDK", "NCSKMRVL", "NCSKSPY", "NCSKVST", "NCSKJNJ",
    "NCSKOPENAI", "NCSKTSMU", "NCSKWMT", "NCSKAPLD", "NCSKOXY", "NCSKCRDO",
    "NCSKDELL", "NCSKXLF", "NCSKSTX", "NCSKBAC", "NCSKAMAT", "NCSKFLY",
    "NCSKCIFR", "NCSKRKLB", "NCSKAVAV", "NCSKINFQ", "NCSKGDX", "NCSKCOP",
    "NCSKKOPN", "NCSKQQQ", "NCSKBE", "NCSKLITE", "NCSKNVDL", "NCSKRDW",
    "NCSKQCOM", "NCSKIREN", "NCSKSKUU", "NCSKQNT", "NCSKPURR", "NCSKUSO",
    "NCSKXOM", "NCSKMU", "NCSKXLK", "NCSKJPM", "NCSKBITO", "NCSIEWJ",
    "NCSKAAL", "NCSKCLSK", "NCSKBUDUSDT", "NCSKCOHR", "NCSKTAIYOYUDEN",
    "NCSKRCAT", "NCSKRECRUIT", "NCSKMDB", "NCSKWDAY", "NCSKNVD2"
])


def is_stablecoin(base_symbol: str) -> bool:
    """Check if base symbol is a stablecoin."""
    return base_symbol.upper() in STABLECOINS


def is_wrapped(base_symbol: str) -> bool:
    """Check if token is wrapped."""
    base = base_symbol.upper()
    for prefix in WRAPPED_PREFIXES:
        if base.startswith(prefix):
            return True
    for suffix in WRAPPED_SUFFIXES:
        if base.endswith(suffix):
            return True
    return False


def is_leveraged(base_symbol: str) -> bool:
    """Check if token is leveraged."""
    base = base_symbol.upper()
    for pattern in LEVERAGED_PATTERNS:
        if pattern in base:
            return True
    return False


def is_synthetic(base_symbol: str) -> bool:
    """Check if token is synthetic/tokenized asset (NCSK*, NCCO* etc)."""
    base = base_symbol.upper()
    for prefix in SYNTHETIC_PREFIXES:
        if base.startswith(prefix):
            return True
    return False


class UniverseProvider:
    """
    Unified provider for LW-001 trading universe.
    
    Handles the pipeline:
    BingX contracts API -> filter USDT perpetual -> filter Trading status -> technical filters -> universe
    
    NO TOP-500 LIMIT. ALL active suitable contracts are included.
    Universe refreshes every 24 hours automatically.
    """
    
    def __init__(
        self,
        bingx_api_key: str = None,
        bingx_api_secret: str = None,
        cache_db_path: str = "/home/evreconse/data/cmc_universe.db",
        fallback_file: str = "/home/evreconse/last_good_universe.json",
        refresh_interval_hours: int = 24,
    ):
        self._bingx_fetcher = BingXFetcher()
        self._cache = CMCUniverseCache()
        self._universe: List[Dict[str, Any]] = []
        self._metadata: Dict = {}
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_interval_hours = refresh_interval_hours
        self._running = False
        
    async def initialize(self) -> None:
        """Initialize the universe provider and start automatic refresh task."""
        logger.info("Initializing BingX Universe Provider (ALL active USDT perpetuals)...")
        
        # Initialize cache
        cache = get_universe_cache()
        
        # Try to load existing cache
        meta = cache.get_active_snapshot_meta()
        if meta:
            logger.info(f"Loaded cached universe: {meta['final_count']} symbols, age: {meta.get('age_hours', 0):.1f}h")
        else:
            logger.info("No cached universe found, will build on first refresh")
        
        # Start automatic refresh task (every 24 hours)
        self._running = True
        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())
        logger.info(f"Automatic universe refresh started (interval: {self._refresh_interval_hours}h)")
    
    async def _auto_refresh_loop(self) -> None:
        """Background task to refresh universe every 24 hours."""
        while self._running:
            try:
                await asyncio.sleep(self._refresh_interval_hours * 3600)
                if not self._running:
                    break
                logger.info("Scheduled universe refresh triggered")
                await self.refresh()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-refresh error: {e}")
                await asyncio.sleep(300)  # Wait 5 min before retry
    
    async def shutdown(self) -> None:
        """Stop the automatic refresh task."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("Universe provider shutdown complete")
    
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
        
        # Map DB fields to meaningful names
        metadata = {
            "total_bingx_contracts": meta.get("bingx_active_contracts", 0),
            "total_usdt_perpetual": meta.get("target_count", 0),
            "excluded_stablecoins": meta.get("filtered_stablecoin", 0),
            "excluded_wrapped": meta.get("filtered_wrapped", 0),
            "excluded_leveraged": meta.get("filtered_leveraged", 0),
            "excluded_synthetic": meta.get("filtered_synthetic", 0) if "filtered_synthetic" in meta else (
                meta.get("filtered_count", 0) - meta.get("filtered_stablecoin", 0) - meta.get("filtered_wrapped", 0) - meta.get("filtered_leveraged", 0)
            ),
            "excluded_non_trading": meta.get("excluded_non_trading", 0),
            "final_universe_count": meta.get("final_count", 0),
            "last_refresh": meta.get("fetched_at"),
            "cache_age_hours": self._get_cache_age_hours(),
            "validation_status": meta.get("validation_status", "UNKNOWN"),
        }
        
        symbols = [u["bingx_symbol"] for u in universe]
        return symbols, metadata
    
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
        Refresh the universe from BingX contracts API.
        
        Fetches ALL contracts, filters for active USDT perpetuals,
        applies technical filters. NO TOP-N LIMIT.
        
        Args:
            force: Force refresh even if cache is fresh
            
        Returns:
            True if refresh succeeded and universe was updated
        """
        logger.info("Starting universe refresh from BingX contracts API...")
        
        try:
            # 1. Fetch ALL BingX contracts
            logger.info("Fetching BingX contracts...")
            contracts = await self._bingx_fetcher.get_contracts()
            
            logger.info(f"Total contracts received: {len(contracts)}")
            
            # 2. Filter USDT perpetual contracts
            usdt_contracts = [c for c in contracts if c.get("symbol", "").endswith("-USDT")]
            logger.info(f"USDT perpetual contracts: {len(usdt_contracts)}")
            
            # 3. Filter Trading status only
            trading_contracts = [c for c in usdt_contracts if c.get("status") in (1, "Trading", True, "true")]
            logger.info(f"Trading USDT perpetual contracts: {len(trading_contracts)}")
            
            # 4. Apply technical filters (NO volume sorting, NO top-N limit)
            final_universe = []
            stats = {
                "total_bingx_contracts": len(contracts),
                "total_usdt_perpetual": len(usdt_contracts),
                "excluded_stablecoins": 0,
                "excluded_wrapped": 0,
                "excluded_leveraged": 0,
                "excluded_synthetic": 0,
                "excluded_non_trading": len(usdt_contracts) - len(trading_contracts),
                "final_count": 0,
            }
            
            for contract in trading_contracts:
                symbol = contract.get("symbol", "")
                base_symbol = contract.get("baseAsset", symbol.replace("-USDT", ""))
                
                # Apply filters
                if is_stablecoin(base_symbol):
                    stats["excluded_stablecoins"] += 1
                    continue
                
                if is_wrapped(base_symbol):
                    stats["excluded_wrapped"] += 1
                    continue
                
                if is_leveraged(base_symbol):
                    stats["excluded_leveraged"] += 1
                    continue
                
                if is_synthetic(base_symbol):
                    stats["excluded_synthetic"] += 1
                    continue
                
                # Passed all filters
                stats["final_count"] += 1
                final_universe.append({
                    "symbol": symbol,
                    "bingx_symbol": symbol,
                    "cmc_rank": 0,  # Not applicable
                    "name": base_symbol,
                    "base_asset": base_symbol,
                    "quote_asset": contract.get("quoteAsset", "USDT"),
                    "lastPrice": float(contract.get("lastPrice", 0)) if contract.get("lastPrice") else 0.0,
                })
            
            logger.info(f"Universe built: {len(final_universe)} symbols")
            logger.info(f"Stats: {stats}")
            logger.info(f"First 10 symbols: {[u['symbol'] for u in final_universe[:10]]}")
            logger.info(f"Last 10 symbols: {[u['symbol'] for u in final_universe[-10:]]}")
            
            # 5. Validate and activate - save to cache
            cache = get_universe_cache()
            snapshot_id = cache.save_snapshot(
                universe=final_universe,
                cmc_raw_count=0,
                target_count=stats["total_usdt_perpetual"],
                filtered_count=stats["excluded_stablecoins"] + stats["excluded_wrapped"] + stats["excluded_leveraged"] + stats["excluded_synthetic"],
                filtered_stablecoin=stats["excluded_stablecoins"],
                filtered_wrapped=stats["excluded_wrapped"],
                filtered_leveraged=stats["excluded_leveraged"],
                filtered_synthetic=stats["excluded_synthetic"],
                excluded_non_trading=stats["excluded_non_trading"],
                eligible_count=stats["total_usdt_perpetual"],
                exact_matches=0,
                base_asset_matches=0,
                ambiguous_count=0,
                no_match_count=0,
                final_count=len(final_universe),
                bingx_active_contracts=stats["total_bingx_contracts"],
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
        status["refresh_interval_hours"] = self._refresh_interval_hours
        status["auto_refresh_running"] = self._running
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