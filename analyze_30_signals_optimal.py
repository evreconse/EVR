#!/usr/bin/env python3
"""
Comprehensive analysis of 30 manual signals (excluding FF-USDT).
Find optimal combination of conditions for new strategy.
"""

import json
import statistics


def load_30_signals():
    """Load 30 verified signals excluding FF-USDT."""
    # Load from minimum_candle_size_research.json
    with open("minimum_candle_size_research.json", "r") as f:
        data = json.load(f)
    
    # Filter only found RED signals, exclude FF-USDT
    verified = [r for r in data["signals"] if r.get("found") and r.get("color") == "RED" and r["symbol"] != "FF-USDT"]
    return verified


def load_down_move_data():
    """Load DownMove% data."""
    with open("down_move_analysis.json", "r") as f:
        data = json.load(f)
    return data["results"]


def merge_data(signals, down_move_data):
    """Merge candle data with DownMove% data."""
    # Create mapping by symbol
    down_move_map = {r["symbol"]: r for r in down_move_data}
    
    merged = []
    for signal in signals:
        symbol = signal["symbol"]
        if symbol in down_move_map:
            merged_signal = signal.copy()
            merged_signal["open_to_low_percent"] = down_move_map[symbol]["open_to_low_percent"]
            merged_signal["prev_close_to_low_percent"] = down_move_map[symbol]["prev_close_to_low_percent"]
            merged.append(merged_signal)
    
    return merged


def print_statistics(signals):
    """Print statistics for all metrics."""
    print("=" * 160)
    print("STATISTICS FOR 30 SIGNALS (EXCLUDING FF-USDT)")
    print("=" * 160)
    print()
    
    # Body%
    body_percents = [s["body_percent"] for s in signals]
    print("Body% Statistics:")
    print(f"  Minimum: {min(body_percents):.4f}%")
    print(f"  Maximum: {max(body_percents):.4f}%")
    print(f"  Mean: {statistics.mean(body_percents):.4f}%")
    print(f"  Median: {statistics.median(body_percents):.4f}%")
    print(f"  25th Percentile: {sorted(body_percents)[int(len(body_percents) * 0.25)]:.4f}%")
    print(f"  75th Percentile: {sorted(body_percents)[int(len(body_percents) * 0.75)]:.4f}%")
    print()
    
    # Range%
    range_percents = [s["range_percent"] for s in signals]
    print("Range% Statistics:")
    print(f"  Minimum: {min(range_percents):.4f}%")
    print(f"  Maximum: {max(range_percents):.4f}%")
    print(f"  Mean: {statistics.mean(range_percents):.4f}%")
    print(f"  Median: {statistics.median(range_percents):.4f}%")
    print(f"  25th Percentile: {sorted(range_percents)[int(len(range_percents) * 0.25)]:.4f}%")
    print(f"  75th Percentile: {sorted(range_percents)[int(len(range_percents) * 0.75)]:.4f}%")
    print()
    
    # LW/Body
    lw_body_ratios = [s["lower_wick_body_ratio"] for s in signals]
    print("LW/Body Statistics:")
    print(f"  Minimum: {min(lw_body_ratios):.2f}x")
    print(f"  Maximum: {max(lw_body_ratios):.2f}x")
    print(f"  Mean: {statistics.mean(lw_body_ratios):.2f}x")
    print(f"  Median: {statistics.median(lw_body_ratios):.2f}x")
    print(f"  25th Percentile: {sorted(lw_body_ratios)[int(len(lw_body_ratios) * 0.25)]:.2f}x")
    print(f"  75th Percentile: {sorted(lw_body_ratios)[int(len(lw_body_ratios) * 0.75)]:.2f}x")
    print()
    
    # LW/Range
    lw_range_ratios = [s["lower_wick_range_ratio"] for s in signals]
    print("LW/Range Statistics:")
    print(f"  Minimum: {min(lw_range_ratios)*100:.1f}%")
    print(f"  Maximum: {max(lw_range_ratios)*100:.1f}%")
    print(f"  Mean: {statistics.mean(lw_range_ratios)*100:.1f}%")
    print(f"  Median: {statistics.median(lw_range_ratios)*100:.1f}%")
    print(f"  25th Percentile: {sorted(lw_range_ratios)[int(len(lw_range_ratios) * 0.25)]*100:.1f}%")
    print(f"  75th Percentile: {sorted(lw_range_ratios)[int(len(lw_range_ratios) * 0.75)]*100:.1f}%")
    print()
    
    # Volume Ratio
    volume_ratios = [s["volume_ratio_prev"] for s in signals]
    print("Volume Ratio Statistics:")
    print(f"  Minimum: {min(volume_ratios):.2f}x")
    print(f"  Maximum: {max(volume_ratios):.2f}x")
    print(f"  Mean: {statistics.mean(volume_ratios):.2f}x")
    print(f"  Median: {statistics.median(volume_ratios):.2f}x")
    print(f"  25th Percentile: {sorted(volume_ratios)[int(len(volume_ratios) * 0.25)]:.2f}x")
    print(f"  75th Percentile: {sorted(volume_ratios)[int(len(volume_ratios) * 0.75)]:.2f}x")
    print()
    
    # Open -> Low %
    open_to_low = [s["open_to_low_percent"] for s in signals]
    print("Open -> Low % Statistics:")
    print(f"  Minimum: {min(open_to_low):.4f}%")
    print(f"  Maximum: {max(open_to_low):.4f}%")
    print(f"  Mean: {statistics.mean(open_to_low):.4f}%")
    print(f"  Median: {statistics.median(open_to_low):.4f}%")
    print(f"  25th Percentile: {sorted(open_to_low)[int(len(open_to_low) * 0.25)]:.4f}%")
    print(f"  75th Percentile: {sorted(open_to_low)[int(len(open_to_low) * 0.75)]:.4f}%")
    print()
    
    # Previous Close -> Low %
    prev_close_to_low = [s["prev_close_to_low_percent"] for s in signals if s["prev_close_to_low_percent"] is not None]
    print("Previous Close -> Low % Statistics:")
    print(f"  Minimum: {min(prev_close_to_low):.4f}%")
    print(f"  Maximum: {max(prev_close_to_low):.4f}%")
    print(f"  Mean: {statistics.mean(prev_close_to_low):.4f}%")
    print(f"  Median: {statistics.median(prev_close_to_low):.4f}%")
    print(f"  25th Percentile: {sorted(prev_close_to_low)[int(len(prev_close_to_low) * 0.25)]:.4f}%")
    print(f"  75th Percentile: {sorted(prev_close_to_low)[int(len(prev_close_to_low) * 0.75)]:.4f}%")


