#!/usr/bin/env python3
"""
Research minimum candle size filter for LW-001.

Goal: Find quantitative filter that eliminates microscopic candles
while preserving large candles capable of significant downward sweeps.
"""

import json
import statistics


def load_verified_signals():
    """Load 31 verified manual signals from reanalysis data."""
    with open("reanalysis_manual_signals.json", "r") as f:
        data = json.load(f)
    
    # Filter only found RED signals
    verified = [r for r in data["results"] if r.get("found") and r.get("color") == "RED"]
    return verified


def print_detailed_metrics_table(signals):
    """Print detailed table with 16 metrics for each signal."""
    print("=" * 180)
    print("DETAILED METRICS TABLE - 31 VERIFIED SIGNALS")
    print("=" * 180)
    print()
    
    print(f"{'Symbol':<15} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'Body':<12} {'Body%':<10} {'LW':<12} {'LW%':<10} {'UW':<12} {'Range':<12} {'Range%':<10} {'LW/Body':<10} {'LW/Range':<10} {'Vol':<12} {'PrevVol':<12} {'VolRatio':<10}")
    print("-" * 180)
    
    for s in signals:
        print(f"{s['symbol']:<15} {s['open']:<12.6f} {s['high']:<12.6f} {s['low']:<12.6f} {s['close']:<12.6f} "
              f"{s['body']:<12.6f} {s['body_percent']:<10.4f} {s['lower_wick']:<12.6f} {s['lower_wick_percent']:<10.4f} "
              f"{s['upper_wick']:<12.6f} {s['candle_range']:<12.6f} {s['range_percent']:<10.4f} {s['lower_wick_body_ratio']:<10.2f} "
              f"{s['lower_wick_range_ratio']*100:<10.1f} {s['volume']:<12.2f} {s['previous_volume']:<12.2f} {s['volume_ratio_prev']:<10.2f}")


def analyze_body_percent_thresholds(signals):
    """Analyze Body % thresholds from 0.10% to 2.00%."""
    print()
    print("=" * 180)
    print("BODY PERCENT THRESHOLD ANALYSIS")
    print("=" * 180)
    print()
    
    body_percents = [s["body_percent"] for s in signals]
    
    print("Body Percent Statistics:")
    print(f"  Minimum: {min(body_percents):.4f}%")
    print(f"  Maximum: {max(body_percents):.4f}%")
    print(f"  Mean: {statistics.mean(body_percents):.4f}%")
    print(f"  Median: {statistics.median(body_percents):.4f}%")
    print()
    
    thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00]
    
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in thresholds:
        filtered = [s for s in signals if s["body_percent"] >= t]
        lost = [s for s in signals if s["body_percent"] < t]
        
        lost_symbols = ", ".join([f"{s['symbol']} ({s['body_percent']:.4f}%)" for s in lost]) if lost else "None"
        
        print(f"{t:.2f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    print("Signals with lowest Body %:")
    sorted_by_body = sorted(signals, key=lambda x: x["body_percent"])
    for s in sorted_by_body[:5]:
        print(f"  {s['symbol']}: Body%={s['body_percent']:.4f}%, Range%={s['range_percent']:.4f}%, LW/Body={s['lower_wick_body_ratio']:.2f}x")


def analyze_range_percent_thresholds(signals):
    """Analyze Range % thresholds from 0.5% to 5.0%."""
    print()
    print("=" * 180)
    print("RANGE PERCENT THRESHOLD ANALYSIS")
    print("=" * 180)
    print()
    
    range_percents = [s["range_percent"] for s in signals]
    
    print("Range Percent Statistics:")
    print(f"  Minimum: {min(range_percents):.4f}%")
    print(f"  Maximum: {max(range_percents):.4f}%")
    print(f"  Mean: {statistics.mean(range_percents):.4f}%")
    print(f"  Median: {statistics.median(range_percents):.4f}%")
    print()
    
    thresholds = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in thresholds:
        filtered = [s for s in signals if s["range_percent"] >= t]
        lost = [s for s in signals if s["range_percent"] < t]
        
        lost_symbols = ", ".join([f"{s['symbol']} ({s['range_percent']:.4f}%)" for s in lost]) if lost else "None"
        
        print(f"{t:.1f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")


def test_filter_combinations(signals):
    """Test filter combinations A-D with different X values."""
    print()
    print("=" * 180)
    print("FILTER COMBINATIONS ANALYSIS")
    print("=" * 180)
    print()
    
    body_thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00]
    range_thresholds = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    
    # Combination A: Red + LW/Body >= 1.0 + Body% >= X + Volume Ratio >= 0.5
    print("Combination A: Red + LW/Body >= 1.0 + Body% >= X + Volume Ratio >= 0.5")
    print(f"{'X (Body%)':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in body_thresholds:
        filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["body_percent"] >= t and s["volume_ratio_prev"] >= 0.5]
        lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["body_percent"] >= t and s["volume_ratio_prev"] >= 0.5)]
        
        lost_symbols = ", ".join([f"{s['symbol']}" for s in lost[:5]]) + ("..." if len(lost) > 5 else "") if lost else "None"
        
        print(f"{t:.2f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    print("Combination B: Red + LW/Body >= 1.0 + Range% >= X + Volume Ratio >= 0.5")
    print(f"{'X (Range%)':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in range_thresholds:
        filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= t and s["volume_ratio_prev"] >= 0.5]
        lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= t and s["volume_ratio_prev"] >= 0.5)]
        
        lost_symbols = ", ".join([f"{s['symbol']}" for s in lost[:5]]) + ("..." if len(lost) > 5 else "") if lost else "None"
        
        print(f"{t:.1f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    print("Combination C: Red + LW/Range >= 30% + Body% >= X + Volume Ratio >= 0.5")
    print(f"{'X (Body%)':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in body_thresholds:
        filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["body_percent"] >= t and s["volume_ratio_prev"] >= 0.5]
        lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["body_percent"] >= t and s["volume_ratio_prev"] >= 0.5)]
        
        lost_symbols = ", ".join([f"{s['symbol']}" for s in lost[:5]]) + ("..." if len(lost) > 5 else "") if lost else "None"
        
        print(f"{t:.2f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    print("Combination D: Red + LW/Range >= 30% + Range% >= X + Volume Ratio >= 0.5")
    print(f"{'X (Range%)':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 180)
    
    for t in range_thresholds:
        filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= t and s["volume_ratio_prev"] >= 0.5]
        lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= t and s["volume_ratio_prev"] >= 0.5)]
        
        lost_symbols = ", ".join([f"{s['symbol']}" for s in lost[:5]]) + ("..." if len(lost) > 5 else "") if lost else "None"
        
        print(f"{t:.1f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")


