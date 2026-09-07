#!/usr/bin/env python3
"""
Stage 2: Research Working Parameters for LW-001

Analyzes metric distributions and tests various threshold combinations
to find mathematically compatible and statistically viable parameters.
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
    "STORJ-USDT", "SC-USDT", "RVN-USDT", "KDA-USDT", "NEXO-USDT"
]

# Filter out Top-20 from mid-tier list
TEST_SYMBOLS = [s for s in MID_TIER_SYMBOLS if s not in TOP_20_EXCLUDE]


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


def calculate_percentiles(data, percentiles):
    """Calculate percentiles for data."""
    return {p: np.percentile(data, p) for p in percentiles}


def check_thresholds(metrics, thresholds):
    """Check if metrics pass all thresholds."""
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


async def collect_dataset():
    """Collect dataset from Top-21-250 symbols."""
    print("=" * 100)
    print("STAGE 2: COLLECTING DATASET")
    print("=" * 100)
    print()
    
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
    
    return all_metrics, symbols_with_data


def analyze_distributions(all_metrics):
    """Analyze distributions of all metrics."""
    print("=" * 100)
    print("METRIC DISTRIBUTIONS")
    print("=" * 100)
    print()
    
    percentiles = [50, 75, 80, 85, 90, 95, 97.5, 99]
    
    metrics_data = {
        'Range %': [m['range_pct'] for m in all_metrics],
        'Body %': [m['body_pct'] for m in all_metrics],
        'LW/Body x': [m['lw_body_ratio'] for m in all_metrics],
        'LW/Range %': [m['lw_range_pct'] for m in all_metrics],
        'Open->Low %': [m['open_low_pct'] for m in all_metrics],
        'Volume Ratio x': [m['volume_ratio'] for m in all_metrics]
    }
    
    print(f"{'Metric':<15} {'Min':<10} {'P50':<8} {'P75':<8} {'P80':<8} {'P85':<8} {'P90':<8} {'P95':<8} {'P97.5':<8} {'P99':<8} {'Max':<10}")
    print("-" * 110)
    
    for metric_name, data in metrics_data.items():
        dist = calculate_percentiles(data, percentiles)
        print(f"{metric_name:<15} {min(data):<10.2f} {dist[50]:<8.2f} {dist[75]:<8.2f} {dist[80]:<8.2f} {dist[85]:<8.2f} {dist[90]:<8.2f} {dist[95]:<8.2f} {dist[97.5]:<8.2f} {dist[99]:<8.2f} {max(data):<10.2f}")
    
    print()
    
    return metrics_data


def research_open_low_thresholds(all_metrics):
    """Research Open->Low thresholds."""
    print("=" * 100)
    print("OPEN->LOW THRESHOLD RESEARCH")
    print("=" * 100)
    print()
    
    thresholds = [-5.0, -4.5, -4.0, -3.5, -3.0, -2.5, -2.0]
    
    print(f"{'Threshold':<12} {'Candles':<10} {'%':<10} {'Symbols':<10}")
    print("-" * 42)
    
    for threshold in thresholds:
        passing = [m for m in all_metrics if m['open_low_pct'] <= threshold]
        unique_symbols = len(set(m['symbol'] for m in passing))
        pct = len(passing) / len(all_metrics) * 100
        
        print(f"{threshold:<12} {len(passing):<10} {pct:<10.4f} {unique_symbols:<10}")
    
    print()


def research_volume_ratio_thresholds(all_metrics):
    """Research Volume Ratio thresholds."""
    print("=" * 100)
    print("VOLUME RATIO THRESHOLD RESEARCH")
    print("=" * 100)
    print()
    
    thresholds = [2.6, 2.5, 2.25, 2.0, 1.75, 1.5]
    
    print(f"{'Threshold':<12} {'Candles':<10} {'%':<10} {'Symbols':<10}")
    print("-" * 42)
    
    for threshold in thresholds:
        passing = [m for m in all_metrics if m['volume_ratio'] >= threshold]
        unique_symbols = len(set(m['symbol'] for m in passing))
        pct = len(passing) / len(all_metrics) * 100
        
        print(f"{threshold:<12} {len(passing):<10} {pct:<10.4f} {unique_symbols:<10}")
    
    print()


def test_candidate_parameters(all_metrics, candidates):
    """Test candidate parameter sets."""
    print("=" * 100)
    print("CANDIDATE PARAMETER TESTING")
    print("=" * 100)
    print()
    
    results = {}
    
    for candidate_name, thresholds in candidates.items():
        print(f"Testing {candidate_name}...")
        print(f"  {thresholds}")
        
        passing_candles = []
        symbol_counts = defaultdict(int)
        
        for m in all_metrics:
            if check_thresholds(m, thresholds):
                passing_candles.append(m)
                symbol_counts[m['symbol']] += 1
        
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
        
        # Find top 5 symbols
        top_5 = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_5_count = sum(count for _, count in top_5)
        top_5_pct = top_5_count / total_passing * 100 if total_passing > 0 else 0
        
        results[candidate_name] = {
            'thresholds': thresholds,
            'total_passing': total_passing,
            'percent_of_dataset': (total_passing / len(all_metrics)) * 100,
            'unique_symbols': unique_symbols,
            'min_per_symbol': min_per_symbol,
            'median_per_symbol': median_per_symbol,
            'avg_per_symbol': avg_per_symbol,
            'max_per_symbol': max_per_symbol,
            'top_5': top_5,
            'top_5_count': top_5_count,
            'top_5_pct': top_5_pct,
            'symbol_counts': dict(symbol_counts),
            'passing_candles': passing_candles
        }
        
        print(f"  Total passing: {total_passing}")
        print(f"  % of dataset: {results[candidate_name]['percent_of_dataset']:.4f}%")
        print(f"  Unique symbols: {unique_symbols}")
        print(f"  Min/Median/Avg/Max per symbol: {min_per_symbol:.1f} / {median_per_symbol:.1f} / {avg_per_symbol:.1f} / {max_per_symbol}")
        print(f"  Top-5 concentration: {top_5_pct:.2f}%")
        print()
    
    return results


def show_real_candles(results, candidate_name, num_candles=10):
    """Show real candle examples for a candidate."""
    print("=" * 100)
    print(f"REAL CANDLE EXAMPLES: {candidate_name}")
    print("=" * 100)
    print()
    
    if candidate_name not in results:
        print(f"Candidate {candidate_name} not found in results")
        return
    
    passing_candles = results[candidate_name]['passing_candles']
    thresholds = results[candidate_name]['thresholds']
    
    if len(passing_candles) == 0:
        print("No candles pass this candidate")
        return
    
    # Get candles from different symbols if possible
    shown_symbols = set()
    candles_to_show = []
    
    for candle in passing_candles:
        if candle['symbol'] not in shown_symbols:
            candles_to_show.append(candle)
            shown_symbols.add(candle['symbol'])
            if len(candles_to_show) >= num_candles:
                break
    
    # If we don't have enough unique symbols, add more from any symbol
    if len(candles_to_show) < num_candles:
        for candle in passing_candles:
            if len(candles_to_show) >= num_candles:
                break
            candles_to_show.append(candle)
    
    for i, candle in enumerate(candles_to_show[:num_candles], 1):
        print(f"Example {i}:")
        print(f"  Symbol: {candle['symbol']}")
        print(f"  Timestamp: {candle['timestamp']}")
        print(f"  O: {candle['open']:.4f}, H: {candle['high']:.4f}, L: {candle['low']:.4f}, C: {candle['close']:.4f}")
        print(f"  Range: {candle['range_pct']:.2f}% (threshold: {thresholds['range_pct']}%) - {'PASS' if candle['range_pct'] >= thresholds['range_pct'] else 'FAIL'}")
        print(f"  Body: {candle['body_pct']:.2f}% (threshold: {thresholds['body_pct']}%) - {'PASS' if candle['body_pct'] >= thresholds['body_pct'] else 'FAIL'}")
        print(f"  LW/Body: {candle['lw_body_ratio']:.2f}x (threshold: {thresholds['lw_body_ratio']}x) - {'PASS' if candle['lw_body_ratio'] >= thresholds['lw_body_ratio'] else 'FAIL'}")
        print(f"  LW/Range: {candle['lw_range_pct']:.2f}% (threshold: {thresholds['lw_range_pct']}%) - {'PASS' if candle['lw_range_pct'] >= thresholds['lw_range_pct'] else 'FAIL'}")
        print(f"  Open->Low: {candle['open_low_pct']:.2f}% (threshold: {thresholds['open_low_pct']}%) - {'PASS' if candle['open_low_pct'] <= thresholds['open_low_pct'] else 'FAIL'}")
        print(f"  Volume Ratio: {candle['volume_ratio']:.2f}x (threshold: {thresholds['volume_ratio']}x) - {'PASS' if candle['volume_ratio'] >= thresholds['volume_ratio'] else 'FAIL'}")
        print()


def generate_final_table(results):
    """Generate final comparison table."""
    print("=" * 100)
    print("FINAL COMPARISON TABLE")
    print("=" * 100)
    print()
    
    print(f"{'Variant':<15} {'Range':<8} {'Body':<8} {'LW/Body':<10} {'LW/Range':<12} {'Open->Low':<12} {'Vol':<8} {'Signals':<10} {'Symbols':<10}")
    print("-" * 105)
    
    for candidate_name in sorted(results.keys()):
        r = results[candidate_name]
        t = r['thresholds']
        
        print(f"{candidate_name:<15} {t['range_pct']:<8} {t['body_pct']:<8} {t['lw_body_ratio']:<10} {t['lw_range_pct']:<12} {t['open_low_pct']:<12} {t['volume_ratio']:<8} {r['total_passing']:<10} {r['unique_symbols']:<10}")
    
    print()


async def main():
    """Main function for Stage 2 research."""
    print("=" * 100)
    print("STAGE 2: RESEARCH WORKING PARAMETERS FOR LW-001")
    print("=" * 100)
    print()
    
    # Step 1: Collect dataset
    all_metrics, symbols_with_data = await collect_dataset()
    
    if len(all_metrics) == 0:
        print("ERROR: No data collected. Exiting.")
        return
    
    # Step 2: Analyze distributions
    metrics_data = analyze_distributions(all_metrics)
    
    # Step 3: Research Open->Low thresholds
    research_open_low_thresholds(all_metrics)
    
    # Step 4: Research Volume Ratio thresholds
    research_volume_ratio_thresholds(all_metrics)
    
    # Step 5: Define candidate parameters
    # Based on geometric analysis and distribution data
    candidates = {
        "CONSERVATIVE": {
            "range_pct": 6.0,
            "body_pct": 1.5,
            "lw_body_ratio": 2.0,
            "lw_range_pct": 70.0,
            "open_low_pct": -4.0,
            "volume_ratio": 2.0
        },
        "BALANCED_1": {
            "range_pct": 5.0,
            "body_pct": 1.2,
            "lw_body_ratio": 1.8,
            "lw_range_pct": 65.0,
            "open_low_pct": -3.5,
            "volume_ratio": 1.75
        },
        "BALANCED_2": {
            "range_pct": 4.5,
            "body_pct": 1.0,
            "lw_body_ratio": 1.5,
            "lw_range_pct": 60.0,
            "open_low_pct": -3.0,
            "volume_ratio": 1.5
        },
        "MODERATE_1": {
            "range_pct": 4.0,
            "body_pct": 0.8,
            "lw_body_ratio": 1.3,
            "lw_range_pct": 55.0,
            "open_low_pct": -2.5,
            "volume_ratio": 1.5
        },
        "MODERATE_2": {
            "range_pct": 3.5,
            "body_pct": 0.6,
            "lw_body_ratio": 1.2,
            "lw_range_pct": 50.0,
            "open_low_pct": -2.5,
            "volume_ratio": 1.5
        },
        "SOFT_1": {
            "range_pct": 3.0,
            "body_pct": 0.5,
            "lw_body_ratio": 1.0,
            "lw_range_pct": 45.0,
            "open_low_pct": -2.0,
            "volume_ratio": 1.5
        },
        "SOFT_2": {
            "range_pct": 2.5,
            "body_pct": 0.4,
            "lw_body_ratio": 0.8,
            "lw_range_pct": 40.0,
            "open_low_pct": -2.0,
            "volume_ratio": 1.5
        }
    }
    
    # Step 6: Test candidates
    results = test_candidate_parameters(all_metrics, candidates)
    
    # Step 7: Generate final table
    generate_final_table(results)
    
    # Step 8: Show real candles for best candidates
    print("=" * 100)
    print("DETAILED ANALYSIS OF BEST CANDIDATES")
    print("=" * 100)
    print()
    
    # Select candidates with reasonable signal count and good distribution
    for candidate_name in ["CONSERVATIVE", "BALANCED_1", "BALANCED_2", "MODERATE_1"]:
        if candidate_name in results and results[candidate_name]['total_passing'] > 0:
            print(f"\n{'='*100}")
            print(f"DETAILED: {candidate_name}")
            print(f"{'='*100}\n")
            
            r = results[candidate_name]
            print(f"Total signals: {r['total_passing']}")
            print(f"Unique symbols: {r['unique_symbols']}")
            print(f"Min/Median/Avg/Max per symbol: {r['min_per_symbol']:.1f} / {r['median_per_symbol']:.1f} / {r['avg_per_symbol']:.1f} / {r['max_per_symbol']:.1f}")
            print(f"Top-5 symbols: {r['top_5']}")
            print(f"Top-5 concentration: {r['top_5_pct']:.2f}%")
            print()
            
            show_real_candles(results, candidate_name, num_candles=10)
    
    print("=" * 100)
    print("STAGE 2: RESEARCH COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
