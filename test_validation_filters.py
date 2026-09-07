#!/usr/bin/env python3
"""
Test all validation filters and analyze per-coin stability.

Research: Test 5 filter variants, calculate per-coin metrics, variance, confidence intervals.

DO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median, stdev
from math import sqrt


def passes_filter(signal, filter_type):
    """Check if signal passes a specific filter."""
    features = signal.get("features", {})
    
    if filter_type == "baseline":
        return True
    
    elif filter_type == "pm10_ge_0":
        pm10 = features.get("previous_movement_10")
        return pm10 is not None and pm10 >= 0
    
    elif filter_type == "pm10_ge_05":
        pm10 = features.get("previous_movement_10")
        return pm10 is not None and pm10 >= 0.5
    
    elif filter_type == "pm10_ge_0_and_1h_down":
        pm10 = features.get("previous_movement_10")
        h1_direction = features.get("1h_direction")
        return pm10 is not None and pm10 >= 0 and h1_direction == "DOWN"
    
    elif filter_type == "pm10_ge_05_and_1h_down":
        pm10 = features.get("previous_movement_10")
        h1_direction = features.get("1h_direction")
        return pm10 is not None and pm10 >= 0.5 and h1_direction == "DOWN"
    
    return False


def calculate_filter_metrics(signals):
    """Calculate metrics for a set of signals."""
    if not signals:
        return None
    
    total = len(signals)
    fast = [s for s in signals if s.get("category") in ["VERY_FAST", "FAST"]]
    slow = [s for s in signals if s.get("category") == "SLOW"]
    sl_hit = [s for s in signals if s.get("category") == "SL_HIT"]
    no_reversal = [s for s in signals if s.get("category") == "NO_REVERSAL"]
    
    hit_tp_before_sl = [s for s in signals if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in signals if s["performance"].get("hit_sl_before_tp", False)]
    
    maes = [s["performance"]["max_adverse_before_2pct"] for s in signals if s["performance"].get("max_adverse_before_2pct") is not None]
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in signals if s["performance"].get("time_to_2pct_candles") is not None]
    times_3pct = [s["performance"]["time_to_3pct_candles"] for s in signals if s["performance"].get("time_to_3pct_candles") is not None]
    
    return {
        "total": total,
        "fast_count": len(fast),
        "fast_pct": len(fast) / total * 100,
        "slow_count": len(slow),
        "slow_pct": len(slow) / total * 100,
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
        "median_time_2pct": median(times_2pct) if times_2pct else None,
        "avg_time_3pct": mean(times_3pct) if times_3pct else None,
        "median_time_3pct": median(times_3pct) if times_3pct else None
    }


def calculate_per_coin_metrics(signals, filter_type):
    """Calculate metrics per coin."""
    coins = {}
    
    for signal in signals:
        if passes_filter(signal, filter_type):
            symbol = signal["symbol"]
            if symbol not in coins:
                coins[symbol] = []
            coins[symbol].append(signal)
    
    per_coin = {}
    for symbol, coin_signals in coins.items():
        metrics = calculate_filter_metrics(coin_signals)
        if metrics:
            per_coin[symbol] = metrics
    
    return per_coin


def calculate_confidence_interval(values, confidence=0.95):
    """Calculate confidence interval for a list of values."""
    if len(values) < 2:
        return None
    
    n = len(values)
    mean_val = mean(values)
    std_val = stdev(values) if len(values) > 1 else 0
    
    # Approximate 95% CI using t-distribution
    from math import sqrt
    margin_of_error = 1.96 * (std_val / sqrt(n))
    
    return {
        "mean": mean_val,
        "std": std_val,
        "margin_of_error": margin_of_error,
        "lower": mean_val - margin_of_error,
        "upper": mean_val + margin_of_error,
        "n": n
    }


def calculate_variance_analysis(signals, filter_type):
    """Calculate variance between coin groups."""
    # Split coins into two groups (odd/even based on sorted symbol names)
    filtered_signals = [s for s in signals if passes_filter(s, filter_type)]
    
    if not filtered_signals:
        return None
    
    symbols = sorted(set(s["symbol"] for s in filtered_signals))
    group_a_symbols = symbols[::2]
    group_b_symbols = symbols[1::2]
    
    group_a = [s for s in filtered_signals if s["symbol"] in group_a_symbols]
    group_b = [s for s in filtered_signals if s["symbol"] in group_b_symbols]
    
    metrics_a = calculate_filter_metrics(group_a)
    metrics_b = calculate_filter_metrics(group_b)
    
    if not metrics_a or not metrics_b:
        return None
    
    variance = {
        "group_a_symbols": group_a_symbols,
        "group_b_symbols": group_b_symbols,
        "group_a": metrics_a,
        "group_b": metrics_b,
        "fast_pct_diff": abs(metrics_a["fast_pct"] - metrics_b["fast_pct"]),
        "sl_hit_pct_diff": abs(metrics_a["sl_hit_pct"] - metrics_b["sl_hit_pct"]),
        "tp_before_sl_pct_diff": abs(metrics_a["tp_before_sl_pct"] - metrics_b["tp_before_sl_pct"])
    }
    
    return variance


def main():
    """Main analysis function."""
    print("=" * 100)
    print("TESTING VALIDATION FILTERS")
    print("=" * 100)
    print("\nDO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load validation data
    with open("validation_with_performance.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Test all filters
    filters = ["baseline", "pm10_ge_0", "pm10_ge_05", "pm10_ge_0_and_1h_down", "pm10_ge_05_and_1h_down"]
    
    print(f"\n{'=' * 100}")
    print("OVERALL FILTER METRICS")
    print(f"{'=' * 100}")
    
    print(f"\n{'Filter':<30} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8} {'MAE':>8} {'Time+2%':>10}")
    print("-" * 90)
    
    results = {}
    for filter_type in filters:
        filtered = [s for s in candidates if passes_filter(s, filter_type)]
        metrics = calculate_filter_metrics(filtered)
        
        if metrics:
            results[filter_type] = {
                "overall": metrics,
                "per_coin": calculate_per_coin_metrics(candidates, filter_type),
                "variance": calculate_variance_analysis(candidates, filter_type)
            }
            
            pass_rate = f"{metrics['total']}/{len(candidates)}"
            fast_pct = f"{metrics['fast_pct']:>7.1f}%"
            sl_pct = f"{metrics['sl_hit_pct']:>7.1f}%"
            tp_pct = f"{metrics['tp_before_sl_pct']:>7.1f}%"
            mae_str = f"{metrics['avg_mae']:>7.2f}%" if metrics['avg_mae'] is not None else "N/A"
            time_str = f"{metrics['avg_time_2pct']:>9.1f}" if metrics['avg_time_2pct'] is not None else "N/A"
            
            print(f"{filter_type:<30} {pass_rate:>6} {fast_pct:>8} {sl_pct:>8} {tp_pct:>8} {mae_str:>8} {time_str:>10}")
    
    # Per-coin analysis
    print(f"\n{'=' * 100}")
    print("PER-COIN ANALYSIS (PM10 >= 0.5%)")
    print(f"{'=' * 100}")
    
    per_coin = results["pm10_ge_05"]["per_coin"]
    print(f"\n{'Symbol':<20} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8} {'MAE':>8}")
    print("-" * 70)
    
    for symbol, metrics in sorted(per_coin.items()):
        fast_pct = f"{metrics['fast_pct']:>7.1f}%"
        sl_pct = f"{metrics['sl_hit_pct']:>7.1f}%"
        tp_pct = f"{metrics['tp_before_sl_pct']:>7.1f}%"
        mae_str = f"{metrics['avg_mae']:>7.2f}%" if metrics['avg_mae'] is not None else "N/A"
        print(f"{symbol:<20} {metrics['total']:>6} {fast_pct:>8} {sl_pct:>8} {tp_pct:>8} {mae_str:>8}")
    
    # Variance analysis
    print(f"\n{'=' * 100}")
    print("VARIANCE ANALYSIS")
    print(f"{'=' * 100}")
    
    for filter_type in filters:
        variance = results[filter_type]["variance"]
        if variance:
            print(f"\n{filter_type}:")
            print(f"  Group A ({len(variance['group_a_symbols'])} symbols): FAST={variance['group_a']['fast_pct']:.1f}%, SL={variance['group_a']['sl_hit_pct']:.1f}%, TP={variance['group_a']['tp_before_sl_pct']:.1f}%")
            print(f"  Group B ({len(variance['group_b_symbols'])} symbols): FAST={variance['group_b']['fast_pct']:.1f}%, SL={variance['group_b']['sl_hit_pct']:.1f}%, TP={variance['group_b']['tp_before_sl_pct']:.1f}%")
            print(f"  Variance: FAST={variance['fast_pct_diff']:.1f}pp, SL={variance['sl_hit_pct_diff']:.1f}pp, TP={variance['tp_before_sl_pct_diff']:.1f}pp")
    
    # Save results
    with open("validation_filter_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to validation_filter_results.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
