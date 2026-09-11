"""
BingX Mapping Module

Deterministic mapping from CMC assets to BingX USDT Perpetual contracts.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from typing import Literal
import logging

logger = logging.getLogger(__name__)


class MappingState(str, Enum):
    """Mapping result states."""
    EXACT_MATCH = "EXACT_MATCH"
    BASE_ASSET_MATCH = "BASE_ASSET_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"
    FILTERED_STABLECOIN = "FILTERED_STABLECOIN"
    FILTERED_WRAPPED = "FILTERED_WRAPPED"
    FILTERED_LEVERAGED = "FILTERED_LEVERAGED"
    BINGX_MISSING = "BINGX_MISSING"
    BINGX_DELISTED = "BINGX_DELISTED"
    BINGX_SETTLING = "BINGX_SETTLING"


@dataclass
class MappingResult:
    """Result of mapping a CMC asset to BingX contract."""
    cmc_symbol: str
    cmc_rank: int
    bingx_symbol: Optional[str]
    state: str
    reason: str
    bingx_status: Optional[str] = None
    bingx_base_asset: Optional[str] = None
    bingx_quote_asset: Optional[str] = None
    
    @property
    def is_mapped(self) -> bool:
        """Whether this asset has a valid mapping for trading."""
        return self.state in ("EXACT_MATCH", "BASE_ASSET_MATCH")
    
    @property
    def is_excluded(self) -> bool:
        """Whether this asset was filtered out."""
        return self.state in (
            "FILTERED_STABLECOIN", "FILTERED_WRAPPED", "FILTERED_LEVERAGED",
            "BINGX_MISSING", "BINGX_DELISTED", "BINGX_SETTLING",
            "AMBIGUOUS", "NO_MATCH"
        )


class BingXContract:
    """BingX USDT Perpetual contract info."""
    
    def __init__(
        self,
        symbol: str,
        base_asset: str,
        quote_asset: str,
        status: str,
        **kwargs
    ):
        self.symbol = symbol
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.status = status  # Trading, Settling, Delisted
        
    @property
    def is_trading(self) -> bool:
        return self.status in (1, "Trading", True, "true", "1")
    
    @property
    def is_usdt_perpetual(self) -> bool:
        return self.symbol.endswith("-USDT") and self.status == "Trading"
    
    @property
    def base_asset_upper(self) -> str:
        return self.symbol.split("-")[0] if "-" in self.symbol else ""


class BingXContractRegistry:
    """Registry of BingX USDT Perpetual contracts."""
    
    def __init__(self):
        self._contracts: Dict[str, BingXContract] = {}  # symbol -> contract
        self._by_base_asset: Dict[str, List[str]] = {}  # base_asset -> [symbols]
    
    def load_from_api(self, contracts: List[Dict[str, Any]]) -> int:
        """Load contracts from BingX API response."""
        self._contracts.clear()
        self._by_base_asset.clear()
        
        count = 0
        for c in contracts:
            symbol = c.get("symbol", "")
            if not symbol.endswith("-USDT"):
                continue
            
            status = c.get("status", "")
            # API returns 1 for trading, "Trading" for string
            if status not in (1, "Trading", True, "true"):
                continue
            
            base_asset = c.get("baseAsset", c.get("asset", ""))
            if not base_asset:
                continue
            
            contract = BingXContract(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=c.get("quoteAsset", "USDT"),
                status=status
            )
            
            self._contracts[symbol] = contract
            
            if base_asset not in self._by_base_asset:
                self._by_base_asset[base_asset] = []
            self._by_base_asset[base_asset].append(symbol)
            
            count += 1
        
        return count
    
    def get_contract(self, symbol: str) -> Optional[BingXContract]:
        """Get contract by exact symbol."""
        return self._contracts.get(symbol)
    
    def get_by_base_asset(self, base_asset: str) -> List[BingXContract]:
        """Get all contracts with given base asset."""
        symbols = self._by_base_asset.get(base_asset, [])
        return [self._contracts[s] for s in self._by_base_asset.get(base_asset, [])]
    
    def get_trading_contracts(self) -> List[str]:
        """Get all trading contract symbols."""
        return [s for s, c in self._contracts.items() if c.is_trading]
    
    @property
    def active_count(self) -> int:
        return sum(1 for c in self._contracts.values() if c.is_trading)


class BingXMapper:
    """
    Deterministic mapping from CMC assets to BingX contracts.
    
    Priority order:
    1. EXACT_MATCH: CMC symbol + "-USDT" == BingX symbol
    2. BASE_ASSET_MATCH: CMC symbol == BingX baseAsset (exactly one match)
    3. AMBIGUOUS: Multiple BingX contracts match
    4. NO_MATCH: No match found
    """
    
    def __init__(self, contract_registry: BingXContractRegistry):
        self.registry = contract_registry
        
        # Stablecoins to exclude
        self.STABLECOINS = frozenset({
            "USDT", "USDC", "USDD", "USDE", "USDe", "USDe", "USDs",
            "DAI", "FDUSD", "PYUSD", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "FDUSD", "PYUSD", "USDX", "USDK", "USDN", "USDS",
            "USDT0", "USDT1", "USDT2", "USDT3", "USDT4", "USDT5",
            "USDT6", "USDT7", "USDT7", "USDT8", "USDT9",
            "DAI", "FDUSD", "PYUSD", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "UST", "USDD", "USDE", "USDP", "GUSD", "LUSD", "sUSD",
            "FRAX", "LUSD", "sUSD", "MIM", "FEI", "RAI", "OHM",
            "BUSD", "HUSD", "TUSD", "USDK", "USDN", "USDS",
            "USDT0", "USDT1", "USDT2", "USDT3", "USDT4", "USDT5",
            "USDT6", "USDT7", "USDT7", "USDT8", "USDT9",
            "USDT0", "USDT1", "USDT2", "USDT3", "USDT4", "USDT5",
            "USDT6", "USDT7", "USDT7", "USDT8", "USDT9",
        })
        
        # Wrapped tokens
        self.WRAPPED_PREFIXES = frozenset([
            "w", "w.", "w_"
        ])
        self.WRAPPED_SUFFIXES = frozenset([
            "w", ".w", "-w", "W", ".W"
        ])
        
        # Leveraged tokens patterns
        self.LEVERAGED_PATTERNS = frozenset([
            "3L", "3S", "2L", "2S", "1L", "1S",
            "UP", "DOWN", "BULL", "BEAR",
            "5L", "5S", "3XL", "3XS", "2XL", "2XS",
            "3L", "3S", "2L", "2S", "1L", "1S",
        ])
    
    def _is_stablecoin(self, symbol: str, cmc_data: dict = None) -> bool:
        """Check if symbol is a stablecoin."""
        base = symbol.replace("-USDT", "").upper()
        
        if base in self.STABLECOINS:
            return True
        
        # Check CMC tags/category if available
        if cmc_data:
            category = cmc_data.get("category", "").lower()
            tags = cmc_data.get("tags", [])
            if any(t in str(tags).lower() for t in ["stablecoin", "stable"]):
                return True
            if "stablecoin" in category.lower():
                return True
        
        return False
    
    def _is_wrapped(self, symbol: str, cmc_data: dict = None) -> bool:
        """Check if token is wrapped."""
        base = symbol.replace("-USDT", "").upper()
        
        # Check prefixes
        for prefix in self.WRAPPED_PREFIXES:
            if base.startswith(prefix):
                return True
        
        # Check suffixes
        for suffix in self.WRAPPED_SUFFIXES:
            if base.endswith(suffix):
                return True
        
        # Check CMC tags
        if cmc_data:
            tags = cmc_data.get("tags", [])
            if any("wrapped" in str(t).lower() for t in tags):
                return True
        
        return False
    
    def _is_leveraged(self, symbol: str, cmc_data: dict = None) -> bool:
        """Check if token is leveraged."""
        base = symbol.replace("-USDT", "").upper()
        
        for pattern in self.LEVERAGED_PATTERNS:
            if pattern in base:
                return True
        
        # Check CMC tags
        if cmc_data:
            tags = cmc_data.get("tags", [])
            if any("leveraged" in str(t).lower() for t in tags):
                return True
        
        return False
    
    def classify_asset(self, cmc_asset: Dict) -> tuple[str, Optional[str]]:
        """
        Classify CMC asset for filtering.
        
        Returns:
            (filter_type, reason) if filtered, (None, None) if OK
        """
        symbol = cmc_asset.get("symbol", "").upper()
        cmc_symbol = cmc_asset.get("symbol", "")
        
        # Check stablecoin
        if self._is_stablecoin(cmc_asset.get("symbol", ""), cmc_asset):
            return "FILTERED_STABLECOIN", f"Stablecoin: {symbol}"
        
        # Check wrapped
        if self._is_wrapped(cmc_symbol, cmc_asset):
            return "FILTERED_WRAPPED", f"Wrapped token: {symbol}"
        
        # Check leveraged
        if self._is_leveraged(cmc_asset.get("symbol", ""), cmc_asset):
            return "FILTERED_LEVERAGED", f"Leveraged token: {symbol}"
        
        return None, None
    
    def map_asset(self, cmc_asset: Dict) -> MappingResult:
        """
        Map a CMC asset to BingX contract.
        
        Returns MappingResult with state and details.
        """
        cmc_symbol = cmc_asset.get("symbol", "").upper()
        cmc_rank = cmc_asset.get("cmc_rank", 0)
        cmc_name = cmc_asset.get("name", "")
        cmc_slug = cmc_asset.get("slug", "")
        
        # Check filters first
        filter_type, reason = self.classify_asset(cmc_asset)
        if filter_type:
            return MappingResult(
                cmc_symbol=cmc_symbol,
                cmc_rank=cmc_rank,
                bingx_symbol=None,
                state=filter_type,
                reason=reason
            )
        
        bingx_symbol = f"{cmc_asset['symbol']}-USDT"
        
        # 1. EXACT_MATCH
        contract = self.registry.get_contract(f"{cmc_asset['symbol']}-USDT")
        if contract and contract.is_trading:
            return MappingResult(
                cmc_symbol=cmc_symbol,
                cmc_rank=cmc_rank,
                bingx_symbol=contract.symbol,
                state="EXACT_MATCH",
                reason=f"Exact symbol match: {contract.symbol}",
                bingx_status=contract.status,
                bingx_base_asset=contract.base_asset,
                bingx_quote_asset=contract.quote_asset
            )
        
        # 2. BASE_ASSET_MATCH - exactly one match
        base_asset = cmc_asset["symbol"]
        matches = self.registry.get_by_base_asset(base_asset)
        trading_matches = [m for m in matches if m.is_trading]
        
        if len(trading_matches) == 1:
            contract = trading_matches[0]
            return MappingResult(
                cmc_symbol=cmc_symbol,
                cmc_rank=cmc_rank,
                bingx_symbol=contract.symbol,
                state="BASE_ASSET_MATCH",
                reason=f"Base asset match: {base_asset} -> {contract.symbol}",
                bingx_status=contract.status,
                bingx_base_asset=contract.base_asset,
                bingx_quote_asset=contract.quote_asset
            )
        elif len(trading_matches) > 1:
            symbols = [m.symbol for m in trading_matches]
            return MappingResult(
                cmc_symbol=cmc_symbol,
                cmc_rank=cmc_rank,
                bingx_symbol=None,
                state="AMBIGUOUS",
                reason=f"Multiple matches: {symbols}",
                bingx_status="AMBIGUOUS"
            )
        
        # No match
        return MappingResult(
            cmc_symbol=cmc_symbol,
            cmc_rank=cmc_rank,
            bingx_symbol=None,
            state="NO_MATCH",
            reason=f"No BingX contract found for {cmc_symbol}",
            bingx_status=None
        )
    
    def process_universe(
        self,
        cmc_assets: List[Dict],
        bingx_contracts: List[Dict]
    ) -> Tuple[List[Dict], Dict]:
        """
        Process full CMC universe through mapping pipeline.
        
        Returns:
            (final_universe, stats_dict)
        """
        # Load BingX contracts
        self.registry.load_from_api(bingx_contracts)
        
        results = []
        stats = {
            "total_cmc": len(cmc_assets),
            "target_count": 0,
            "filtered_stablecoin": 0,
            "filtered_wrapped": 0,
            "filtered_leveraged": 0,
            "eligible_for_mapping": 0,
            "exact_matches": 0,
            "base_asset_matches": 0,
            "ambiguous": 0,
            "no_match": 0,
            "final_count": 0,
            "bingx_active_contracts": 0
        }
        
        for asset in cmc_assets:
            rank = asset.get("cmc_rank", 0)
            if not (20 <= asset.get("cmc_rank", 0) <= 250):
                continue
            
            stats["target_count"] += 1
            
            # Apply technical filters
            filter_type, reason = self.classify_asset(asset)
            if filter_type:
                stats[f"filtered_{filter_type.lower().replace('filtered_', '').replace('_', '_')}"] += 1
                continue
            
            stats["eligible_for_mapping"] += 1
            result = self.map_asset(asset)
            
            # Count mapping results
            if result.state == "EXACT_MATCH":
                stats["exact_matches"] += 1
            elif result.state == "BASE_ASSET_MATCH":
                stats["base_asset_matches"] += 1
            elif result.state == "AMBIGUOUS":
                stats["ambiguous"] += 1
            elif result.state == "NO_MATCH":
                stats["no_match"] += 1
            
            if result.is_mapped:
                stats["final_count"] += 1
            
            # Add BingX info to asset
            asset["bingx_symbol"] = result.bingx_symbol
            asset["mapping_state"] = result.state
            asset["excluded_reason"] = result.reason
            asset["bingx_status"] = result.bingx_status
            asset["bingx_base_asset"] = result.bingx_base_asset
            asset["bingx_quote_asset"] = result.bingx_quote_asset
        
        stats["bingx_active_contracts"] = self.registry.active_count
        
        # Build final universe
        final_universe = [
            a for a in cmc_assets
            if a.get("mapping_state") in ("EXACT_MATCH", "BASE_ASSET_MATCH")
        ]
        
        return final_universe, stats


def map_cmc_to_bingx(
    cmc_assets: List[Dict],
    bingx_contracts: List[Dict]
) -> Tuple[List[Dict], Dict]:
    """
    High-level function to map CMC assets to BingX contracts.
    
    Returns:
        (final_universe, stats)
    """
    registry = BingXContractRegistry()
    mapper = BingXMapper(registry)
    return mapper.process_universe(cmc_assets, bingx_contracts)


if __name__ == "__main__":
    # Test mapping logic
    import json
    
    # Sample test
    sample_cmc = [
        {"symbol": "BTC", "cmc_rank": 1, "name": "Bitcoin", "slug": "bitcoin"},
        {"symbol": "ETH", "cmc_rank": 2, "name": "Ethereum", "slug": "ethereum"},
        {"symbol": "USDT", "cmc_rank": 3, "name": "Tether", "slug": "tether"},
        {"symbol": "BTC", "cmc_rank": 1, "name": "Bitcoin", "slug": "bitcoin"},  # duplicate
        {"symbol": "DOGE", "cmc_rank": 10, "name": "Dogecoin", "slug": "dogecoin"},
    ]
    
    sample_bingx = [
        {"symbol": "BTC-USDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "Trading"},
        {"symbol": "ETH-USDT", "baseAsset": "ETH", "quoteAsset": "USDT", "status": "Trading"},
        {"symbol": "DOGE-USDT", "baseAsset": "DOGE", "quoteAsset": "USDT", "status": "Trading"},
    ]
    
    result, stats = map_cmc_to_bingx(sample_cmc, sample_bingx)
    print(f"Stats: {stats}")
    for r in result:
        print(f"  {r['symbol']}: {r.get('mapping_state')} -> {r.get('bingx_symbol')}")