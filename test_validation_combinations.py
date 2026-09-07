#!/usr/bin/env python3
"""
Test combinations on validation sample.

Research: Test the three-factor combination and deeper combinations on validation sample.

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


def test_combination(signals, conditions):
    """Test a combination of conditions."""
    passed = signals
    
    for feature_path, threshold, operator in conditions:
        passed = test_condition(passed, feature_path, threshold, operator)
    
    return passed


def evaluate_filter(passed_signals, all_signals):
    """Evaluate filter effectiveness."""
    total = len(all_signals)
    
    very_fast_signals = [s for s in all_signals if s["category"] == "VERY_FAST"]
    slow_signals = [s for s in all_signals if s["category"] == "SLOW"]
    sl_hit_signals = [s for s in all_signals if s["category"] == "SL_HIT"]
    no_reversal = [s for s in all_signals if s["category"] == "NO_REVERSAL"]
    
    passed_very_fast = [s for s in passed_signals if s["category"] == "VERY_FAST"]
    passed_slow = [s for s in passed_signals if s["category"] == "SLOW"]
    passed_sl_hit = [s for s in passed_signals if s["category"] == "SL_HIT"]
    passed_no_reversal = [s for s in passed_signals if s["category"] == "NO_REVERSAL"]
    
    # Calculate +2% before -3% rate
    reached_2pct_before_sl = 0
    total_passed = len(passed_signals)
    
    for s in passed_signals:
        if s["performance"]["time_to_2pct_candles"] is not None and not s["performance"]["hit_sl_3pct"]:
            reached_2pct_before_sl += 1
        elif s["performance"]["time_to_2pct_candles"] is not None and s["performance"]["hit_sl_3pct"]:
            if s["performance"]["time_to_2pct_candles"] < s["performance"]["candles_before_sl"]:
                reached_2pct_before_sl += 1
    
    # Calculate MAE before +2%
    maes = [s["performance"]["max_adverse_before_2pct"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    
    # Calculate time to +2%
    times = [s["performance"]["time_to_2pct_candles"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    
    return {
        "total_signals": total,
        "passed_signals": len(passed_signals),
        "pass_rate": len(passed_signals) / total * 100 if total > 0 else 0,
        "very_fast_preserved": len(passed_very_fast),
        "very_fast_preserved_pct": len(passed_very_fast) / len(very_fast_signals) * 100 if very_fast_signals else 0,
        "slow_preserved": len(passed_slow),
        "slow_preserved_pct": len(passed_slow) / len(slow_signals) * 100 if slow_signals else 0,
        "sl_hit_reduced": len(sl_hit_signals) - len(passed_sl_hit),
        "sl_hit_remaining": len(passed_sl_hit),
        "sl_hit_reduction_pct": (len(sl_hit_signals) - len(passed_sl_hit)) / len(sl_hit_signals) * 100 if sl_hit_signals else 0,
        "no_reversal_reduced": len(no_reversal) - len(passed_no_reversal),
        "no_reversal_remaining": len(passed_no_reversal),
        "no_reversal_reduction_pct": (len(no_reversal) - len(passed_no_reversal)) / len(no_reversal) * 100 if no_reversal else 0,
        "reached_2pct_before_sl_pct": reached_2pct_before_sl / total_passed * 100 if total_passed > 0 else 0,
        "avg_mae_before_2pct": mean(maes) if maes else None,
        "median_mae_before_2pct": median(maes) if maes else None,
        "avg_time_to_2pct": mean(times) if times else None,
        "median_time_to_2pct": median(times) if times else None
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("VALIDATION SAMPLE COMBINATION TESTING")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load validation deep features
    with open("validation_deep_features.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Test the three-factor combination from original research
    print(f"\n{'=' * 100}")
    print("THREE-FACTOR COMBINATION (from original research)")
    print(f"{'=' * 100}")
    
    combination = [
        (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
        (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">="),
        (["deep_features", "current_range_percent"], 4.0, "<=")
    ]
    
    passed = test_combination(candidates, combination)
    eval_result = evaluate_filter(passed, candidates)
    
    print(f"\nprevious_movement_10 >= 0.0 AND range_position_20 >= 0.5 AND current_range_percent <= 4.0")
    print(f"Pass rate: {eval_result['pass_rate']:.1f}%")
    print(f"VERY_FAST preserved: {eval_result['very_fast_preserved_pct']:.1f}%")
    print(f"SLOW preserved: {eval_result['slow_preserved_pct']:.1f}%")
    print(f"SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
    print(f"NO_REVERSAL reduced: {eval_result['no_reversal_reduction_pct']:.1f}%")
    print(f"Reached +2% before -3%: {eval_result['reached_2pct_before_sl_pct']:.1f}%")
    if eval_result['avg_mae_before_2pct']:
        print(f"Avg MAE before +2%: {eval_result['avg_mae_before_2pct']:.2f}%")
        print(f"Median MAE before +2%: {eval_result['median_mae_before_2pct']:.2f}%")
    if eval_result['avg_time_to_2pct']:
        print(f"Avg time to +2%: {eval_result['avg_time_to_2pct']:.1f} candles")
        print(f"Median time to +2%: {eval_result['median_time_to_2pct']:.1f} candles")
    
    # Test deeper combinations
    print(f"\n{'=' * 100}")
    print("DEEPER COMBINATIONS")
    print(f"{'=' * 100}")
    
    combinations = [
        # Trend + EMA slope
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
        ],
        
        # Trend + short_term_direction
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
        ],
        
        # Trend + range position (without range size)
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">=")
        ],
        
        # Short-term direction only (best individual result)
        [
            (["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
        ],
        
        # EMA slope only
        [
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
        ],
        
        # Price above EMA only
        [
            (["deep_features", "ema_sma", "price_above_ema_21"], True, "==")
        ],
        
        # Trend + EMA slope + range position
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">=")
        ],
        
        # Trend + short_term_direction + range position
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "short_term_trend", "short_term_direction"], "UP", "=="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">=")
        ],
    ]
    
    for i, combo in enumerate(combinations, 1):
        passed = test_combination(candidates, combo)
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\nCombination {i}:")
        for feature_path, threshold, operator in combo:
            feature_name = " -> ".join(feature_path)
            print(f"  {feature_name} {operator} {threshold}")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  VERY_FAST preserved: {eval_result['very_fast_preserved_pct']:.1f}%")
        print(f"  SLOW preserved: {eval_result['slow_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  NO_REVERSAL reduced: {eval_result['no_reversal_reduction_pct']:.1f}%")
        print(f"  Reached +2% before -3%: {eval_result['reached_2pct_before_sl_pct']:.1f}%")
        if eval_result['avg_mae_before_2pct']:
            print(f"  Avg MAE before +2%: {eval_result['avg_mae_before_2pct']:.2f}%")
        if eval_result['avg_time_to_2pct']:
            print(f"  Avg time to +2%: {eval_result['avg_time_to_2pct']:.1f} candles")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
