#!/usr/bin/env python3
"""
Test threshold variations for key patterns.

Research: Test various thresholds for the most promising features to find optimal values.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean


def test_deep_condition(signals, feature_path, threshold, operator):
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
    """Evaluate filter effectiveness."""
    total = len(all_signals)
    
    fast_signals = [s for s in all_signals if s["category"] in ["VERY_FAST", "FAST"]]
    sl_hit_signals = [s for s in all_signals if s["category"] == "SL_HIT"]
    
    passed_fast = [s for s in passed_signals if s["category"] in ["VERY_FAST", "FAST"]]
    passed_sl_hit = [s for s in passed_signals if s["category"] == "SL_HIT"]
    
    return {
        "total_signals": total,
        "passed_signals": len(passed_signals),
        "pass_rate": len(passed_signals) / total * 100 if total > 0 else 0,
        "fast_preserved": len(passed_fast),
        "fast_preserved_pct": len(passed_fast) / len(fast_signals) * 100 if fast_signals else 0,
        "sl_hit_reduced": len(sl_hit_signals) - len(passed_sl_hit),
        "sl_hit_remaining": len(passed_sl_hit),
        "sl_hit_reduction_pct": (len(sl_hit_signals) - len(passed_sl_hit)) / len(sl_hit_signals) * 100 if sl_hit_signals else 0,
        "sl_hit_in_passed": len(passed_sl_hit) / len(passed_signals) * 100 if passed_signals else 0
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("THRESHOLD VARIATIONS TESTING")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load analysis results
    with open("deep_features_analysis.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Group by category
    categories = {}
    for candidate in candidates:
        cat = candidate["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(candidate)
    
    fast_signals = categories.get("VERY_FAST", []) + categories.get("FAST", [])
    sl_hit_signals = categories.get("SL_HIT", [])
    
    print(f"FAST/VERY_FAST: {len(fast_signals)} signals")
    print(f"SL_HIT: {len(sl_hit_signals)} signals")
    
    # Test threshold variations for key features
    print(f"\n{'=' * 100}")
    print("THRESHOLD VARIATIONS")
    print(f"{'=' * 100}")
    
    # Feature 1: previous_movement_10 (short_term_trend)
    print(f"\n--- previous_movement_10 ---")
    for threshold in [-5.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 5.0]:
        passed = test_deep_condition(candidates, ["deep_features", "short_term_trend", "10_candles"], threshold, ">=")
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n>= {threshold}%:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 2: ema_21_slope
    print(f"\n--- ema_21_slope ---")
    for threshold in [-5.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 5.0]:
        passed = test_deep_condition(candidates, ["deep_features", "ema_sma", "ema_21_slope"], threshold, ">=")
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n>= {threshold}:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 3: range_position_20
    print(f"\n--- range_position_20 ---")
    for threshold in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        passed = test_deep_condition(candidates, ["deep_features", "distance_to_extremes", "range_position_20"], threshold, ">=")
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n>= {threshold}:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 4: current_range_percent
    print(f"\n--- current_range_percent ---")
    for threshold in [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]:
        passed = test_deep_condition(candidates, ["deep_features", "current_range_percent"], threshold, "<=")
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n<= {threshold}%:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 5: range_atr_ratio
    print(f"\n--- range_atr_ratio ---")
    for threshold in [0.5, 0.7, 0.9, 1.1, 1.3, 1.5]:
        passed = test_deep_condition(candidates, ["deep_features", "range_atr_ratio"], threshold, "<=")
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n<= {threshold}:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 6: short_term_direction == UP
    print(f"\n--- short_term_direction == UP ---")
    passed = test_deep_condition(candidates, ["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
    eval_result = evaluate_filter(passed, candidates)
    print(f"\nDirection == UP:")
    print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
    print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
    print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
    print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Feature 7: ema_alignment == True
    print(f"\n--- ema_alignment == True ---")
    passed = test_deep_condition(candidates, ["deep_features", "ema_sma", "ema_alignment"], True, "==")
    eval_result = evaluate_filter(passed, candidates)
    print(f"\nEMA alignment == True:")
    print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
    print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
    print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
    print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
