#!/usr/bin/env python3
"""
Comparative Threshold Test for LW-001

Tests 5 threshold variants on rank 21-250 symbols (excluding Top-20).
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta
from collections import defaultdict
import numpy as np

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    LW001_THRESHOLDS
)


# Top-20 symbols to EXCLUDE
TOP_20_EXCLUDE = {
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT",
    "LTC-USDT", "ATOM-USDT", "NEAR-USDT", "OP-USDT", "ARB-USDT"
}

# Mid-tier symbols (rank 21-250 approximation)
MID_TIER_SYMBOLS = [
    "PEPE-USDT", "SHIB-USDT", "FLOKI-USDT", "BONK-USDT", "WIF-USDT",
    "ORDI-USDT", "SATS-USDT", "1000PEPE-USDT", "1000SHIB-USDT", "MEME-USDT",
    "TIA-USDT", "SEI-USDT", "SUI-USDT", "INJ-USDT", "APT-USDT",
    "FTM-USDT", "QNT-USDT", "ALGO-USDT", "VET-USDT", "ICP-USDT",
    "HBAR-USDT", "EOS-USDT", "XLM-USDT", "XEM-USDT", "XTZ-USDT",
    "BCH-USDT", "ETC-USDT", "ZEC-USDT", "DASH-USDT", "KAVA-USDT",
    "MINA-USDT", "ROSE-USDT", "CELO-USDT", "GLM-USDT", "RNDR-USDT",
    "FET-USDT", "AGIX-USDT", "OCEAN-USDT", "MASK-USDT", "LDO-USDT",
    "AAVE-USDT", "MKR-USDT", "COMP-USDT", "UNI-USDT", "CRV-USDT",
    "SNX-USDT", "1INCH-USDT", "YFI-USDT", "PERP-USDT", "GMX-USDT",
    "GRT-USDT", "LRC-USDT", "MANA-USDT", "SAND-USDT", "AXS-USDT",
    "ENJ-USDT", "IMX-USDT", "GALA-USDT", "STX-USDT", "FLOW-USDT",
    "NEO-USDT", "ONT-USDT", "ZIL-USDT", "QTUM-USDT", "IOST-USDT",
    "TRX-USDT", "XDC-USDT", "CSPR-USDT", "PHB-USDT", "KSM-USDT",
    "DOT-USDT", "AVAX-USDT", "NEAR-USDT", "FIL-USDT", "AR-USDT",
    "STORJ-USDT", "SC-USDT", "RVN-USDT", "KDA-USDT", "NEXO-USDT",
    "BUSD-USDT", "USDC-USDT", "USDT-USDT", "DAI-USDT", "TUSD-USDT"
]

# Filter out Top-20 from mid-tier list
TEST_SYMBOLS = [s for s in MID_TIER_SYMBOLS if s not in TOP_20_EXCLUDE]

# Threshold variants
THRESHOLD_VARIANTS = {
    "BASE": {
        "range_pct": 6.0,
        "body_pct": 1.9,
        "lw_body_ratio": 2.5,
        "lw_range_pct": 63.0,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    },
    "OPTION_1": {
        "range_pct": 6.0,
        "body_pct": 1.51,
        "lw_body_ratio": 2.5,
        "lw_range_pct": 63.0,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    },
    "OPTION_2": {
        "range_pct": 7.54,
        "body_pct": 1.9,
        "lw_body_ratio": 2.5,
        "lw_range_pct": 63.0,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    },
    "OPTION_3": {
        "range_pct": 6.0,
        "body_pct": 1.9,
        "lw_body_ratio": 1.99,
        "lw_range_pct": 63.0,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    },
    "OPTION_4": {
        "range_pct": 6.0,
        "body_pct": 1.9,
        "lw_body_ratio": 2.5,
        "lw_range_pct": 79.2,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    },
    "OPTION_5": {
        "range_pct": 6.0,
        "body_pct": 1.9,
        "lw_body_ratio": 2.0,
        "lw_range_pct": 70.0,
        "open_low_pct": -5.0,
        "volume_ratio": 2.6
    }
}


async def fetch_historical_candles_for_symbol(symbol: str, days: int = 60):
    """Fetch historical candles for a single symbol."""
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        return candles
    except Exception as e:
        print(f"  Error: {e}")
        return []


def calculate_avg_volume_20(candles, index):
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    if start_idx >= index:
        return 1.0
    
    volumes = []
    for i in range(start_idx, index):
        vol = float(candles[i].get('volume', candles[i].get('vol', 0)))
        volumes.append(vol)
    
    if not volumes:
        return 1.0
    
    return sum(volumes) / len(volumes)


def check_conditions(metrics, thresholds):
    """Check if metrics pass all conditions."""
    # Handle both dict and object input
    if isinstance(metrics, dict):
        range_pct = metrics['range_pct']
        body_pct = metrics['body_pct']
        lw_body_ratio = metrics['lw_body_ratio']
        lw_range_pct = metrics['lw_range_pct']
        open_low_pct = metrics['open_low_pct']
        volume_ratio = metrics['volume_ratio']
    else:
        range_pct = metrics.range_pct
        body_pct = metrics.body_pct
        lw_body_ratio = metrics.lower_wick_body_ratio
        lw_range_pct = metrics.lower_wick_range_pct
        open_low_pct = metrics.open_to_low_pct
        volume_ratio = metrics.volume_ratio
    
    return (
        range_pct >= thresholds["range_pct"] and
        body_pct >= thresholds["body_pct"] and
        lw_body_ratio >= thresholds["lw_body_ratio"] and
        lw_range_pct >= thresholds["lw_range_pct"] and
        open_low_pct <= thresholds["open_low_pct"] and
        volume_ratio >= thresholds["volume_ratio"]
    )


def run_funnel_analysis(all_metrics, thresholds):
    """Run funnel analysis for a threshold variant."""
    total = len(all_metrics)
    
    funnel = {
        "start": total,
        "range": 0,
        "body": 0,
        "lw_body": 0,
        "lw_range": 0,
        "open_low": 0,
        "volume": 0,
        "final": 0
    }
    
    for m in all_metrics:
        passed = True
        
        if m['range_pct'] >= thresholds["range_pct"]:
            funnel["range"] += 1
        else:
            passed = False
        
        if passed and m['body_pct'] >= thresholds["body_pct"]:
            funnel["body"] += 1
        else:
            passed = False
        
        if passed and m['lw_body_ratio'] >= thresholds["lw_body_ratio"]:
            funnel["lw_body"] += 1
        else:
            passed = False
        
        if passed and m['lw_range_pct'] >= thresholds["lw_range_pct"]:
            funnel["lw_range"] += 1
        else:
            passed = False
        
        if passed and m['open_low_pct'] <= thresholds["open_low_pct"]:
            funnel["open_low"] += 1
        else:
            passed = False
        
        if passed and m['volume_ratio'] >= thresholds["volume_ratio"]:
            funnel["volume"] += 1
            funnel["final"] += 1
    
    return funnel


async def main():
    print("=" * 100)
    print("COMPARATIVE THRESHOLD TEST FOR LW-001")
    print("=" * 100)
    print()
    
    print("Dataset Configuration:")
    print(f"  Symbols: Rank 21-250 (excluding Top-20)")
    print(f"  Total symbols to test: {len(TEST_SYMBOLS)}")
    print(f"  Period: 60 days")
    print(f"  Timeframe: 15m")
    print()
    
    # Collect dataset
    print("=" * 100)
    print("COLLECTING DATASET")
    print("=" * 100)
    
    all_metrics = []
    symbols_with_data = []
    
    for i, symbol in enumerate(TEST_SYMBOLS, 1):
        print(f"[{i}/{len(TEST_SYMBOLS)}] Fetching {symbol}...")
        candles = await fetch_historical_candles_for_symbol(symbol, days=60)
        
        if not candles:
            print(f"  No data")
            continue
        
        print(f"  Collected {len(candles)} candles")
        symbols_with_data.append(symbol)
        
        for j in range(len(candles)):
            try:
                open_price = float(candles[j].get('open', 0))
                high_price = float(candles[j].get('high', 0))
                low_price = float(candles[j].get('low', 0))
                close_price = float(candles[j].get('close', 0))
                volume = float(candles[j].get('volume', candles[j].get('vol', 0)))
                
                if open_price <= 0:
                    continue
                
                avg_volume_20 = calculate_avg_volume_20(candles, j)
                
                metrics = calculate_all_metrics(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    reference_average_volume=avg_volume_20
                )
                
                all_metrics.append({
                    'symbol': symbol,
                    'timestamp': candles[j].get('time', candles[j].get('timestamp', 0)),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume,
                    'range_pct': metrics.range_pct,
                    'body_pct': metrics.body_pct,
                    'lw_body_ratio': metrics.lower_wick_body_ratio,
                    'lw_range_pct': metrics.lower_wick_range_pct,
                    'open_low_pct': metrics.open_to_low_pct,
                    'volume_ratio': metrics.volume_ratio
                })
            except Exception as e:
                continue
    
    print()
    print(f"Total candles collected: {len(all_metrics)}")
    print(f"Symbols with data: {len(symbols_with_data)}")
    print(f"Symbols without data: {len(TEST_SYMBOLS) - len(symbols_with_data)}")
    print()
    
    if len(all_metrics) == 0:
        print("ERROR: No data collected. Exiting.")
        return
    
    # Test each variant
    print("=" * 100)
    print("TESTING THRESHOLD VARIANTS")
    print("=" * 100)
    print()
    
    results = {}
    
    for variant_name, thresholds in THRESHOLD_VARIANTS.items():
        print(f"Testing {variant_name}...")
        print(f"  Thresholds: {thresholds}")
        
        # Find passing candles
        passing_candles = []
        symbol_counts = defaultdict(int)
        
        for m in all_metrics:
            if check_conditions(m, thresholds):
                passing_candles.append(m)
                symbol_counts[m['symbol']] += 1
        
        # Calculate statistics
        total_passing = len(passing_candles)
        unique_symbols = len(symbol_counts)
        
        if unique_symbols > 0:
            counts = list(symbol_counts.values())
            min_per_symbol = min(counts)
            median_per_symbol = np.median(counts)
            avg_per_symbol = np.mean(counts)
            max_per_symbol = max(counts)
        else:
            min_per_symbol = median_per_symbol = avg_per_symbol = max_per_symbol = 0
        
        # Calculate average metrics for passing candles
        if total_passing > 0:
            avg_range = np.mean([m['range_pct'] for m in passing_candles])
            avg_body = np.mean([m['body_pct'] for m in passing_candles])
            avg_lw_body = np.mean([m['lw_body_ratio'] for m in passing_candles])
            avg_lw_range = np.mean([m['lw_range_pct'] for m in passing_candles])
            avg_open_low = np.mean([m['open_low_pct'] for m in passing_candles])
            avg_vol_ratio = np.mean([m['volume_ratio'] for m in passing_candles])
        else:
            avg_range = avg_body = avg_lw_body = avg_lw_range = avg_open_low = avg_vol_ratio = 0
        
        # Funnel analysis
        funnel = run_funnel_analysis(all_metrics, thresholds)
        
        results[variant_name] = {
            'total_passing': total_passing,
            'percent_of_dataset': (total_passing / len(all_metrics)) * 100,
            'unique_symbols': unique_symbols,
            'min_per_symbol': min_per_symbol,
            'median_per_symbol': median_per_symbol,
            'avg_per_symbol': avg_per_symbol,
            'max_per_symbol': max_per_symbol,
            'avg_range': avg_range,
            'avg_body': avg_body,
            'avg_lw_body': avg_lw_body,
            'avg_lw_range': avg_lw_range,
            'avg_open_low': avg_open_low,
            'avg_vol_ratio': avg_vol_ratio,
            'funnel': funnel,
            'symbol_counts': dict(symbol_counts),
            'passing_candles': passing_candles
        }
        
        print(f"  Total passing: {total_passing}")
        print(f"  % of dataset: {results[variant_name]['percent_of_dataset']:.4f}%")
        print(f"  Unique symbols: {unique_symbols}")
        print(f"  Min/Median/Avg/Max per symbol: {min_per_symbol:.1f} / {median_per_symbol:.1f} / {avg_per_symbol:.1f} / {max_per_symbol}")
        print()
    
    # Print final comparison table
    print("=" * 100)
    print("FINAL COMPARISON TABLE")
    print("=" * 100)
    print()
    print(f"{'Variant':<12} {'Candles':<10} {'%':<12} {'Symbols':<10} {'Min/Med/Avg/Max':<25} {'Bottleneck'}")
    print("-" * 100)
    
    for variant_name in ["BASE", "OPTION_1", "OPTION_2", "OPTION_3", "OPTION_4", "OPTION_5"]:
        r = results[variant_name]
        bottleneck = "None"
        if r['funnel']['range'] == 0:
            bottleneck = "Range"
        elif r['funnel']['body'] == 0:
            bottleneck = "Body"
        elif r['funnel']['lw_body'] == 0:
            bottleneck = "LW/Body"
        elif r['funnel']['lw_range'] == 0:
            bottleneck = "LW/Range"
        elif r['funnel']['open_low'] == 0:
            bottleneck = "Open->Low"
        elif r['funnel']['volume'] == 0:
            bottleneck = "Volume"
        
        print(f"{variant_name:<12} {r['total_passing']:<10} {r['percent_of_dataset']:<12.4f} {r['unique_symbols']:<10} "
              f"{r['min_per_symbol']:.1f}/{r['median_per_symbol']:.1f}/{r['avg_per_symbol']:.1f}/{r['max_per_symbol']:<5.1f} {bottleneck}")
    
    print()
    
    # Print funnel details for each variant
    print("=" * 100)
    print("FUNNEL ANALYSIS DETAILS")
    print("=" * 100)
    print()
    
    for variant_name in ["BASE", "OPTION_1", "OPTION_2", "OPTION_3", "OPTION_4", "OPTION_5"]:
        r = results[variant_name]
        f = r['funnel']
        
        print(f"{variant_name}:")
        print(f"  Start: {f['start']} (100.00%)")
        print(f"  Range: {f['range']} ({f['range']/f['start']*100:.2f}% of start)")
        print(f"  Body: {f['body']} ({f['body']/f['start']*100:.2f}% of start)")
        print(f"  LW/Body: {f['lw_body']} ({f['lw_body']/f['start']*100:.2f}% of start)")
        print(f"  LW/Range: {f['lw_range']} ({f['lw_range']/f['start']*100:.2f}% of start)")
        print(f"  Open->Low: {f['open_low']} ({f['open_low']/f['start']*100:.2f}% of start)")
        print(f"  Volume: {f['volume']} ({f['volume']/f['start']*100:.2f}% of start)")
        print(f"  FINAL: {f['final']} ({f['final']/f['start']*100:.2f}% of start)")
        print()
    
    # Print symbol distribution for variants with signals
    print("=" * 100)
    print("SYMBOL DISTRIBUTION (for variants with signals)")
    print("=" * 100)
    print()
    
    for variant_name in ["OPTION_1", "OPTION_2", "OPTION_3", "OPTION_4", "OPTION_5"]:
        r = results[variant_name]
        if r['total_passing'] > 0:
            print(f"{variant_name}:")
            print(f"  {'Symbol':<20} {'Signals':<10}")
            print(f"  {'-'*20} {'-'*10}")
            for symbol, count in sorted(r['symbol_counts'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {symbol:<20} {count:<10}")
            print()
    
    # Print real candle examples
    print("=" * 100)
    print("REAL CANDLE EXAMPLES (up to 5 per variant)")
    print("=" * 100)
    print()
    
    for variant_name in ["OPTION_1", "OPTION_2", "OPTION_3", "OPTION_4", "OPTION_5"]:
        r = results[variant_name]
        if r['total_passing'] > 0:
            print(f"{variant_name}:")
            for i, candle in enumerate(r['passing_candles'][:5], 1):
                print(f"  Example {i}:")
                print(f"    Symbol: {candle['symbol']}")
                print(f"    Timestamp: {candle['timestamp']}")
                print(f"    O: {candle['open']:.4f}, H: {candle['high']:.4f}, L: {candle['low']:.4f}, C: {candle['close']:.4f}")
                print(f"    Range: {candle['range_pct']:.2f}%, Body: {candle['body_pct']:.2f}%")
                print(f"    LW/Body: {candle['lw_body_ratio']:.2f}x, LW/Range: {candle['lw_range_pct']:.2f}%")
                print(f"    Open->Low: {candle['open_low_pct']:.2f}%, Vol Ratio: {candle['volume_ratio']:.2f}x")
                print()
    
    print("=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
