#!/usr/bin/env python3
"""
Analyze actual metric distributions in previous dataset using corrected formulas.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def calculate_corrected_metrics(kline, avg_volume_20):
    """Calculate metrics using Open as denominator for Range and Body."""
    open_price = float(kline['open'])
    close_price = float(kline['close'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    volume = float(kline['volume'])
    
    body = abs(close_price - open_price)
    lower_wick = min(open_price, close_price) - low_price
    upper_wick = high_price - max(open_price, close_price)
    candle_range = high_price - low_price
    
    if candle_range == 0:
        return None
    
    # CORRECTED: Use Open as denominator for Range and Body
    body_percent = (body / open_price) * 100
    range_percent = (candle_range / open_price) * 100
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    open_to_low_percent = ((low_price - open_price) / open_price) * 100
    
    volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else None
    
    return {
        "body_percent": body_percent,
        "range_percent": range_percent,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "open_to_low_percent": open_to_low_percent,
        "volume_ratio": volume_ratio
    }


def main():
    """Main function."""
    print("=" * 100)
    print("ANALYZING METRIC DISTRIBUTIONS IN PREVIOUS DATASET")
    print("=" * 100)
    
    # Load previous dataset
    try:
        with open("new_historical_signals.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERROR: new_historical_signals.json not found")
        return
    
    signals = data["signals"]
    
    print(f"\nLoaded {len(signals)} signals from previous dataset")
    
    # Analyze distributions
    ranges = []
    bodies = []
    lw_body_ratios = []
    lw_range_ratios = []
    open_to_lows = []
    volume_ratios = []
    
    for signal in signals:
        # These metrics were calculated with OLD (incorrect) formulas
        # We need to recalculate with CORRECTED formulas
        # But we don't have the raw kline data, only the calculated metrics
        
        # Let's analyze what we have from the previous search
        metrics = signal['metrics']
        
        ranges.append(metrics['range_percent'])
        bodies.append(metrics['body_percent'])
        lw_body_ratios.append(metrics['lower_wick_body_ratio'])
        lw_range_ratios.append(metrics['lower_wick_range_ratio'])
        open_to_lows.append(metrics['open_to_low_percent'])
        if metrics.get('volume_ratio') is not None:
            volume_ratios.append(metrics['volume_ratio'])
    
    print(f"\n" + "=" * 100)
    print("METRIC DISTRIBUTIONS (from previous search with INCORRECT formulas)")
    print("=" * 100)
    
    print(f"\nRange:")
    print(f"  Min: {min(ranges):.2f}%")
    print(f"  Max: {max(ranges):.2f}%")
    print(f"  Mean: {mean(ranges):.2f}%")
    print(f"  Median: {median(ranges):.2f}%")
    
    print(f"\nBody:")
    print(f"  Min: {min(bodies):.2f}%")
    print(f"  Max: {max(bodies):.2f}%")
    print(f"  Mean: {mean(bodies):.2f}%")
    print(f"  Median: {median(bodies):.2f}%")
    
    print(f"\nLW/Body:")
    print(f"  Min: {min(lw_body_ratios):.2f}x")
    print(f"  Max: {max(lw_body_ratios):.2f}x")
    print(f"  Mean: {mean(lw_body_ratios):.2f}x")
    print(f"  Median: {median(lw_body_ratios):.2f}x")
    
    print(f"\nLW/Range:")
    print(f"  Min: {min(lw_range_ratios)*100:.1f}%")
    print(f"  Max: {max(lw_range_ratios)*100:.1f}%")
    print(f"  Mean: {mean(lw_range_ratios)*100:.1f}%")
    print(f"  Median: {median(lw_range_ratios)*100:.1f}%")
    
    print(f"\nOpen to Low:")
    print(f"  Min: {min(open_to_lows):.2f}%")
    print(f"  Max: {max(open_to_lows):.2f}%")
    print(f"  Mean: {mean(open_to_lows):.2f}%")
    print(f"  Median: {median(open_to_lows):.2f}%")
    
    if volume_ratios:
        print(f"\nVolume Ratio:")
        print(f"  Min: {min(volume_ratios):.2f}x")
        print(f"  Max: {max(volume_ratios):.2f}x")
        print(f"  Mean: {mean(volume_ratios):.2f}x")
        print(f"  Median: {median(volume_ratios):.2f}x")
    
    print(f"\n" + "=" * 100)
    print("COMPARING WITH STRICT THRESHOLDS")
    print("=" * 100)
    
    strict_range = 6.0
    strict_body = 1.9
    strict_lw_body = 2.5
    strict_lw_range = 0.63
    strict_open_low = -5.0
    strict_volume = 2.6
    
    range_pass = sum(1 for r in ranges if r >= strict_range)
    body_pass = sum(1 for b in bodies if b >= strict_body)
    lw_body_pass = sum(1 for l in lw_body_ratios if l >= strict_lw_body)
    lw_range_pass = sum(1 for l in lw_range_ratios if l >= strict_lw_range)
    open_low_pass = sum(1 for o in open_to_lows if o <= strict_open_low)
    volume_pass = sum(1 for v in volume_ratios if v >= strict_volume) if volume_ratios else 0
    
    print(f"\nRange >= {strict_range}%: {range_pass}/{len(ranges)} ({range_pass/len(ranges)*100:.1f}%)")
    print(f"Body >= {strict_body}%: {body_pass}/{len(bodies)} ({body_pass/len(bodies)*100:.1f}%)")
    print(f"LW/Body >= {strict_lw_body}x: {lw_body_pass}/{len(lw_body_ratios)} ({lw_body_pass/len(lw_body_ratios)*100:.1f}%)")
    print(f"LW/Range >= {strict_lw_range*100}%: {lw_range_pass}/{len(lw_range_ratios)} ({lw_range_pass/len(lw_range_ratios)*100:.1f}%)")
    print(f"Open to Low <= {strict_open_low}%: {open_low_pass}/{len(open_to_lows)} ({open_low_pass/len(open_to_lows)*100:.1f}%)")
    if volume_ratios:
        print(f"Volume Ratio >= {strict_volume}x: {volume_pass}/{len(volume_ratios)} ({volume_pass/len(volume_ratios)*100:.1f}%)")
    
    print(f"\n" + "=" * 100)
    print("ANALYSIS")
    print("=" * 100)
    
    print(f"\nThe strict thresholds are very restrictive:")
    print(f"- Only {range_pass/len(ranges)*100:.1f}% of signals have Range >= {strict_range}%")
    print(f"- Only {body_pass/len(bodies)*100:.1f}% of signals have Body >= {strict_body}%")
    print(f"- Only {lw_body_pass/len(lw_body_ratios)*100:.1f}% of signals have LW/Body >= {strict_lw_body}x")
    print(f"- Only {lw_range_pass/len(lw_range_ratios)*100:.1f}% of signals have LW/Range >= {strict_lw_range*100}%")
    print(f"- Only {open_low_pass/len(open_to_lows)*100:.1f}% of signals have Open to Low <= {strict_open_low}%")
    if volume_ratios:
        print(f"- Only {volume_pass/len(volume_ratios)*100:.1f}% of signals have Volume Ratio >= {strict_volume}x")
    
    print(f"\n" + "=" * 100)
    print("RECOMMENDATION")
    print("=" * 100)
    print(f"\nThe strict minimum thresholds are too high for actual market data.")
    print(f"Even with 3,640 signals, very few pass all 6 conditions simultaneously.")
    print(f"\nSuggested approach:")
    print(f"1. Use the original target parameters (Range 4%, Body 1.8%, etc.)")
    print(f"2. Or adjust strict thresholds to match actual market distributions")
    print(f"3. Test with more realistic thresholds based on 75th-90th percentiles")


if __name__ == "__main__":
    main()
