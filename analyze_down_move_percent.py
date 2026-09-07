#!/usr/bin/env python3
"""
Additional analysis: Calculate DownMove% for 31 manual signals.

Calculate:
1. Open → Low % - how much price dropped from Open to Low
2. Previous Close → Low % - how much price dropped from previous Close to Low
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import statistics
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def load_verified_signals():
    """Load 31 verified manual signals from previous research."""
    with open("minimum_candle_size_research.json", "r") as f:
        data = json.load(f)
    
    # Filter only found RED signals
    verified = [r for r in data["signals"] if r.get("found") and r.get("color") == "RED"]
    return verified


async def fetch_previous_candle(symbol: str, target_timestamp_ms: int, fetcher: BingXFetcher):
    """Fetch the previous M15 candle."""
    # Fetch data around the target time to get previous candle
    start_time = target_timestamp_ms - (4 * 15 * 60 * 1000)  # 4 hours before
    end_time = target_timestamp_ms + (15 * 60 * 1000)  # 15 minutes after
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        return None, f"API error: {e}"
    
    # Find target candle by timestamp
    target_index = -1
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        if kline_time == target_timestamp_ms:
            target_index = i
            break
    
    if target_index == -1:
        return None, "Target candle not found"
    
    # Get previous candle
    if target_index > 0:
        prev_kline = klines[target_index - 1]
        return prev_kline, None
    else:
        return None, "No previous candle available"


async def analyze_down_move(signals):
    """Analyze DownMove% for all signals."""
    print("=" * 140)
    print("ADDITIONAL ANALYSIS: DOWNMOVE% FOR 31 MANUAL SIGNALS")
    print("=" * 140)
    print()
    
    fetcher = BingXFetcher()
    
    results = []
    
    for i, signal in enumerate(signals, 1):
        symbol = signal["symbol"]
        open_price = signal["open"]
        high_price = signal["high"]
        low_price = signal["low"]
        close_price = signal["close"]
        timestamp_ms = signal["actual_timestamp_ms"]
        
        print(f"[{i}/31] Processing {symbol}...")
        
        # Calculate Open → Low %
        open_to_low_percent = (low_price - open_price) / open_price * 100
        
        # Fetch previous candle
        prev_kline, error = await fetch_previous_candle(symbol, timestamp_ms, fetcher)
        
        if error:
            print(f"  Error fetching previous candle: {error}")
            prev_close_to_low_percent = None
        else:
            prev_close = float(prev_kline['close'])
            prev_close_to_low_percent = (low_price - prev_close) / prev_close * 100
            print(f"  Previous Close: {prev_close:.6f}")
        
        print(f"  Open -> Low %: {open_to_low_percent:.4f}%")
        if prev_close_to_low_percent is not None:
            print(f"  Previous Close -> Low %: {prev_close_to_low_percent:.4f}%")
        
        result = {
            "symbol": symbol,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "open_to_low_percent": open_to_low_percent,
            "prev_close_to_low_percent": prev_close_to_low_percent,
            "timestamp_ms": timestamp_ms,
        }
        results.append(result)
    
    return results


def print_detailed_table(results):
    """Print detailed table with DownMove% data."""
    print()
    print("=" * 140)
    print("DETAILED DOWNMOVE% TABLE")
    print("=" * 140)
    print()
    
    print(f"{'Symbol':<15} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'Open->Low%':<12} {'PrevClose->Low%':<12}")
    print("-" * 140)
    
    for r in results:
        prev_close_low = f"{r['prev_close_to_low_percent']:.4f}%" if r['prev_close_to_low_percent'] is not None else "N/A"
        print(f"{r['symbol']:<15} {r['open']:<12.6f} {r['high']:<12.6f} {r['low']:<12.6f} {r['close']:<12.6f} "
              f"{r['open_to_low_percent']:<12.4f}% {prev_close_low:<12}")


def analyze_statistics(results):
    """Analyze statistics for DownMove%."""
    print()
    print("=" * 140)
    print("DOWNMOVE% STATISTICS")
    print("=" * 140)
    print()
    
    # Open -> Low %
    open_to_low_values = [r["open_to_low_percent"] for r in results]
    
    print("Open -> Low % Statistics:")
    print(f"  Minimum: {min(open_to_low_values):.4f}%")
    print(f"  Maximum: {max(open_to_low_values):.4f}%")
    print(f"  Mean: {statistics.mean(open_to_low_values):.4f}%")
    print(f"  Median: {statistics.median(open_to_low_values):.4f}%")
    print(f"  25th Percentile: {sorted(open_to_low_values)[int(len(open_to_low_values) * 0.25)]:.4f}%")
    print(f"  75th Percentile: {sorted(open_to_low_values)[int(len(open_to_low_values) * 0.75)]:.4f}%")
    print()
    
    # Previous Close -> Low %
    prev_close_to_low_values = [r["prev_close_to_low_percent"] for r in results if r["prev_close_to_low_percent"] is not None]
    
    if prev_close_to_low_values:
        print("Previous Close -> Low % Statistics:")
        print(f"  Minimum: {min(prev_close_to_low_values):.4f}%")
        print(f"  Maximum: {max(prev_close_to_low_values):.4f}%")
        print(f"  Mean: {statistics.mean(prev_close_to_low_values):.4f}%")
        print(f"  Median: {statistics.median(prev_close_to_low_values):.4f}%")
        print(f"  25th Percentile: {sorted(prev_close_to_low_values)[int(len(prev_close_to_low_values) * 0.25)]:.4f}%")
        print(f"  75th Percentile: {sorted(prev_close_to_low_values)[int(len(prev_close_to_low_values) * 0.75)]:.4f}%")
    
    print()
    print("Smallest DownMove% signals (Open -> Low %):")
    sorted_by_open_low = sorted(results, key=lambda x: x["open_to_low_percent"])
    for r in sorted_by_open_low[:10]:
        prev_close_low = f"{r['prev_close_to_low_percent']:.4f}%" if r['prev_close_to_low_percent'] is not None else "N/A"
        print(f"  {r['symbol']:<15} Open->Low%={r['open_to_low_percent']:<10.4f}% PrevClose->Low%={prev_close_low}")
    
    print()
    print("Largest DownMove% signals (Open -> Low %):")
    for r in sorted_by_open_low[-10:]:
        prev_close_low = f"{r['prev_close_to_low_percent']:.4f}%" if r['prev_close_to_low_percent'] is not None else "N/A"
        print(f"  {r['symbol']:<15} Open->Low%={r['open_to_low_percent']:<10.4f}% PrevClose->Low%={prev_close_low}")


async def main():
    """Main analysis."""
    print("=" * 140)
    print("ADDITIONAL ANALYSIS: DOWNMOVE% FOR 31 MANUAL SIGNALS")
    print("=" * 140)
    print()
    
    # Load verified signals
    signals = load_verified_signals()
    print(f"Loaded {len(signals)} verified RED signals")
    print()
    
    # Analyze down move
    results = await analyze_down_move(signals)
    
    # Print detailed table
    print_detailed_table(results)
    
    # Analyze statistics
    analyze_statistics(results)
    
    # Save results
    output = {
        "total_signals": len(results),
        "results": results,
    }
    
    with open("down_move_analysis.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Results saved to down_move_analysis.json")


if __name__ == "__main__":
    asyncio.run(main())
