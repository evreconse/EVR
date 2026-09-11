#!/usr/bin/env python3
"""
Dry-run script for CMC Universe.
Tests the full pipeline without sending Telegram messages.
"""

import asyncio
import sys
import os

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()


async def dry_run():
    """Run a dry-run of the CMC Universe pipeline."""
    print("="*80)
    print("CMC UNIVERSE DRY-RUN")
    print("="*80)
    print()
    
    # 1. Fetch CMC data
    print("\n[1/4] Fetching CMC rankings...")
    from src.exchange.coinmarketcap_fetcher import CoinMarketCapFetcher
    cmc_fetcher = CoinMarketCapFetcher()
    
    try:
        cmc_assets = await cmc_fetcher.fetch_target_universe()
        print(f"  CMC Target Universe: {len(cmc_assets)} assets (ranks 20-250)")
        print(f"  Sample: {[a['symbol'] for a in cmc_assets[:5]]}")
    except Exception as e:
        print(f"  ERROR fetching CMC: {e}")
        return False
    
    # 2. Fetch BingX contracts
    print("\n[2/4] Fetching BingX contracts...")
    from src.exchange.bingx_fetcher import BingXFetcher
    bingx_fetcher = BingXFetcher()
    contracts = await bingx_fetcher.get_contracts()
    print(f"  BingX contracts: {len(contracts)}")
    
    # Filter to USDT perpetual trading
    usdt_perpetual = [c for c in contracts if c.get('symbol', '').endswith('-USDT') and c.get('status') == 'Trading']
    print(f"  USDT Perpetual Trading: {len(usdt_perpetual)}")
    
    # 3. Run mapping pipeline
    print("\n[3/4] Running mapping pipeline...")
    from src.data_provider.bingx_mapping import map_cmc_to_bingx
    
    # Prepare CMC assets
    cmc_assets = await cmc_fetcher.fetch_target_universe()
    
    # Run mapping
    final_universe, stats = map_cmc_to_bingx(cmc_assets, contracts)
    
    print(f"\n{'='*60}")
    print("DRY-RUN RESULTS")
    print("="*60)
    print(f"CMC Target Universe: {stats.get('target_count', 0)}")
    print(f"  Excluded - Stablecoin: {stats.get('filtered_stablecoin', 0)}")
    print(f"  Excluded - Wrapped:    {stats.get('filtered_wrapped', 0)}")
    print(f"  Excluded - Leveraged:  {stats.get('filtered_leveraged', 0)}")
    print(f"  Eligible for mapping:   {stats.get('eligible_for_mapping', 0)}")
    print(f"  EXACT_MATCH:            {stats.get('exact_matches', 0)}")
    print(f"  BASE_ASSET_MATCH:       {stats.get('base_asset_matches', 0)}")
    print(f"  AMBIGUOUS:              {stats.get('ambiguous', 0)}")
    print(f"  NO_MATCH:               {stats.get('no_match', 0)}")
    print(f"  FINAL UNIVERSE:         {stats.get('final_count', 0)} symbols")
    print(f"  BingX active contracts: {stats.get('bingx_active_contracts', 0)}")
    
    # Show sample mappings
    from src.data_provider.bingx_mapping import map_cmc_to_bingx, BingXContractRegistry, BingXMapper
    
    registry = BingXContractRegistry()
    registry.load_from_api(contracts)
    mapper = BingXMapper(registry)
    
    # Test a few symbols
    print("\nSample mappings:")
    for asset in cmc_assets[:10]:
        result = mapper.map_asset(asset)
        status = "✓" if result.is_mapped else "✗"
        print(f"  {status} {asset['symbol']:8s} → {result.state:20s} {result.bingx_symbol or 'N/A':12s} ({result.reason})")
    
    print("\n" + "="*60)
    print("DRY-RUN COMPLETE")
    print("="*60)
    return True


async def main():
    try:
        from src.exchange.coinmarketcap_fetcher import CoinMarketCapFetcher
        from src.exchange.bingx_fetcher import BingXFetcher
        from src.data_provider.bingx_mapping import map_cmc_to_bingx, BingXContractRegistry, BingXMapper
        
        print("="*80)
        print("CMC UNIVERSE DRY-RUN")
        print("="*80)
        print()
        
        # 1. Fetch CMC data
        print("\n[1/4] Fetching CMC rankings...")
        cmc_fetcher = CoinMarketCapFetcher()
        
        cmc_assets = await cmc_fetcher.fetch_target_universe()
        print(f"  CMC Target Universe: {len(cmc_assets)} assets (ranks 20-250)")
        print(f"  Sample: {[a['symbol'] for a in cmc_assets[:5]]}")
        
        # 2. Fetch BingX contracts
        print("\n[2/4] Fetching BingX contracts...")
        bingx_fetcher = BingXFetcher()
        contracts = await bingx_fetcher.get_contracts()
        print(f"  BingX contracts: {len(contracts)}")
        
        # Filter to USDT perpetual trading
        usdt_perpetual = [c for c in contracts if c.get('symbol', '').endswith('-USDT') and c.get('status') == 'Trading']
        print(f"  USDT Perpetual Trading: {len(usdt_perpetual)}")
        
        # 3. Run mapping pipeline
        print("\n[3/4] Running mapping pipeline...")
        final_universe, stats = map_cmc_to_bingx(cmc_assets, contracts)
        
        print(f"\n{'='*60}")
        print("DRY-RUN RESULTS")
        print("="*60)
        print(f"CMC Target Universe: {stats.get('target_count', 0)}")
        print(f"  Excluded - Stablecoin: {stats.get('filtered_stablecoin', 0)}")
        print(f"  Excluded - Wrapped:    {stats.get('filtered_wrapped', 0)}")
        print(f"  Excluded - Leveraged:  {stats.get('filtered_leveraged', 0)}")
        print(f"  Eligible for mapping:   {stats.get('eligible_for_mapping', 0)}")
        print(f"  EXACT_MATCH:            {stats.get('exact_matches', 0)}")
        print(f"  BASE_ASSET_MATCH:       {stats.get('base_asset_matches', 0)}")
        print(f"  AMBIGUOUS:              {stats.get('ambiguous', 0)}")
        print(f"  NO_MATCH:               {stats.get('no_match', 0)}")
        print(f"  FINAL UNIVERSE:         {stats.get('final_count', 0)} symbols")
        print(f"  BingX active contracts: {stats.get('bingx_active_contracts', 0)}")
        
        # Show sample mappings
        print("\nSample mappings:")
        registry = BingXContractRegistry()
        registry.load_from_api(contracts)
        mapper = BingXMapper(registry)
        
        for asset in cmc_assets[:10]:
            result = mapper.map_asset(asset)
            status = "[OK]" if result.is_mapped else "[FAIL]"
            print(f"  {status} {asset['symbol']:8s} -> {result.state:20s} {result.bingx_symbol or 'N/A':12s} ({result.reason})")
        
        print("\n" + "="*60)
        print("DRY-RUN COMPLETE")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    exit(0 if asyncio.run(main()) else 1)