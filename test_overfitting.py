#!/usr/bin/env python3
"""
Test overfitting by testing filters on different subsamples.

Research: Split data by symbol to test if filters work across different coins.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean


def analyze_filter_on_signals(signals, filter_def):
    """Analyze filter performance on a signal set."""
    passed = [s for s in signals if s.get("comprehensive_features", {}).get("previous_movement", {}).get("10_candles", -999) >= filter_def.get("pm10_threshold", -999)]
    
    if not passed:
        return None
    
    total = len(passed)
    fast = [s for s in passed if s.get("category") in ["VERY_FAST", "FAST"]]
    sl_hit = [s for s in passed if s.get("category") == "SL_HIT"]
    
    hit_tp_before_sl = [s for s in passed if s["performance"].get("hit_tp_before_sl", False)]
    
    return {
        "total": total,
        "fast_pct": len(fast) / total * 100,
        "sl_hit_pct": len(sl_hit) / total * 100,
        "tp_before_sl_pct": len(hit_tp_before_sl) / total * 100
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("OVERFITTING TEST: SUBSAMPLE ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load comprehensive data
    with open("large_with_ht.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    
    # Load performance and classification data
    with open("diverse_performance.json", "r") as f:
        perf_data = json.load(f)
    
    with open("diverse_classified.json", "r") as f:
        class_data = json.load(f)
    
    # Merge data
    perf_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["performance"] for c in perf_data["candidates"]}
    class_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["category"] for c in class_data["candidates"]}
    
    for candidate in candidates:
        key = candidate["symbol"] + "_" + str(candidate["timestamp_ms"])
        if key in perf_map:
            candidate["performance"] = perf_map[key]
        if key in class_map:
            candidate["category"] = class_map[key]
    
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Get unique symbols
    symbols = list(set(c["symbol"] for c in candidates))
    print(f"Unique symbols: {len(symbols)}")
    
    # Split into two subsamples by symbol (odd/even index)
    symbols_a = symbols[::2]
    symbols_b = symbols[1::2]
    
    sample_a = [c for c in candidates if c["symbol"] in symbols_a]
    sample_b = [c for c in candidates if c["symbol"] in symbols_b]
    
    print(f"\nSample A (symbols: {len(symbols_a)}): {len(sample_a)} signals")
    print(f"Sample B (symbols: {len(symbols_b)}): {len(sample_b)} signals")
    
    # Test PM10 >= 0 on both samples
    filter_def = {"pm10_threshold": 0}
    
    print(f"\n{'=' * 100}")
    print("PM10 >= 0 FILTER ON SUBSAMPLES")
    print(f"{'=' * 100}")
    
    perf_a = analyze_filter_on_signals(sample_a, filter_def)
    perf_b = analyze_filter_on_signals(sample_b, filter_def)
    perf_all = analyze_filter_on_signals(candidates, filter_def)
    
    print(f"\n{'Sample':<15} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8}")
    print("-" * 50)
    
    if perf_a:
        print(f"{'Sample A':<15} {perf_a['total']:>6} {perf_a['fast_pct']:>7.1f}% {perf_a['sl_hit_pct']:>7.1f}% {perf_a['tp_before_sl_pct']:>7.1f}%")
    if perf_b:
        print(f"{'Sample B':<15} {perf_b['total']:>6} {perf_b['fast_pct']:>7.1f}% {perf_b['sl_hit_pct']:>7.1f}% {perf_b['tp_before_sl_pct']:>7.1f}%")
    if perf_all:
        print(f"{'All':<15} {perf_all['total']:>6} {perf_all['fast_pct']:>7.1f}% {perf_all['sl_hit_pct']:>7.1f}% {perf_all['tp_before_sl_pct']:>7.1f}%")
    
    # Test PM10 >= 0.5 on both samples
    filter_def_05 = {"pm10_threshold": 0.5}
    
    print(f"\n{'=' * 100}")
    print("PM10 >= 0.5% FILTER ON SUBSAMPLES")
    print(f"{'=' * 100}")
    
    perf_a_05 = analyze_filter_on_signals(sample_a, filter_def_05)
    perf_b_05 = analyze_filter_on_signals(sample_b, filter_def_05)
    perf_all_05 = analyze_filter_on_signals(candidates, filter_def_05)
    
    print(f"\n{'Sample':<15} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8}")
    print("-" * 50)
    
    if perf_a_05:
        print(f"{'Sample A':<15} {perf_a_05['total']:>6} {perf_a_05['fast_pct']:>7.1f}% {perf_a_05['sl_hit_pct']:>7.1f}% {perf_a_05['tp_before_sl_pct']:>7.1f}%")
    if perf_b_05:
        print(f"{'Sample B':<15} {perf_b_05['total']:>6} {perf_b_05['fast_pct']:>7.1f}% {perf_b_05['sl_hit_pct']:>7.1f}% {perf_b_05['tp_before_sl_pct']:>7.1f}%")
    if perf_all_05:
        print(f"{'All':<15} {perf_all_05['total']:>6} {perf_all_05['fast_pct']:>7.1f}% {perf_all_05['sl_hit_pct']:>7.1f}% {perf_all_05['tp_before_sl_pct']:>7.1f}%")
    
    # Calculate stability
    print(f"\n{'=' * 100}")
    print("STABILITY ANALYSIS")
    print(f"{'=' * 100}")
    
    if perf_a and perf_b:
        fast_diff = abs(perf_a['fast_pct'] - perf_b['fast_pct'])
        sl_diff = abs(perf_a['sl_hit_pct'] - perf_b['sl_hit_pct'])
        tp_diff = abs(perf_a['tp_before_sl_pct'] - perf_b['tp_before_sl_pct'])
        
        print(f"\nPM10 >= 0 stability:")
        print(f"  FAST% difference: {fast_diff:.1f} pp")
        print(f"  SL% difference: {sl_diff:.1f} pp")
        print(f"  TP% difference: {tp_diff:.1f} pp")
        
        if fast_diff < 20 and sl_diff < 20 and tp_diff < 20:
            print(f"  Verdict: STABLE (differences < 20 pp)")
        else:
            print(f"  Verdict: UNSTABLE (high variance between samples)")
    
    if perf_a_05 and perf_b_05:
        fast_diff_05 = abs(perf_a_05['fast_pct'] - perf_b_05['fast_pct'])
        sl_diff_05 = abs(perf_a_05['sl_hit_pct'] - perf_b_05['sl_hit_pct'])
        tp_diff_05 = abs(perf_a_05['tp_before_sl_pct'] - perf_b_05['tp_before_sl_pct'])
        
        print(f"\nPM10 >= 0.5% stability:")
        print(f"  FAST% difference: {fast_diff_05:.1f} pp")
        print(f"  SL% difference: {sl_diff_05:.1f} pp")
        print(f"  TP% difference: {tp_diff_05:.1f} pp")
        
        if fast_diff_05 < 20 and sl_diff_05 < 20 and tp_diff_05 < 20:
            print(f"  Verdict: STABLE (differences < 20 pp)")
        else:
            print(f"  Verdict: UNSTABLE (high variance between samples)")
    
    # Save results
    results = {
        "sample_a_symbols": symbols_a,
        "sample_b_symbols": symbols_b,
        "pm10_0": {"sample_a": perf_a, "sample_b": perf_b, "all": perf_all},
        "pm10_05": {"sample_a": perf_a_05, "sample_b": perf_b_05, "all": perf_all_05}
    }
    
    with open("overfitting_test.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to overfitting_test.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
