#!/usr/bin/env python3
"""
Analyze LW-001 Threshold Funnel

This script analyzes how many historical candles pass each threshold
and each combination of thresholds to identify bottlenecks.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import UTC, datetime, timedelta
from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    check_all_conditions,
    LW001_THRESHOLDS
)


async def fetch_historical_candles(symbol: str = "BTC-USDT", count: int = 1000):
    """Fetch historical candles for funnel analysis."""
    print("=" * 100)
    print(f"FETCHING {count} HISTORICAL CANDLES FOR {symbol}")
    print("=" * 100)
    
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=count * 0.25 / 96)  # 15m candles, ~96 per day
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    candles = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        start_time=start_ms,
        end_time=end_ms,
        limit=count
    )
    
    print(f"Fetched {len(candles)} candles\n")
    return candles


def calculate_avg_volume_20(candles: list, index: int) -> float:
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    volumes = [float(candles[i]['volume']) for i in range(start_idx, index)]
    return sum(volumes) / len(volumes) if volumes else 1.0


def analyze_single_conditions(candles: list):
    """Analyze how many candles pass each individual condition."""
    print("\n" + "=" * 100)
    print("INDIVIDUAL CONDITION ANALYSIS")
    print("=" * 100)
    
    results = {
        "range": 0,
        "body": 0,
        "lw_body": 0,
        "lw_range": 0,
        "open_low": 0,
        "volume": 0
    }
    
    for i in range(len(candles)):
        avg_volume_20 = calculate_avg_volume_20(candles, i)
        
        open_price = float(candles[i]['open'])
        high_price = float(candles[i]['high'])
        low_price = float(candles[i]['low'])
        close_price = float(candles[i]['close'])
        volume = float(candles[i]['volume'])
        
        metrics = calculate_all_metrics(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            reference_average_volume=avg_volume_20
        )
        
        if metrics.range_pct >= LW001_THRESHOLDS['range_pct']['value']:
            results["range"] += 1
        
        if metrics.body_pct >= LW001_THRESHOLDS['body_pct']['value']:
            results["body"] += 1
        
        if metrics.lower_wick_body_ratio >= LW001_THRESHOLDS['lower_wick_body_ratio']['value']:
            results["lw_body"] += 1
        
        if metrics.lower_wick_range_pct >= LW001_THRESHOLDS['lower_wick_range_pct']['value']:
            results["lw_range"] += 1
        
        if metrics.open_to_low_pct <= LW001_THRESHOLDS['open_to_low_pct']['value']:
            results["open_low"] += 1
        
        if metrics.volume_ratio >= LW001_THRESHOLDS['volume_ratio']['value']:
            results["volume"] += 1
    
    total = len(candles)
    
    print(f"\nTotal candles analyzed: {total}\n")
    print(f"1. Range >= {LW001_THRESHOLDS['range_pct']['value']}%: {results['range']} ({results['range']/total*100:.2f}%)")
    print(f"2. Body >= {LW001_THRESHOLDS['body_pct']['value']}%: {results['body']} ({results['body']/total*100:.2f}%)")
    print(f"3. LW/Body >= {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x: {results['lw_body']} ({results['lw_body']/total*100:.2f}%)")
    print(f"4. LW/Range >= {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%: {results['lw_range']} ({results['lw_range']/total*100:.2f}%)")
    print(f"5. Open->Low <= {LW001_THRESHOLDS['open_to_low_pct']['value']}%: {results['open_low']} ({results['open_low']/total*100:.2f}%)")
    print(f"6. Volume Ratio >= {LW001_THRESHOLDS['volume_ratio']['value']}x: {results['volume']} ({results['volume']/total*100:.2f}%)")
    
    return results


def analyze_combinations(candles: list):
    """Analyze how many candles pass combinations of conditions."""
    print("\n" + "=" * 100)
    print("COMBINATION ANALYSIS")
    print("=" * 100)
    
    # Track which conditions each candle passes
    condition_passes = []
    
    for i in range(len(candles)):
        avg_volume_20 = calculate_avg_volume_20(candles, i)
        
        open_price = float(candles[i]['open'])
        high_price = float(candles[i]['high'])
        low_price = float(candles[i]['low'])
        close_price = float(candles[i]['close'])
        volume = float(candles[i]['volume'])
        
        metrics = calculate_all_metrics(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            reference_average_volume=avg_volume_20
        )
        
        passes = {
            "range": metrics.range_pct >= LW001_THRESHOLDS['range_pct']['value'],
            "body": metrics.body_pct >= LW001_THRESHOLDS['body_pct']['value'],
            "lw_body": metrics.lower_wick_body_ratio >= LW001_THRESHOLDS['lower_wick_body_ratio']['value'],
            "lw_range": metrics.lower_wick_range_pct >= LW001_THRESHOLDS['lower_wick_range_pct']['value'],
            "open_low": metrics.open_to_low_pct <= LW001_THRESHOLDS['open_to_low_pct']['value'],
            "volume": metrics.volume_ratio >= LW001_THRESHOLDS['volume_ratio']['value']
        }
        
        condition_passes.append(passes)
    
    total = len(candles)
    
    # Count combinations
    def count_combinations(min_conditions):
        count = 0
        for passes in condition_passes:
            if sum(passes.values()) >= min_conditions:
                count += 1
        return count
    
    # Count all 6 conditions (AND logic)
    all_6 = sum(1 for passes in condition_passes if all(passes.values()))
    
    print(f"\nTotal candles analyzed: {total}\n")
    print(f"Pass >= 1 condition: {count_combinations(1)} ({count_combinations(1)/total*100:.2f}%)")
    print(f"Pass >= 2 conditions: {count_combinations(2)} ({count_combinations(2)/total*100:.2f}%)")
    print(f"Pass >= 3 conditions: {count_combinations(3)} ({count_combinations(3)/total*100:.2f}%)")
    print(f"Pass >= 4 conditions: {count_combinations(4)} ({count_combinations(4)/total*100:.2f}%)")
    print(f"Pass >= 5 conditions: {count_combinations(5)} ({count_combinations(5)/total*100:.2f}%)")
    print(f"Pass ALL 6 conditions (AND): {all_6} ({all_6/total*100:.4f}%)")
    
    # Find which conditions are most restrictive
    print("\n" + "-" * 100)
    print("MOST RESTRICTIVE CONDITIONS (lowest pass rate)")
    print("-" * 100)
    
    single_results = analyze_single_conditions(candles)
    sorted_conditions = sorted(single_results.items(), key=lambda x: x[1])
    
    for name, count in sorted_conditions:
        pct = count / total * 100
        print(f"{name:15s}: {count:4d} ({pct:6.2f}%)")
    
    return all_6


async def run_funnel_analysis():
    """Run complete funnel analysis."""
    candles = await fetch_historical_candles(symbol="BTC-USDT", count=1000)
    
    if len(candles) < 100:
        print("ERROR: Need at least 100 candles for analysis")
        return
    
    single_results = analyze_single_conditions(candles)
    all_6_pass = analyze_combinations(candles)
    
    # Summary
    print("\n" + "=" * 100)
    print("FUNNEL ANALYSIS SUMMARY")
    print("=" * 100)
    
    total = len(candles)
    
    print(f"\nTotal candles analyzed: {total}")
    print(f"Candles passing ALL 6 conditions: {all_6_pass}")
    print(f"Pass rate: {all_6_pass/total*100:.4f}%")
    
    if all_6_pass == 0:
        print("\n[INFO] No candles pass all 6 conditions in this sample.")
        print("This indicates the current thresholds may be too strict for this market/timeframe.")
        print("Recommendation: Analyze individual condition pass rates to identify bottlenecks.")
    elif all_6_pass < 5:
        print(f"\n[INFO] Only {all_6_pass} candles pass all 6 conditions.")
        print("This is a very low signal rate. Consider analyzing individual conditions.")
    else:
        print(f"\n[INFO] {all_6_pass} candles pass all 6 conditions.")
        print("This is a reasonable signal rate for the current thresholds.")


if __name__ == "__main__":
    asyncio.run(run_funnel_analysis())
