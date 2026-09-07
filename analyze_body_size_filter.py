#!/usr/bin/env python3
"""
Research minimum body size filter for LW-001.

Goal: Find minimum body_percent that eliminates microscopic candles
while preserving large candles with relatively small lower wicks.
"""

import json
import statistics
from datetime import UTC, datetime


def load_verified_signals():
    """Load the 31 VERIFIED signals from original_timestamps_verification.json"""
    with open("original_timestamps_verification.json", "r") as f:
        data = json.load(f)
    
    # Filter only VERIFIED signals
    verified = [r for r in data["results"] if r["status"] == "VERIFIED"]
    return verified


def calculate_extended_metrics(signal):
    """Calculate extended metrics including body_percent, lower_wick_percent, range_percent"""
    open_price = signal["open"]
    high_price = signal["high"]
    low_price = signal["low"]
    close_price = signal["close"]
    
    # For red candle
    body = open_price - close_price
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    candle_range = high_price - low_price
    
    # Percentages
    body_percent = body / open_price * 100
    lower_wick_percent = lower_wick / open_price * 100
    upper_wick_percent = upper_wick / open_price * 100
    range_percent = candle_range / open_price * 100
    
    # Ratios
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    body_range_ratio = body / candle_range if candle_range > 0 else 0
    
    return {
        "body": body,
        "body_percent": body_percent,
        "lower_wick": lower_wick,
        "lower_wick_percent": lower_wick_percent,
        "upper_wick": upper_wick,
        "upper_wick_percent": upper_wick_percent,
        "candle_range": candle_range,
        "range_percent": range_percent,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "body_range_ratio": body_range_ratio,
    }


def fetch_previous_volume(symbol, target_timestamp_ms):
    """Fetch previous candle volume for volume ratio calculation."""
    import asyncio
    import sys
    sys.path.insert(0, "src")
    from src.exchange.bingx_fetcher import BingXFetcher
    from datetime import timedelta
    
    async def _fetch():
        fetcher = BingXFetcher()
        target_time = datetime.fromtimestamp(target_timestamp_ms / 1000, tz=UTC)
        start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
        end_time = int((target_time + timedelta(hours=1)).timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,
                start_time=start_time,
                end_time=end_time
            )
            
            # Find target candle
            target_index = -1
            for i, kline in enumerate(klines):
                if int(kline['time']) == target_timestamp_ms:
                    target_index = i
                    break
            
            if target_index > 0:
                return float(klines[target_index - 1]['volume'])
            return 0
        except Exception as e:
            print(f"Error fetching previous volume for {symbol}: {e}")
            return 0
    
    return asyncio.run(_fetch())


def analyze_body_percent_distribution(signals_with_metrics):
    """Analyze body_percent distribution."""
    body_percents = [s["body_percent"] for s in signals_with_metrics]
    
    print("=" * 120)
    print("BODY PERCENT DISTRIBUTION")
    print("=" * 120)
    print()
    print(f"Total signals: {len(body_percents)}")
    print()
    print("Statistics:")
    print(f"  Minimum: {min(body_percents):.4f}%")
    print(f"  Maximum: {max(body_percents):.4f}%")
    print(f"  Mean: {statistics.mean(body_percents):.4f}%")
    print(f"  Median: {statistics.median(body_percents):.4f}%")
    
    if len(body_percents) >= 4:
        q1 = statistics.quantiles(body_percents, n=4)[0]
        q3 = statistics.quantiles(body_percents, n=4)[2]
        print(f"  Q1 (25%): {q1:.4f}%")
        print(f"  Q3 (75%): {q3:.4f}%")
    
    print()
    print("Distribution by ranges:")
    ranges = [
        (0, 0.01, "0 - 0.01%"),
        (0.01, 0.02, "0.01 - 0.02%"),
        (0.02, 0.03, "0.02 - 0.03%"),
        (0.03, 0.05, "0.03 - 0.05%"),
        (0.05, 0.07, "0.05 - 0.07%"),
        (0.07, 0.10, "0.07 - 0.10%"),
        (0.10, 0.15, "0.10 - 0.15%"),
        (0.15, 0.20, "0.15 - 0.20%"),
        (0.20, 0.30, "0.20 - 0.30%"),
        (0.30, float('inf'), "0.30%+"),
    ]
    
    for min_r, max_r, label in ranges:
        count = sum(1 for bp in body_percents if min_r <= bp < max_r)
        pct = count / len(body_percents) * 100
        print(f"  {label:<15} {count:2d}/{len(body_percents)} ({pct:5.1f}%)")
    
    print()
    print("Coverage at different thresholds:")
    thresholds = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]
    for t in thresholds:
        count = sum(1 for bp in body_percents if bp >= t)
        pct = count / len(body_percents) * 100
        print(f"  body_percent >= {t:.2f}%: {count:2d}/{len(body_percents)} ({pct:5.1f}%)")


