#!/usr/bin/env python3
"""
Test multi-feature combinations.

Research: Test combinations of the most promising features to find optimal filters.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json


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


def test_combination(signals, conditions):
    """Test a combination of conditions."""
    passed = signals
    
    for feature_path, threshold, operator in conditions:
        passed = test_deep_condition(passed, feature_path, threshold, operator)
    
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
    print("MULTI-FEATURE COMBINATION TESTING")
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
    
    # Test combinations
    print(f"\n{'=' * 100}")
    print("COMBINATION TESTS")
    print(f"{'=' * 100}")
    
    # Based on threshold variations, test promising combinations
    combinations = [
        # Trend-based combinations
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 1.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
        ],
        [
            (["deep_features", "short_term_trend", "short_term_direction"], "UP", "=="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">=")
        ],
        
        # Range + trend combinations
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.6, ">=")
        ],
        
        # Volatility + trend combinations
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "current_range_percent"], 4.0, "<=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "range_atr_ratio"], 1.1, "<=")
        ],
        
        # Three-factor combinations
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">="),
            (["deep_features", "current_range_percent"], 4.0, "<=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.5, ">="),
            (["deep_features", "current_range_percent"], 4.0, "<=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 1.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">="),
            (["deep_features", "current_range_percent"], 4.0, "<=")
        ],
        
        # Conservative (high FAST preservation)
        [
            (["deep_features", "current_range_percent"], 4.0, "<="),
            (["deep_features", "short_term_trend", "10_candles"], -2.0, ">=")
        ],
        [
            (["deep_features", "current_range_percent"], 5.0, "<="),
            (["deep_features", "short_term_trend", "10_candles"], -1.0, ">=")
        ],
        
        # Aggressive (high SL_HIT reduction)
        [
            (["deep_features", "short_term_trend", "short_term_direction"], "UP", "=="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.6, ">=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 1.0, ">="),
            (["deep_features", "distance_to_extremes", "range_position_20"], 0.6, ">=")
        ],
        
        # Including volume_ratio from previous analysis
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["volume_ratio"], 1.2, "<=")
        ],
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">="),
            (["volume_ratio"], 1.2, "<=")
        ],
        
        # Four-factor combinations
        [
            (["deep_features", "short_term_trend", "10_candles"], 0.0, ">="),
            (["deep_features", "ema_sma", "ema_21_slope"], 0.0, ">="),
            (["deep_features", "current_range_percent"], 4.0, "<="),
            (["volume_ratio"], 1.2, "<=")
        ],
    ]
    
    for i, conditions in enumerate(combinations, 1):
        passed = test_combination(candidates, conditions)
        eval_result = evaluate_filter(passed, candidates)
        
        print(f"\nCombination {i}:")
        for feature_path, threshold, operator in conditions:
            feature_name = " -> ".join(feature_path)
            print(f"  {feature_name} {operator} {threshold}")
        print(f"  Pass rate: {eval_result['pass_rate']:.1f}%")
        print(f"  FAST preserved: {eval_result['fast_preserved_pct']:.1f}%")
        print(f"  SL_HIT reduced: {eval_result['sl_hit_reduction_pct']:.1f}%")
        print(f"  SL_HIT in passed: {eval_result['sl_hit_in_passed']:.1f}%")
        
        if eval_result['fast_preserved_pct'] > 50 and eval_result['sl_hit_reduction_pct'] > 50:
            print(f"  *** GOOD BALANCE ***")
        if eval_result['fast_preserved_pct'] > 70 and eval_result['sl_hit_reduction_pct'] > 40:
            print(f"  *** HIGH FAST PRESERVATION ***")
        if eval_result['sl_hit_reduction_pct'] > 70 and eval_result['fast_preserved_pct'] > 40:
            print(f"  *** HIGH SL_HIT REDUCTION ***")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
