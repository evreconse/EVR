#!/usr/bin/env python3
"""
Test PM10 thresholds from -2% to +3%.

Research: Detailed PM10 threshold analysis to find optimal zone.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def analyze_pm10_threshold(signals, threshold):
    """Analyze performance for a specific PM10 threshold."""
    passed = [s for s in signals if s.get("comprehensive_features", {}).get("previous_movement", {}).get("10_candles", -999) >= threshold]
    
    if not passed:
        return None
    
    total = len(passed)
    fast = [s for s in passed if s.get("category") in ["VERY_FAST", "FAST"]]
    sl_hit = [s for s in passed if s.get("category") == "SL_HIT"]
    no_reversal = [s for s in passed if s.get("category") == "NO_REVERSAL"]
    
    hit_tp_before_sl = [s for s in passed if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in passed if s["performance"].get("hit_sl_before_tp", False)]
    
    maes = [s["performance"]["max_adverse_before_2pct"] for s in passed if s["performance"]["max_adverse_before_2pct"] is not None]
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in passed if s["performance"]["time_to_2pct_candles"] is not None]
    
    return {
        "threshold": threshold,
        "pass_rate": total / len(signals) * 100,
        "total": total,
        "fast_count": len(fast),
        "fast_pct": len(fast) / total * 100,
        "sl_hit_count": len(sl_hit),
        "sl_hit_pct": len(sl_hit) / total * 100,
        "no_reversal_count": len(no_reversal),
        "no_reversal_pct": len(no_reversal) / total * 100,
        "tp_before_sl_count": len(hit_tp_before_sl),
        "tp_before_sl_pct": len(hit_tp_before_sl) / total * 100,
        "sl_before_tp_count": len(hit_sl_before_tp),
        "sl_before_tp_pct": len(hit_sl_before_tp) / total * 100,
        "avg_mae": mean(maes) if maes else None,
        "median_mae": median(maes) if maes else None,
        "avg_time_2pct": mean(times_2pct) if times_2pct else None,
        "median_time_2pct": median(times_2pct) if times_2pct else None
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("PM10 THRESHOLD ANALYSIS (-2% to +3%)")
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
    
    # Test thresholds from -2% to +3% in 0.5% increments
    thresholds = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    print(f"\n{'=' * 100}")
    print("PM10 THRESHOLD RESULTS")
    print(f"{'=' * 100}")
    
    print(f"\n{'Threshold':>12} {'Pass%':>8} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8} {'MAE':>8} {'Time+2%':>10}")
    print("-" * 80)
    
    results = []
    for threshold in thresholds:
        perf = analyze_pm10_threshold(candidates, threshold)
        if perf:
            results.append(perf)
            pass_rate = f"{perf['pass_rate']:>7.1f}%"
            fast_pct = f"{perf['fast_pct']:>7.1f}%"
            sl_pct = f"{perf['sl_hit_pct']:>7.1f}%"
            tp_pct = f"{perf['tp_before_sl_pct']:>7.1f}%"
            mae_str = f"{perf['avg_mae']:>7.2f}%" if perf['avg_mae'] is not None else "N/A"
            time_str = f"{perf['avg_time_2pct']:>9.1f}" if perf['avg_time_2pct'] is not None else "N/A"
            print(f"{threshold:>10}% {pass_rate:>8} {perf['total']:>6} {fast_pct:>8} {sl_pct:>8} {tp_pct:>8} {mae_str:>8} {time_str:>10}")
    
    # Save results
    with open("pm10_threshold_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to pm10_threshold_results.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