def compare_candle_types(signals_with_metrics):
    """Compare small vs large candles with different LW/Body ratios."""
    print()
    print("=" * 120)
    print("CANDLE TYPE COMPARISON")
    print("=" * 120)
    
    # Type A: Small candles with LW/Body >= 2x
    type_a = [s for s in signals_with_metrics 
              if s["body_percent"] < 0.10 and s["lower_wick_body_ratio"] >= 2.0]
    
    # Type B: Large candles with LW/Body 1.1-2x
    type_b = [s for s in signals_with_metrics 
              if s["body_percent"] >= 0.10 and 1.1 <= s["lower_wick_body_ratio"] < 2.0]
    
    print()
    print(f"Type A: Small candles (body < 0.10%) with LW/Body >= 2x: {len(type_a)}")
    if type_a:
        print(f"  Avg body_percent: {statistics.mean([s['body_percent'] for s in type_a]):.4f}%")
        print(f"  Avg LW/Body: {statistics.mean([s['lower_wick_body_ratio'] for s in type_a]):.2f}x")
        print(f"  Avg range_percent: {statistics.mean([s['range_percent'] for s in type_a]):.4f}%")
        print()
        print("  Examples:")
        for s in type_a[:5]:
            print(f"    {s['symbol']}: body={s['body_percent']:.4f}%, LW/Body={s['lower_wick_body_ratio']:.2f}x, range={s['range_percent']:.4f}%")
    
    print()
    print(f"Type B: Large candles (body >= 0.10%) with LW/Body 1.1-2x: {len(type_b)}")
    if type_b:
        print(f"  Avg body_percent: {statistics.mean([s['body_percent'] for s in type_b]):.4f}%")
        print(f"  Avg LW/Body: {statistics.mean([s['lower_wick_body_ratio'] for s in type_b]):.2f}x")
        print(f"  Avg range_percent: {statistics.mean([s['range_percent'] for s in type_b]):.4f}%")
        print()
        print("  Examples:")
        for s in type_b[:5]:
            print(f"    {s['symbol']}: body={s['body_percent']:.4f}%, LW/Body={s['lower_wick_body_ratio']:.2f}x, range={s['range_percent']:.4f}%")


def test_filter_combinations(signals_with_metrics):
    """Test various filter combinations."""
    print()
    print("=" * 120)
    print("EXPERIMENTAL FILTER COMBINATIONS")
    print("=" * 120)
    
    # Base condition: red + LW/Body >= 2.0
    base_signals = [s for s in signals_with_metrics if s["lower_wick_body_ratio"] >= 2.0]
    
    print()
    print(f"Base (Red + LW/Body >= 2.0): {len(base_signals)}/{len(signals_with_metrics)} ({len(base_signals)/len(signals_with_metrics)*100:.1f}%)")
    
    # Test various body_percent thresholds
    print()
    print("Body percent thresholds (with LW/Body >= 2.0):")
    thresholds = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]
    for t in thresholds:
        filtered = [s for s in base_signals if s["body_percent"] >= t]
        print(f"  body_percent >= {t:.2f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")
    
    # Test lower_wick_percent thresholds
    print()
    print("Lower wick percent thresholds (with LW/Body >= 2.0):")
    lw_thresholds = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]
    for t in lw_thresholds:
        filtered = [s for s in base_signals if s["lower_wick_percent"] >= t]
        print(f"  lower_wick_percent >= {t:.2f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")
    
    # Test range_percent thresholds
    print()
    print("Range percent thresholds (with LW/Body >= 2.0):")
    range_thresholds = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
    for t in range_thresholds:
        filtered = [s for s in base_signals if s["range_percent"] >= t]
        print(f"  range_percent >= {t:.1f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")
    
    # Test combinations
    print()
    print("Combined filters:")
    
    # Body + LW/Body
    for body_t in [0.05, 0.10, 0.15]:
        filtered = [s for s in signals_with_metrics 
                   if s["lower_wick_body_ratio"] >= 2.0 and s["body_percent"] >= body_t]
        print(f"  LW/Body >= 2.0 + body >= {body_t:.2f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")
    
    # Range + LW/Body
    for range_t in [0.5, 0.7, 1.0]:
        filtered = [s for s in signals_with_metrics 
                   if s["lower_wick_body_ratio"] >= 2.0 and s["range_percent"] >= range_t]
        print(f"  LW/Body >= 2.0 + range >= {range_t:.1f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")
    
    # Lower wick + LW/Body
    for lw_t in [0.05, 0.10, 0.15]:
        filtered = [s for s in signals_with_metrics 
                   if s["lower_wick_body_ratio"] >= 2.0 and s["lower_wick_percent"] >= lw_t]
        print(f"  LW/Body >= 2.0 + lower_wick >= {lw_t:.2f}%: {len(filtered)}/{len(signals_with_metrics)} ({len(filtered)/len(signals_with_metrics)*100:.1f}%)")


