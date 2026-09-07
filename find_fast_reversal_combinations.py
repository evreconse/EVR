#!/usr/bin/env python3
"""
Find combinations that distinguish FAST from SL_HIT signals.

Research: Test various combinations of conditions to find filters that
reduce SL_HIT rate while preserving FAST signals.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean


def test_condition(signals, metric, threshold, operator):
    """Test a single condition on signals."""
    passed = []
    for s in signals:
        value = None
        
        # Get value from appropriate source
        if metric in s.get("formula_details", {}):
            value = s["formula_details"][metric]
        elif metric == "lower_wick_body_ratio" and metric in s:
            value = s[metric]
        elif metric == "lower_wick_range_ratio" and metric in s:
            value = s[metric]
        elif metric == "volume_ratio" and metric in s:
            value = s[metric]
        elif metric == "range_position_10" and "pre_signal_context" in s:
            value = s["pre_signal_context"].get("range_position", {}).get("10_candles")
        elif metric == "previous_movement_10" and "pre_signal_context" in s:
            value = s["pre_signal_context"].get("previous_movement", {}).get("10_candles")
        
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
    
    return passed


def test_combination(signals, conditions):
    """Test a combination of conditions on signals."""
    passed = []
    
    for s in signals:
        all_pass = True
        
        for metric, threshold, operator in conditions:
            value = None
            
            if metric in s.get("formula_details", {}):
                value = s["formula_details"][metric]
            elif metric == "lower_wick_body_ratio" and metric in s:
                value = s[metric]
            elif metric == "lower_wick_range_ratio" and metric in s:
                value = s[metric]
            elif metric == "volume_ratio" and metric in s:
                value = s[metric]
            elif metric == "range_position_10" and "pre_signal_context" in s:
                value = s["pre_signal_context"].get("range_position", {}).get("10_candles")
            elif metric == "previous_movement_10" and "pre_signal_context" in s:
                value = s["pre_signal_context"].get("previous_movement", {}).get("10_candles")
            
            if value is None:
                all_pass = False
                break
            
            if operator == ">=":
                if value < threshold:
                    all_pass = False
                    break
            elif operator == "<=":
                if value > threshold:
                    all_pass = False
                    break
            elif operator == ">":
                if value <= threshold:
                    all_pass = False
                    break
            elif operator == "<":
                if value >= threshold:
                    all_pass = False
                    break
        
        if all_pass:
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
    print("FINDING FAST REVERSAL COMBINATIONS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load analysis results
    with open("large_sample_context_analysis.json", "r") as f:
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
    
    # Test individual conditions based on our findings
    print(f"\n{'=' * 100}")
    print("INDIVIDUAL CONDITION TESTS")
    print(f"{'=' * 100}")
    
    # Based on findings: FAST signals have higher range position and previous movement
    conditions_to_test = [
        ("range_position_10", 0.5, ">="),  # FAST at 60.6%, SL_HIT at 42.1%
        ("range_position_10", 0.6, ">="),
        ("range_position_10", 0.7, ">="),
        ("previous_movement_10", 0.0, ">="),  # FAST at +2.61%, SL_HIT at -2.80%
        ("previous_movement_10", 1.0, ">="),
        ("previous_movement_10", 2.0, ">="),
        ("volume_ratio", 1.2, "<="),  # FAST at 1.08x, SL_HIT at 1.49x
        ("volume_ratio", 1.3, "<="),
        ("range_percent", 4.0, "<="),  # FAST at 3.75%, SL_HIT at 5.49%
        ("range_percent", 5.0, "<="),
        ("open_to_low_percent", -3.5, ">="),  # FAST at -3.45%, SL_HIT at -4.72%
        ("open_to_low_percent", -4.0, ">="),
    ]
    
    for metric, threshold, operator in conditions_to_test:
        passed = test_condition(candidates, metric, threshold, operator)
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\n{metric} {operator} {threshold}:")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved']}/{len(fast_signals)} ({eval_result['fast_preserved_pct']:.1f}%)")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduced']}/{len(sl_hit_signals)} ({eval_result['sl_hit_reduction_pct']:.1f}%)")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
    
    # Test combinations
    print(f"\n{'=' * 100}")
    print("COMBINATION TESTS")
    print(f"{'=' * 100}")
    
    # Based on findings: FAST = high range position + positive previous movement + lower volume
    combinations = [
        # Rising + middle-top of range
        [("previous_movement_10", 0.0, ">="), ("range_position_10", 0.5, ">=")],
        [("previous_movement_10", 1.0, ">="), ("range_position_10", 0.5, ">=")],
        [("previous_movement_10", 0.0, ">="), ("range_position_10", 0.6, ">=")],
        
        # Rising + lower volume
        [("previous_movement_10", 0.0, ">="), ("volume_ratio", 1.2, "<=")],
        [("previous_movement_10", 1.0, ">="), ("volume_ratio", 1.2, "<=")],
        
        # Middle-top of range + lower volume
        [("range_position_10", 0.5, ">="), ("volume_ratio", 1.2, "<=")],
        [("range_position_10", 0.6, ">="), ("volume_ratio", 1.2, "<=")],
        
        # Three-factor combinations
        [("previous_movement_10", 0.0, ">="), ("range_position_10", 0.5, ">="), ("volume_ratio", 1.2, "<=")],
        [("previous_movement_10", 1.0, ">="), ("range_position_10", 0.5, ">="), ("volume_ratio", 1.3, "<=")],
        
        # Conservative (smaller candles)
        [("range_percent", 4.0, "<="), ("previous_movement_10", 0.0, ">=")],
        [("range_percent", 5.0, "<="), ("previous_movement_10", 0.0, ">="), ("range_position_10", 0.5, ">=")],
    ]
    
    for i, conditions in enumerate(combinations, 1):
        passed = test_combination(candidates, conditions)
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\nCombination {i}:")
        for metric, threshold, operator in conditions:
            print(f"  {metric} {operator} {threshold}")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved']}/{len(fast_signals)} ({eval_result['fast_preserved_pct']:.1f}%)")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduced']}/{len(sl_hit_signals)} ({eval_result['sl_hit_reduction_pct']:.1f}%)")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
        
        if eval_result['fast_preserved_pct'] > 50 and eval_result['sl_hit_reduction_pct'] > 50:
            print(f"  *** GOOD BALANCE ***")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
