#!/usr/bin/env python3
"""
Final analysis of large validation sample - UP direction hypothesis testing.

Research: Compare UP vs DOWN groups, test filters, generate comparison table.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def test_condition(signals, feature_path, threshold, operator):
    """Test a condition on deep features."""
    passed = []
    
    for s in signals:
        # Navigate to feature
        value = s
        for key in feature_path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        
        if value is None:
            continue
        
        if operator == ">=":
            if value >= threshold:
                passed.append(s)
        elif operator == "<=":
            if value <= threshold:
                passed.append(s)
        elif operator == ">":
            if value > threshold:
                passed.append(s)
        elif operator == "<":
            if value < threshold:
                passed.append(s)
        elif operator == "==":
            if value == threshold:
                passed.append(s)
    
    return passed


def evaluate_filter(passed_signals, all_signals):
    """Evaluate filter effectiveness with TP +3% / SL -3% model."""
    total = len(all_signals)
    
    hit_tp_before_sl = [s for s in passed_signals if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in passed_signals if s["performance"].get("hit_sl_before_tp", False)]
    hit_tp = [s for s in passed_signals if s["performance"].get("hit_tp_3pct", False)]
    hit_sl = [s for s in passed_signals if s["performance"].get("hit_sl_3pct", False)]
    
    # Calculate +2% before -3% rate
    reached_2pct_before_sl = 0
    total_passed = len(passed_signals)
    
    for s in passed_signals:
        if s["performance"]["time_to_2pct_candles"] is not None and not s["performance"]["hit_sl_3pct"]:
            reached_2pct_before_sl += 1
        elif s["performance"]["time_to_2pct_candles"] is not None and s["performance"]["hit_sl_3pct"]:
            if s["performance"]["time_to_2pct_candles"] < s["performance"]["candles_before_sl"]:
                reached_2pct_before_sl += 1
    
    # Calculate +3% before -3% rate
    reached_3pct_before_sl = 0
    
    for s in passed_signals:
        if s["performance"]["time_to_3pct_candles"] is not None and not s["performance"]["hit_sl_3pct"]:
            reached_3pct_before_sl += 1
        elif s["performance"]["time_to_3pct_candles"] is not None and s["performance"]["hit_sl_3pct"]:
            if s["performance"]["time_to_3pct_candles"] < s["performance"]["candles_before_sl"]:
                reached_3pct_before_sl += 1
    
    # Calculate MAE before +2% and +3%
    maes_2pct = [s["performance"]["max_adverse_before_2pct"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    maes_3pct = [s["performance"]["max_adverse_before_3pct"] for s in passed_signals if s["performance"]["time_to_3pct_candles"] is not None]
    
    # Calculate time to +2% and +3%
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    times_3pct = [s["performance"]["time_to_3pct_candles"] for s in passed_signals if s["performance"]["time_to_3pct_candles"] is not None]
    
    return {
        "total_signals": total,
        "passed_signals": len(passed_signals),
        "pass_rate": len(passed_signals) / total * 100 if total > 0 else 0,
        "hit_tp_before_sl": len(hit_tp_before_sl),
        "hit_sl_before_tp": len(hit_sl_before_tp),
        "hit_tp": len(hit_tp),
        "hit_sl": len(hit_sl),
        "reached_2pct_before_sl_pct": reached_2pct_before_sl / total_passed * 100 if total_passed > 0 else 0,
        "reached_3pct_before_sl_pct": reached_3pct_before_sl / total_passed * 100 if total_passed > 0 else 0,
        "hit_sl_pct": len(hit_sl) / total_passed * 100 if total_passed > 0 else 0,
        "avg_mae_before_2pct": mean(maes_2pct) if maes_2pct else None,
        "median_mae_before_2pct": median(maes_2pct) if maes_2pct else None,
        "avg_mae_before_3pct": mean(maes_3pct) if maes_3pct else None,
        "median_mae_before_3pct": median(maes_3pct) if maes_3pct else None,
        "avg_time_to_2pct": mean(times_2pct) if times_2pct else None,
        "median_time_to_2pct": median(times_2pct) if times_2pct else None,
        "avg_time_to_3pct": mean(times_3pct) if times_3pct else None,
        "median_time_to_3pct": median(times_3pct) if times_3pct else None
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("LARGE VALIDATION SAMPLE FINAL ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load complete data
    with open("large_validation_complete.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Group by short_term_direction
    print(f"\n{'=' * 100}")
    print("UP vs DOWN GROUP COMPARISON")
    print(f"{'=' * 100}")
    
    up_signals = []
    down_signals = []
    sideways_signals = []
    no_direction = []
    
    for c in candidates:
        if "deep_features" in c and "short_term_trend" in c["deep_features"]:
            direction = c["deep_features"]["short_term_trend"].get("short_term_direction")
            if direction == "UP":
                up_signals.append(c)
            elif direction == "DOWN":
                down_signals.append(c)
            elif direction == "SIDEWAYS":
                sideways_signals.append(c)
            else:
                no_direction.append(c)
        else:
            no_direction.append(c)
    
    print(f"\nUP: {len(up_signals)} signals ({len(up_signals)/len(candidates)*100:.1f}%)")
    print(f"DOWN: {len(down_signals)} signals ({len(down_signals)/len(candidates)*100:.1f}%)")
    print(f"SIDEWAYS: {len(sideways_signals)} signals ({len(sideways_signals)/len(candidates)*100:.1f}%)")
    print(f"NO DIRECTION: {len(no_direction)} signals ({len(no_direction)/len(candidates)*100:.1f}%)")
    
    # Evaluate UP group
    if up_signals:
        up_eval = evaluate_filter(up_signals, up_signals)
        print(f"\nUP Group Performance:")
        print(f"  +2% before -3%: {up_eval['reached_2pct_before_sl_pct']:.1f}%")
        print(f"  +3% before -3%: {up_eval['reached_3pct_before_sl_pct']:.1f}%")
        print(f"  SL -3%: {up_eval['hit_sl_pct']:.1f}%")
        if up_eval['avg_mae_before_2pct']:
            print(f"  Avg MAE before +2%: {up_eval['avg_mae_before_2pct']:.2f}%")
        if up_eval['avg_time_to_2pct']:
            print(f"  Avg time to +2%: {up_eval['avg_time_to_2pct']:.1f} candles")
        if up_eval['avg_time_to_3pct']:
            print(f"  Avg time to +3%: {up_eval['avg_time_to_3pct']:.1f} candles")
    
    # Evaluate DOWN group
    if down_signals:
        down_eval = evaluate_filter(down_signals, down_signals)
        print(f"\nDOWN Group Performance:")
        print(f"  +2% before -3%: {down_eval['reached_2pct_before_sl_pct']:.1f}%")
        print(f"  +3% before -3%: {down_eval['reached_3pct_before_sl_pct']:.1f}%")
        print(f"  SL -3%: {down_eval['hit_sl_pct']:.1f}%")
        if down_eval['avg_mae_before_2pct']:
            print(f"  Avg MAE before +2%: {down_eval['avg_mae_before_2pct']:.2f}%")
        if down_eval['avg_time_to_2pct']:
            print(f"  Avg time to +2%: {down_eval['avg_time_to_2pct']:.1f} candles")
        if down_eval['avg_time_to_3pct']:
            print(f"  Avg time to +3%: {down_eval['avg_time_to_3pct']:.1f} candles")
    
    # Test filters
    print(f"\n{'=' * 100}")
    print("FILTER TESTING")
    print(f"{'=' * 100}")
    
    results = []
    
    # 1. No filter (baseline)
    baseline = evaluate_filter(candidates, candidates)
    results.append(("No Filter", baseline))
    print(f"\n1. No Filter (Baseline)")
    print(f"  Pass Rate: {baseline['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {baseline['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {baseline['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {baseline['hit_sl_pct']:.1f}%")
    if baseline['avg_mae_before_2pct']:
        print(f"  Avg MAE: {baseline['avg_mae_before_2pct']:.2f}%")
    if baseline['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {baseline['avg_time_to_2pct']:.1f} candles")
    if baseline['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {baseline['avg_time_to_3pct']:.1f} candles")
    
    # 2. short_term_direction == UP
    up_passed = test_condition(candidates, ["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
    up_eval = evaluate_filter(up_passed, candidates)
    results.append(("short_term_direction == UP", up_eval))
    print(f"\n2. short_term_direction == UP")
    print(f"  Pass Rate: {up_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {up_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {up_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {up_eval['hit_sl_pct']:.1f}%")
    if up_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {up_eval['avg_mae_before_2pct']:.2f}%")
    if up_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {up_eval['avg_time_to_2pct']:.1f} candles")
    if up_eval['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {up_eval['avg_time_to_3pct']:.1f} candles")
    
    # 3. previous_movement_10 >= 0
    pm_passed = test_condition(candidates, ["deep_features", "short_term_trend", "10_candles"], 0.0, ">=")
    pm_eval = evaluate_filter(pm_passed, candidates)
    results.append(("previous_movement_10 >= 0", pm_eval))
    print(f"\n3. previous_movement_10 >= 0")
    print(f"  Pass Rate: {pm_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {pm_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {pm_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {pm_eval['hit_sl_pct']:.1f}%")
    if pm_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {pm_eval['avg_mae_before_2pct']:.2f}%")
    if pm_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {pm_eval['avg_time_to_2pct']:.1f} candles")
    if pm_eval['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {pm_eval['avg_time_to_3pct']:.1f} candles")
    
    # 4. short_term_direction == UP AND previous_movement_10 >= 0
    up_pm_passed = test_condition(up_passed, ["deep_features", "short_term_trend", "10_candles"], 0.0, ">=")
    up_pm_eval = evaluate_filter(up_pm_passed, candidates)
    results.append(("UP AND previous_movement_10 >= 0", up_pm_eval))
    print(f"\n4. UP AND previous_movement_10 >= 0")
    print(f"  Pass Rate: {up_pm_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {up_pm_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {up_pm_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {up_pm_eval['hit_sl_pct']:.1f}%")
    if up_pm_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {up_pm_eval['avg_mae_before_2pct']:.2f}%")
    if up_pm_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {up_pm_eval['avg_time_to_2pct']:.1f} candles")
    if up_pm_eval['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {up_pm_eval['avg_time_to_3pct']:.1f} candles")
    
    # 5. range_position_20 >= 0.5
    rp_passed = test_condition(candidates, ["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">=")
    rp_eval = evaluate_filter(rp_passed, candidates)
    results.append(("range_position_20 >= 0.5", rp_eval))
    print(f"\n5. range_position_20 >= 0.5")
    print(f"  Pass Rate: {rp_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {rp_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {rp_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {rp_eval['hit_sl_pct']:.1f}%")
    if rp_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {rp_eval['avg_mae_before_2pct']:.2f}%")
    if rp_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {rp_eval['avg_time_to_2pct']:.1f} candles")
    if rp_eval['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {rp_eval['avg_time_to_3pct']:.1f} candles")
    
    # 6. ema_21_slope >= 0
    ema_passed = test_condition(candidates, ["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
    ema_eval = evaluate_filter(ema_passed, candidates)
    results.append(("ema_21_slope >= 0", ema_eval))
    print(f"\n6. ema_21_slope >= 0")
    print(f"  Pass Rate: {ema_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {ema_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {ema_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {ema_eval['hit_sl_pct']:.1f}%")
    if ema_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {ema_eval['avg_mae_before_2pct']:.2f}%")
    if ema_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {ema_eval['avg_time_to_2pct']:.1f} candles")
    if ema_eval['avg_time_to_3pct']:
        print(f"  Avg time to +3%: {ema_eval['avg_time_to_3pct']:.1f} candles")
    
    # Print comparison table
    print(f"\n{'=' * 100}")
    print("FINAL COMPARISON TABLE")
    print(f"{'=' * 100}")
    print(f"\n{'Filter':<40} {'Pass Rate':>10} {'+2% before -3%':>15} {'+3% before -3%':>15} {'SL -3%':>10} {'Avg MAE':>10} {'Time +2%':>10} {'Time +3%':>10}")
    print("-" * 130)
    
    for name, eval_result in results:
        print(f"{name:<40} {eval_result['pass_rate']:>9.1f}% {eval_result['reached_2pct_before_sl_pct']:>14.1f}% {eval_result['reached_3pct_before_sl_pct']:>14.1f}% {eval_result['hit_sl_pct']:>9.1f}% {eval_result['avg_mae_before_2pct']:>9.2f}% {eval_result['avg_time_to_2pct']:>9.1f} {eval_result['avg_time_to_3pct']:>9.1f}")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")
    
    return results


if __name__ == "__main__":
    results = main()