def find_boundary_signals(signals):
    """Find signals at the boundary of different thresholds."""
    print()
    print("=" * 180)
    print("BOUNDARY SIGNALS ANALYSIS")
    print("=" * 180)
    print()
    
    # Signals with lowest Body %
    print("Signals with lowest Body % (potential boundary):")
    sorted_by_body = sorted(signals, key=lambda x: x["body_percent"])
    for s in sorted_by_body[:10]:
        print(f"  {s['symbol']:<15} Body%={s['body_percent']:<10.4f}% Range%={s['range_percent']:<10.4f}% LW/Body={s['lower_wick_body_ratio']:<10.2f}x VolRatio={s['volume_ratio_prev']:<10.2f}x")
    
    print()
    print("Signals with lowest Range % (potential boundary):")
    sorted_by_range = sorted(signals, key=lambda x: x["range_percent"])
    for s in sorted_by_range[:10]:
        print(f"  {s['symbol']:<15} Body%={s['body_percent']:<10.4f}% Range%={s['range_percent']:<10.4f}% LW/Body={s['lower_wick_body_ratio']:<10.2f}x VolRatio={s['volume_ratio_prev']:<10.2f}x")
    
    print()
    print("Signals with LW/Body 1.0-1.5x (moderate lower wick):")
    moderate_lw = [s for s in signals if 1.0 <= s["lower_wick_body_ratio"] < 1.5]
    for s in moderate_lw:
        print(f"  {s['symbol']:<15} Body%={s['body_percent']:<10.4f}% Range%={s['range_percent']:<10.4f}% LW/Body={s['lower_wick_body_ratio']:<10.2f}x VolRatio={s['volume_ratio_prev']:<10.2f}x")


def main():
    """Main analysis."""
    print("=" * 180)
    print("RESEARCH: MINIMUM CANDLE SIZE FILTER FOR LW-001")
    print("=" * 180)
    print()
    
    # Load verified signals
    signals = load_verified_signals()
    print(f"Loaded {len(signals)} verified RED signals")
    print()
    
    # Print detailed metrics table
    print_detailed_metrics_table(signals)
    
    # Analyze Body % thresholds
    analyze_body_percent_thresholds(signals)
    
    # Analyze Range % thresholds
    analyze_range_percent_thresholds(signals)
    
    # Test filter combinations
    test_filter_combinations(signals)
    
    # Find boundary signals
    find_boundary_signals(signals)
    
    # Save results
    output = {
        "total_signals": len(signals),
        "signals": signals,
    }
    
    with open("minimum_candle_size_research.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Results saved to minimum_candle_size_research.json")


if __name__ == "__main__":
    main()