def show_boundary_examples(signals_with_metrics):
    """Show boundary examples for analysis."""
    print()
    print("=" * 120)
    print("BOUNDARY EXAMPLES")
    print("=" * 120)
    
    # Sort by body_percent
    sorted_by_body = sorted(signals_with_metrics, key=lambda x: x["body_percent"])
    
    print()
    print("Smallest candles (by body_percent):")
    print(f"{'Symbol':<15} {'Body %':<10} {'LW %':<10} {'Range %':<10} {'LW/Body':<10} {'Open':<10}")
    print("-" * 80)
    for s in sorted_by_body[:5]:
        print(f"{s['symbol']:<15} {s['body_percent']:<10.4f} {s['lower_wick_percent']:<10.4f} "
              f"{s['range_percent']:<10.4f} {s['lower_wick_body_ratio']:<10.2f} {s['open']:<10.6f}")
    
    print()
    print("Largest candles (by body_percent):")
    print(f"{'Symbol':<15} {'Body %':<10} {'LW %':<10} {'Range %':<10} {'LW/Body':<10} {'Open':<10}")
    print("-" * 80)
    for s in sorted_by_body[-5:]:
        print(f"{s['symbol']:<15} {s['body_percent']:<10.4f} {s['lower_wick_percent']:<10.4f} "
              f"{s['range_percent']:<10.4f} {s['lower_wick_body_ratio']:<10.2f} {s['open']:<10.6f}")
    
    # Small candles with high LW/Body
    small_high_lw = [s for s in signals_with_metrics 
                    if s["body_percent"] < 0.10 and s["lower_wick_body_ratio"] >= 2.0]
    small_high_lw.sort(key=lambda x: x["lower_wick_body_ratio"], reverse=True)
    
    print()
    print("Small candles (body < 0.10%) with high LW/Body (>= 2x):")
    print(f"{'Symbol':<15} {'Body %':<10} {'LW %':<10} {'Range %':<10} {'LW/Body':<10} {'Open':<10}")
    print("-" * 80)
    for s in small_high_lw[:5]:
        print(f"{s['symbol']:<15} {s['body_percent']:<10.4f} {s['lower_wick_percent']:<10.4f} "
              f"{s['range_percent']:<10.4f} {s['lower_wick_body_ratio']:<10.2f} {s['open']:<10.6f}")
    
    # Large candles with moderate LW/Body
    large_mod_lw = [s for s in signals_with_metrics 
                   if s["body_percent"] >= 0.10 and 1.1 <= s["lower_wick_body_ratio"] < 2.0]
    large_mod_lw.sort(key=lambda x: x["body_percent"], reverse=True)
    
    print()
    print("Large candles (body >= 0.10%) with moderate LW/Body (1.1-2x):")
    print(f"{'Symbol':<15} {'Body %':<10} {'LW %':<10} {'Range %':<10} {'LW/Body':<10} {'Open':<10}")
    print("-" * 80)
    for s in large_mod_lw[:5]:
        print(f"{s['symbol']:<15} {s['body_percent']:<10.4f} {s['lower_wick_percent']:<10.4f} "
              f"{s['range_percent']:<10.4f} {s['lower_wick_body_ratio']:<10.2f} {s['open']:<10.6f}")


def main():
    """Main analysis."""
    print("=" * 120)
    print("RESEARCH: MINIMUM BODY SIZE FILTER FOR LW-001")
    print("=" * 120)
    print()
    
    # Load verified signals
    verified_signals = load_verified_signals()
    print(f"Loaded {len(verified_signals)} VERIFIED signals")
    print()
    
    # Calculate extended metrics
    signals_with_metrics = []
    for signal in verified_signals:
        metrics = calculate_extended_metrics(signal)
        signals_with_metrics.append({**signal, **metrics})
    
    # Print detailed table
    print("=" * 120)
    print("DETAILED METRICS TABLE")
    print("=" * 120)
    print()
    print(f"{'Symbol':<15} {'MSK':<20} {'Open':<10} {'Body':<10} {'Body %':<10} {'LW':<10} {'LW %':<10} "
          f"{'LW/Body':<10} {'Range':<10} {'Range %':<10}")
    print("-" * 120)
    
    for s in signals_with_metrics:
        print(f"{s['symbol']:<15} {s['original_msk']:<20} {s['open']:<10.6f} {s['body']:<10.6f} "
              f"{s['body_percent']:<10.4f} {s['lower_wick']:<10.6f} {s['lower_wick_percent']:<10.4f} "
              f"{s['lower_wick_body_ratio']:<10.2f} {s['candle_range']:<10.6f} {s['range_percent']:<10.4f}")
    
    # Analyze distributions
    analyze_body_percent_distribution(signals_with_metrics)
    
    # Compare candle types
    compare_candle_types(signals_with_metrics)
    
    # Test filter combinations
    test_filter_combinations(signals_with_metrics)
    
    # Show boundary examples
    show_boundary_examples(signals_with_metrics)
    
    # Save results
    output = {
        "total_signals": len(signals_with_metrics),
        "signals": signals_with_metrics,
    }
    
    with open("body_size_filter_research.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Results saved to body_size_filter_research.json")


if __name__ == "__main__":
    main()
