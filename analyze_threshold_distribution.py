#!/usr/bin/env python3
"""
Threshold Distribution Analysis for LW-001

This script collects a large dataset of historical candles and analyzes
the distribution of canonical metrics to understand why current thresholds
produce 0 signals.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import UTC, datetime, timedelta
from collections import defaultdict
import numpy as np
from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    LW001_THRESHOLDS
)


async def fetch_top_symbols(limit: int = 250):
    """Fetch top trading pairs from exchange."""
    print("=" * 100)
    print(f"FETCHING TOP {limit} SYMBOLS")
    print("=" * 100)
    
    # Use hardcoded list of popular symbols (BingX doesn't have public ticker endpoint)
    symbols = [
        "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
        "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT",
        "LTC-USDT", "ATOM-USDT", "NEAR-USDT", "OP-USDT", "ARB-USDT"
    ]
    
    # Limit to requested number
    symbols = symbols[:limit]
    print(f"Using {len(symbols)} symbols\n")
    return symbols


async def fetch_historical_candles_for_symbol(symbol: str, days: int = 60):
    """Fetch historical candles for a single symbol."""
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    candles = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        start_time=start_ms,
        end_time=end_ms,
        limit=1000
    )
    
    return candles


def calculate_avg_volume_20(candles: list, index: int) -> float:
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    volumes = [float(candles[i]['volume']) for i in range(start_idx, index)]
    return sum(volumes) / len(volumes) if volumes else 1.0


def calculate_statistics(values: list) -> dict:
    """Calculate percentile statistics for a list of values."""
    if not values:
        return {}
    
    values_sorted = sorted(values)
    n = len(values_sorted)
    
    return {
        'count': n,
        'min': values_sorted[0],
        'p10': values_sorted[int(n * 0.1)] if n >= 10 else values_sorted[0],
        'p25': values_sorted[int(n * 0.25)] if n >= 4 else values_sorted[0],
        'p50': values_sorted[int(n * 0.5)],
        'p75': values_sorted[int(n * 0.75)] if n >= 4 else values_sorted[-1],
        'p90': values_sorted[int(n * 0.9)] if n >= 10 else values_sorted[-1],
        'p95': values_sorted[int(n * 0.95)] if n >= 20 else values_sorted[-1],
        'p99': values_sorted[int(n * 0.99)] if n >= 100 else values_sorted[-1],
        'max': values_sorted[-1]
    }


async def collect_dataset(symbols: list, days: int = 60, max_candles_per_symbol: int = 5000):
    """Collect large dataset of candles with canonical metrics."""
    print("=" * 100)
    print(f"COLLECTING DATASET: {len(symbols)} symbols, {days} days, 15m candles")
    print("=" * 100)
    
    all_metrics = []
    symbol_counts = defaultdict(int)
    
    for i, symbol in enumerate(symbols):
        print(f"\n[{i+1}/{len(symbols)}] Fetching {symbol}...")
        
        try:
            candles = await fetch_historical_candles_for_symbol(symbol, days)
            
            if not candles:
                print(f"  No candles fetched")
                continue
            
            # Limit candles per symbol to avoid memory issues
            candles = candles[:max_candles_per_symbol]
            
            for j in range(len(candles)):
                avg_volume_20 = calculate_avg_volume_20(candles, j)
                
                open_price = float(candles[j]['open'])
                high_price = float(candles[j]['high'])
                low_price = float(candles[j]['low'])
                close_price = float(candles[j]['close'])
                volume = float(candles[j]['volume'])
                
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
            
            symbol_counts[symbol] = len(candles)
            print(f"  Collected {len(candles)} candles")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"\nTotal candles collected: {len(all_metrics)}")
    print(f"Symbols with data: {len(symbol_counts)}")
    
    return all_metrics, symbol_counts


def analyze_distributions(all_metrics: list):
    """Analyze distribution of each metric."""
    print("\n" + "=" * 100)
    print("METRIC DISTRIBUTIONS")
    print("=" * 100)
    
    metrics_data = {
        'Range %': [m['range_pct'] for m in all_metrics],
        'Body %': [m['body_pct'] for m in all_metrics],
        'LW/Body': [m['lw_body_ratio'] for m in all_metrics],
        'LW/Range %': [m['lw_range_pct'] for m in all_metrics],
        'Open->Low %': [m['open_low_pct'] for m in all_metrics],
        'Volume Ratio': [m['volume_ratio'] for m in all_metrics]
    }
    
    print(f"\n{'Metric':<15} {'Count':>8} {'Min':>10} {'P50':>10} {'P75':>10} {'P90':>10} {'P95':>10} {'P99':>10} {'Max':>10}")
    print("-" * 100)
    
    for metric_name, values in metrics_data.items():
        stats = calculate_statistics(values)
        print(f"{metric_name:<15} {stats['count']:>8} {stats['min']:>10.4f} {stats['p50']:>10.4f} {stats['p75']:>10.4f} {stats['p90']:>10.4f} {stats['p95']:>10.4f} {stats['p99']:>10.4f} {stats['max']:>10.4f}")
    
    return metrics_data


def funnel_analysis(all_metrics: list):
    """Perform sequential funnel analysis."""
    print("\n" + "=" * 100)
    print("FUNNEL ANALYSIS")
    print("=" * 100)
    
    total = len(all_metrics)
    unique_symbols = len(set(m['symbol'] for m in all_metrics))
    
    print(f"\nStarting: {total} candles, {unique_symbols} unique symbols")
    
    # Step 1: Range >= 6%
    step1 = [m for m in all_metrics if m['range_pct'] >= LW001_THRESHOLDS['range_pct']['value']]
    print(f"After Range >= {LW001_THRESHOLDS['range_pct']['value']}%: {len(step1)} ({len(step1)/total*100:.2f}%), {len(set(m['symbol'] for m in step1))} symbols")
    
    # Step 2: Body >= 1.9%
    step2 = [m for m in step1 if m['body_pct'] >= LW001_THRESHOLDS['body_pct']['value']]
    print(f"After Body >= {LW001_THRESHOLDS['body_pct']['value']}%: {len(step2)} ({len(step2)/total*100:.2f}%), {len(set(m['symbol'] for m in step2))} symbols")
    
    # Step 3: LW/Body >= 2.5x
    step3 = [m for m in step2 if m['lw_body_ratio'] >= LW001_THRESHOLDS['lower_wick_body_ratio']['value']]
    print(f"After LW/Body >= {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x: {len(step3)} ({len(step3)/total*100:.2f}%), {len(set(m['symbol'] for m in step3))} symbols")
    
    # Step 4: LW/Range >= 63%
    step4 = [m for m in step3 if m['lw_range_pct'] >= LW001_THRESHOLDS['lower_wick_range_pct']['value']]
    print(f"After LW/Range >= {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%: {len(step4)} ({len(step4)/total*100:.2f}%), {len(set(m['symbol'] for m in step4))} symbols")
    
    # Step 5: Open->Low <= -5%
    step5 = [m for m in step4 if m['open_low_pct'] <= LW001_THRESHOLDS['open_to_low_pct']['value']]
    print(f"After Open->Low <= {LW001_THRESHOLDS['open_to_low_pct']['value']}%: {len(step5)} ({len(step5)/total*100:.2f}%), {len(set(m['symbol'] for m in step5))} symbols")
    
    # Step 6: Volume Ratio >= 2.6x
    step6 = [m for m in step5 if m['volume_ratio'] >= LW001_THRESHOLDS['volume_ratio']['value']]
    print(f"After Volume Ratio >= {LW001_THRESHOLDS['volume_ratio']['value']}x: {len(step6)} ({len(step6)/total*100:.2f}%), {len(set(m['symbol'] for m in step6))} symbols")
    
    print(f"\nFINAL: {len(step6)} candles pass ALL 6 conditions")
    
    return step6


def analyze_combinations(all_metrics: list):
    """Analyze combinations of 2-3 parameters."""
    print("\n" + "=" * 100)
    print("PARAMETER COMBINATIONS")
    print("=" * 100)
    
    total = len(all_metrics)
    
    # 2-parameter combinations
    combinations_2 = [
        ("Range + Body", lambda m: m['range_pct'] >= 6.0 and m['body_pct'] >= 1.9),
        ("Range + LW/Body", lambda m: m['range_pct'] >= 6.0 and m['lw_body_ratio'] >= 2.5),
        ("Range + LW/Range", lambda m: m['range_pct'] >= 6.0 and m['lw_range_pct'] >= 63.0),
        ("Range + Open->Low", lambda m: m['range_pct'] >= 6.0 and m['open_low_pct'] <= -5.0),
        ("Body + LW/Body", lambda m: m['body_pct'] >= 1.9 and m['lw_body_ratio'] >= 2.5),
        ("Body + LW/Range", lambda m: m['body_pct'] >= 1.9 and m['lw_range_pct'] >= 63.0),
        ("Body + Open->Low", lambda m: m['body_pct'] >= 1.9 and m['open_low_pct'] <= -5.0),
        ("LW/Body + LW/Range", lambda m: m['lw_body_ratio'] >= 2.5 and m['lw_range_pct'] >= 63.0),
        ("LW/Range + Open->Low", lambda m: m['lw_range_pct'] >= 63.0 and m['open_low_pct'] <= -5.0),
        ("Open->Low + Volume", lambda m: m['open_low_pct'] <= -5.0 and m['volume_ratio'] >= 2.6),
    ]
    
    print(f"\n2-Parameter Combinations:")
    print(f"{'Combination':<25} {'Count':>8} {'%':>10}")
    print("-" * 50)
    
    for name, condition in combinations_2:
        count = sum(1 for m in all_metrics if condition(m))
        print(f"{name:<25} {count:>8} {count/total*100:>10.4f}%")
    
    # 3-parameter combinations
    combinations_3 = [
        ("Range + Body + LW/Body", lambda m: m['range_pct'] >= 6.0 and m['body_pct'] >= 1.9 and m['lw_body_ratio'] >= 2.5),
        ("Range + LW/Body + LW/Range", lambda m: m['range_pct'] >= 6.0 and m['lw_body_ratio'] >= 2.5 and m['lw_range_pct'] >= 63.0),
        ("Range + LW/Range + Open->Low", lambda m: m['range_pct'] >= 6.0 and m['lw_range_pct'] >= 63.0 and m['open_low_pct'] <= -5.0),
        ("Body + LW/Body + LW/Range", lambda m: m['body_pct'] >= 1.9 and m['lw_body_ratio'] >= 2.5 and m['lw_range_pct'] >= 63.0),
    ]
    
    print(f"\n3-Parameter Combinations:")
    print(f"{'Combination':<35} {'Count':>8} {'%':>10}")
    print("-" * 60)
    
    for name, condition in combinations_3:
        count = sum(1 for m in all_metrics if condition(m))
        print(f"{name:<35} {count:>8} {count/total*100:>10.4f}%")


def find_closest_candles(all_metrics: list, n: int = 50):
    """Find candles closest to passing all conditions."""
    print("\n" + "=" * 100)
    print(f"CLOSEST CANDLES (Top {n} near-misses)")
    print("=" * 100)
    
    # Calculate "distance" from thresholds for each candle
    def calculate_distance(m):
        # Distance for each condition (how far from threshold)
        range_dist = max(0, 6.0 - m['range_pct'])
        body_dist = max(0, 1.9 - m['body_pct'])
        lw_body_dist = max(0, 2.5 - m['lw_body_ratio'])
        lw_range_dist = max(0, 63.0 - m['lw_range_pct'])
        open_low_dist = max(0, m['open_low_pct'] - (-5.0))  # Open->Low should be <= -5%
        volume_dist = max(0, 2.6 - m['volume_ratio'])
        
        # Normalize distances (rough normalization)
        return range_dist + body_dist + lw_body_dist + lw_range_dist + open_low_dist + volume_dist
    
    # Sort by distance (closest first)
    sorted_metrics = sorted(all_metrics, key=calculate_distance)
    
    # Get top N closest
    closest = sorted_metrics[:n]
    
    print(f"\n{'Symbol':<12} {'Range':>10} {'Body':>10} {'LW/B':>8} {'LW/R':>8} {'O->L':>8} {'Vol':>8} {'Pass':>4}")
    print("-" * 80)
    
    for m in closest:
        passes = sum([
            m['range_pct'] >= 6.0,
            m['body_pct'] >= 1.9,
            m['lw_body_ratio'] >= 2.5,
            m['lw_range_pct'] >= 63.0,
            m['open_low_pct'] <= -5.0,
            m['volume_ratio'] >= 2.6
        ])
        
        print(f"{m['symbol']:<12} {m['range_pct']:>10.2f} {m['body_pct']:>10.2f} {m['lw_body_ratio']:>8.2f} {m['lw_range_pct']:>8.2f} {m['open_low_pct']:>8.2f} {m['volume_ratio']:>8.2f} {passes:>4}/6")
    
    return closest


async def run_threshold_analysis():
    """Run complete threshold analysis."""
    # Step 1: Collect dataset
    symbols = await fetch_top_symbols(limit=50)  # Start with 50 symbols for testing
    all_metrics, symbol_counts = await collect_dataset(symbols, days=60, max_candles_per_symbol=2000)
    
    if len(all_metrics) < 1000:
        print("\nERROR: Dataset too small for analysis")
        return
    
    # Step 2: Analyze distributions
    metrics_data = analyze_distributions(all_metrics)
    
    # Step 3: Funnel analysis
    final_signals = funnel_analysis(all_metrics)
    
    # Step 4: Combinations analysis
    analyze_combinations(all_metrics)
    
    # Step 5: Find closest candles
    closest = find_closest_candles(all_metrics, n=50)
    
    # Summary
    print("\n" + "=" * 100)
    print("THRESHOLD ANALYSIS SUMMARY")
    print("=" * 100)
    
    print(f"\nTotal candles analyzed: {len(all_metrics)}")
    print(f"Symbols analyzed: {len(symbol_counts)}")
    print(f"Candles passing ALL 6 conditions: {len(final_signals)}")
    
    if len(final_signals) == 0:
        print("\n[INFO] No candles pass all 6 conditions.")
        print("This indicates the current thresholds may be too restrictive or describe a rare candle type.")
    else:
        print(f"\n[INFO] {len(final_signals)} candles pass all 6 conditions.")
        print("These are valid LW-001 signals with current thresholds.")


if __name__ == "__main__":
    asyncio.run(run_threshold_analysis())
