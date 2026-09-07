#!/usr/bin/env python3
"""
Analyze pullback/continuation patterns.

Research: Classify signals into 5 pattern variants and analyze performance.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def classify_pullback_pattern(signal):
    """Classify signal into pullback/continuation pattern variants."""
    if "comprehensive_features" not in signal:
        return "NO_FEATURES"
    
    cf = signal["comprehensive_features"]
    
    if "previous_movement" not in cf:
        return "NO_PM_DATA"
    
    pm = cf["previous_movement"]
    pm10 = pm.get("10_candles")
    pm20 = pm.get("20_candles")
    pm5 = pm.get("5_candles")
    growth_10 = pm.get("growth_10")
    was_growth_10 = pm.get("was_growth_10")
    
    # Variant A: Growth 10-20 candles + small pullback before signal (still positive)
    if pm20 is not None and pm10 is not None:
        if pm20 > 0 and pm10 > 0 and pm10 < pm20 * 0.8:
            return "VARIANT_A"
    
    # Variant B: Growth + strong pullback + signal (negative PM10)
    if pm20 is not None and pm10 is not None:
        if pm20 > 0 and pm10 < 0:
            return "VARIANT_B"
    
    # Variant C: Fall + signal (significant negative movement)
    if pm10 is not None and pm10 < -1.0:
        return "VARIANT_C"
    
    # Variant D: Sideways + signal (small movement)
    if pm10 is not None and abs(pm10) < 0.5:
        return "VARIANT_D"
    
    # Variant E: Breakout local high + pullback + signal
    if "range_positions" in cf:
        rp = cf["range_positions"]
        if rp.get("recent_high_breakout_20") and pm10 is not None and pm10 < 0:
            return "VARIANT_E"
    
    # Default based on growth context
    if was_growth_10:
        return "GROWTH_CONTEXT"
    elif was_growth_10 is False:
        return "FALL_CONTEXT"
    
    # Fallback based on PM10 sign
    if pm10 is not None:
        if pm10 >= 0:
            return "POSITIVE_PM10"
        else:
            return "NEGATIVE_PM10"
    
    return "UNKNOWN"


def analyze_pattern_performance(signals, pattern_name):
    """Analyze performance for a specific pattern."""
    pattern_signals = [s for s in signals if s.get("pullback_pattern") == pattern_name]
    
    if not pattern_signals:
        return None
    
    total = len(pattern_signals)
    fast = [s for s in pattern_signals if s.get("category") in ["VERY_FAST", "FAST"]]
    slow = [s for s in pattern_signals if s.get("category") == "SLOW"]
    sl_hit = [s for s in pattern_signals if s.get("category") == "SL_HIT"]
    no_reversal = [s for s in pattern_signals if s.get("category") == "NO_REVERSAL"]
    
    hit_tp_before_sl = [s for s in pattern_signals if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in pattern_signals if s["performance"].get("hit_sl_before_tp", False)]
    
    maes = [s["performance"]["max_adverse_before_2pct"] for s in pattern_signals if s["performance"]["max_adverse_before_2pct"] is not None]
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in pattern_signals if s["performance"]["time_to_2pct_candles"] is not None]
    
    return {
        "total": total,
        "fast_pct": len(fast) / total * 100,
        "slow_pct": len(slow) / total * 100,
        "sl_hit_pct": len(sl_hit) / total * 100,
        "no_reversal_pct": len(no_reversal) / total * 100,
        "tp_before_sl_pct": len(hit_tp_before_sl) / total * 100,
        "sl_before_tp_pct": len(hit_sl_before_tp) / total * 100,
        "avg_mae": mean(maes) if maes else None,
        "median_mae": median(maes) if maes else None,
        "avg_time_2pct": mean(times_2pct) if times_2pct else None,
        "median_time_2pct": median(times_2pct) if times_2pct else None
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("PULLBACK/CONTINUATION PATTERN ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load comprehensive data with performance
    with open("large_comprehensive.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    
    # Load performance data from previous analysis
    with open("diverse_performance.json", "r") as f:
        perf_data = json.load(f)
    
    # Merge performance data
    perf_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["performance"] for c in perf_data["candidates"]}
    
    for candidate in candidates:
        key = candidate["symbol"] + "_" + str(candidate["timestamp_ms"])
        if key in perf_map:
            candidate["performance"] = perf_map[key]
    
    # Load classification data
    with open("diverse_classified.json", "r") as f:
        class_data = json.load(f)
    
    # Merge classification data
    class_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["category"] for c in class_data["candidates"]}
    
    for candidate in candidates:
        key = candidate["symbol"] + "_" + str(candidate["timestamp_ms"])
        if key in class_map:
            candidate["category"] = class_map[key]
    
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Classify pullback patterns
    pattern_counts = {}
    for candidate in candidates:
        pattern = classify_pullback_pattern(candidate)
        candidate["pullback_pattern"] = pattern
        
        if pattern not in pattern_counts:
            pattern_counts[pattern] = 0
        pattern_counts[pattern] += 1
    
    print(f"\n{'=' * 100}")
    print("PATTERN DISTRIBUTION")
    print(f"{'=' * 100}")
    
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{pattern}: {count} ({count/len(candidates)*100:.1f}%)")
    
    # Analyze performance for each pattern
    print(f"\n{'=' * 100}")
    print("PATTERN PERFORMANCE ANALYSIS")
    print(f"{'=' * 100}")
    
    patterns = ["VARIANT_A", "VARIANT_B", "VARIANT_C", "VARIANT_D", "VARIANT_E", "GROWTH_CONTEXT", "FALL_CONTEXT", "UNKNOWN"]
    
    print(f"\n{'Pattern':<20} {'Total':>8} {'FAST%':>8} {'SL%':>8} {'TP%':>8} {'MAE':>8} {'Time+2%':>10}")
    print("-" * 80)
    
    for pattern in patterns:
        perf = analyze_pattern_performance(candidates, pattern)
        if perf:
            mae_str = f"{perf['avg_mae']:>7.2f}%" if perf['avg_mae'] is not None else "N/A"
            time_str = f"{perf['avg_time_2pct']:>9.1f}" if perf['avg_time_2pct'] is not None else "N/A"
            print(f"{pattern:<20} {perf['total']:>8} {perf['fast_pct']:>7.1f}% {perf['sl_hit_pct']:>7.1f}% {perf['tp_before_sl_pct']:>7.1f}% {mae_str:>10} {time_str:>10}")
    
    # Save results
    results = {
        "candidates": candidates,
        "pattern_counts": pattern_counts,
        "pattern_performance": {p: analyze_pattern_performance(candidates, p) for p in patterns}
    }
    
    with open("pullback_patterns.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to pullback_patterns.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