def analyze_threshold_coverage(signals):
    """Analyze coverage for different thresholds."""
    print()
    print("=" * 160)
    print("THRESHOLD COVERAGE ANALYSIS")
    print("=" * 160)
    print()
    
    # Body% thresholds
    body_thresholds = [0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00]
    print("Body% Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in body_thresholds:
        filtered = [s for s in signals if s["body_percent"] >= t]
        lost = [s for s in signals if s["body_percent"] < t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['body_percent']:.4f}%)" for s in lost]) if lost else "None"
        print(f"{t:.2f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    
    # Range% thresholds
    range_thresholds = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    print("Range% Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in range_thresholds:
        filtered = [s for s in signals if s["range_percent"] >= t]
        lost = [s for s in signals if s["range_percent"] < t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['range_percent']:.4f}%)" for s in lost]) if lost else "None"
        print(f"{t:.1f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    
    # LW/Body thresholds
    lw_body_thresholds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    print("LW/Body Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in lw_body_thresholds:
        filtered = [s for s in signals if s["lower_wick_body_ratio"] >= t]
        lost = [s for s in signals if s["lower_wick_body_ratio"] < t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['lower_wick_body_ratio']:.2f}x)" for s in lost]) if lost else "None"
        print(f"{t:.2f}x{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    
    # LW/Range thresholds
    lw_range_thresholds = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    print("LW/Range Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in lw_range_thresholds:
        filtered = [s for s in signals if s["lower_wick_range_ratio"] >= t]
        lost = [s for s in signals if s["lower_wick_range_ratio"] < t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['lower_wick_range_ratio']*100:.1f}%)" for s in lost]) if lost else "None"
        print(f"{t*100:.0f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    
    # Volume Ratio thresholds
    vol_thresholds = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0]
    print("Volume Ratio Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in vol_thresholds:
        filtered = [s for s in signals if s["volume_ratio_prev"] >= t]
        lost = [s for s in signals if s["volume_ratio_prev"] < t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['volume_ratio_prev']:.2f}x)" for s in lost]) if lost else "None"
        print(f"{t:.2f}x{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")
    
    print()
    
    # Open -> Low % thresholds
    down_move_thresholds = [-2.0, -2.5, -3.0, -3.5, -4.0, -5.0]
    print("Open -> Low % Threshold Coverage:")
    print(f"{'Threshold':<12} {'Coverage':<15} {'Lost':<10} {'Lost Signals'}")
    print("-" * 160)
    
    for t in down_move_thresholds:
        filtered = [s for s in signals if s["open_to_low_percent"] <= t]
        lost = [s for s in signals if s["open_to_low_percent"] > t]
        lost_symbols = ", ".join([f"{s['symbol']} ({s['open_to_low_percent']:.4f}%)" for s in lost]) if lost else "None"
        print(f"{t:.1f}%{'':<8} {len(filtered)}/{len(signals):<10} ({len(filtered)/len(signals)*100:.1f}%) {len(lost):<10} {lost_symbols}")


def test_combinations(signals):
    """Test various filter combinations."""
    print()
    print("=" * 160)
    print("FILTER COMBINATION ANALYSIS")
    print("=" * 160)
    print()
    
    # Combination 1: LW/Body >= 1.0 + Range% >= 2.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= 2.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= 2.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 1: LW/Body >= 1.0 + Range% >= 2.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 2: LW/Body >= 1.0 + Body% >= 0.40 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["body_percent"] >= 0.40 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["body_percent"] >= 0.40 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 2: LW/Body >= 1.0 + Body% >= 0.40 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 3: LW/Range >= 30% + Range% >= 2.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= 2.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= 2.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 3: LW/Range >= 30% + Range% >= 2.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 4: LW/Range >= 30% + Body% >= 0.40 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["body_percent"] >= 0.40 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["body_percent"] >= 0.40 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 4: LW/Range >= 30% + Body% >= 0.40 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 5: LW/Body >= 1.0 + Open->Low% <= -3.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 5: LW/Body >= 1.0 + Open->Low% <= -3.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 6: LW/Range >= 30% + Open->Low% <= -3.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 6: LW/Range >= 30% + Open->Low% <= -3.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 7: LW/Body >= 1.0 + Range% >= 2.0 + Open->Low% <= -3.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= 2.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_body_ratio"] >= 1.0 and s["range_percent"] >= 2.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 7: LW/Body >= 1.0 + Range% >= 2.0 + Open->Low% <= -3.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")
    print()
    
    # Combination 8: LW/Range >= 30% + Range% >= 2.0 + Open->Low% <= -3.0 + Volume >= 0.5
    filtered = [s for s in signals if s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= 2.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5]
    lost = [s for s in signals if not (s["lower_wick_range_ratio"] >= 0.30 and s["range_percent"] >= 2.0 and s["open_to_low_percent"] <= -3.0 and s["volume_ratio_prev"] >= 0.5)]
    print("Combination 8: LW/Range >= 30% + Range% >= 2.0 + Open->Low% <= -3.0 + Volume >= 0.5")
    print(f"  Coverage: {len(filtered)}/{len(signals)} ({len(filtered)/len(signals)*100:.1f}%)")
    print(f"  Lost: {len(lost)}")
    if lost:
        print(f"  Lost signals: {', '.join([s['symbol'] for s in lost])}")


def main():
    """Main analysis."""
    print("=" * 160)
    print("COMPREHENSIVE ANALYSIS OF 30 MANUAL SIGNALS (EXCLUDING FF-USDT)")
    print("=" * 160)
    print()
    
    # Load 30 signals
    signals = load_30_signals()
    print(f"Loaded {len(signals)} verified RED signals (excluding FF-USDT)")
    print()
    
    # Load DownMove% data
    down_move_data = load_down_move_data()
    
    # Merge data
    signals = merge_data(signals, down_move_data)
    print(f"Merged with DownMove% data: {len(signals)} signals")
    print()
    
    # Print statistics
    print_statistics(signals)
    
    # Analyze threshold coverage
    analyze_threshold_coverage(signals)
    
    # Test combinations
    test_combinations(signals)
    
    # Save results
    output = {
        "total_signals": len(signals),
        "signals": signals,
    }
    
    with open("30_signals_analysis.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Results saved to 30_signals_analysis.json")


if __name__ == "__main__":
    main()
