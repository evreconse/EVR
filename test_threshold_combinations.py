#!/usr/bin/env python3
"""
Test threshold combinations to find filters that reduce SL-hit signals.

Research: Test various threshold combinations on control signals to find
conditions that would filter out SL-hit signals while preserving good signals.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean


def test_threshold(signals, metric, threshold, operator=">="):
    """Test a single threshold on signals."""
    passed = []
    failed = []
    
    for signal in signals:
        value = signal.get(metric)
        if value is None:
            continue
        
        if operator == ">=":
            if value >= threshold:
                passed.append(signal)
            else:
                failed.append(signal)
        elif operator == "<=":
            if value <= threshold:
                passed.append(signal)
            else:
                failed.append(signal)
    
    return passed, failed


def evaluate_combination(signals, conditions):
    """Evaluate a combination of conditions on signals."""
    passed = []
    failed = []
    
    for signal in signals:
        all_pass = True
        
        for metric, threshold, operator in conditions:
            value = signal.get(metric)
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
        
        if all_pass:
            passed.append(signal)
        else:
            failed.append(signal)
    
    return passed, failed


def analyze_filter_effectiveness(passed_signals, all_signals):
    """Analyze how effective a filter is at reducing SL-hit signals."""
    sl_hit_count = sum(1 for s in all_signals if s.get("sl_risk_category") == "SL_HIT")
    high_risk_count = sum(1 for s in all_signals if s.get("sl_risk_category") == "HIGH_RISK")
    
    passed_sl_hit = sum(1 for s in passed_signals if s.get("sl_risk_category") == "SL_HIT")
    passed_high_risk = sum(1 for s in passed_signals if s.get("sl_risk_category") == "HIGH_RISK")
    passed_good = sum(1 for s in passed_signals if s.get("sl_risk_category") in ["LOW_RISK", "MODERATE_RISK"])
    
    return {
        "total_signals": len(all_signals),
        "passed_signals": len(passed_signals),
        "sl_hit_reduced": sl_hit_count - passed_sl_hit,
        "sl_hit_remaining": passed_sl_hit,
        "high_risk_reduced": high_risk_count - passed_high_risk,
        "high_risk_remaining": passed_high_risk,
        "good_signals_preserved": passed_good,
        "sl_hit_reduction_pct": (sl_hit_count - passed_sl_hit) / sl_hit_count * 100 if sl_hit_count > 0 else 0
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("THRESHOLD COMBINATION TESTING")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load analysis results
    with open("fast_reversal_factors_analysis.json", "r") as f:
        data = json.load(f)
    
    signals = data["control_signals"]
    print(f"\nLoaded {len(signals)} signals")
    
    # Count by category
    sl_hit = [s for s in signals if s.get("sl_risk_category") == "SL_HIT"]
    high_risk = [s for s in signals if s.get("sl_risk_category") == "HIGH_RISK"]
    no_reversal = [s for s in signals if s.get("sl_risk_category") == "NO_REVERSAL"]
    
    print(f"\nCurrent distribution:")
    print(f"  SL_HIT: {len(sl_hit)}")
    print(f"  HIGH_RISK: {len(high_risk)}")
    print(f"  NO_REVERSAL: {len(no_reversal)}")
    
    # Test individual thresholds
    print(f"\n{'=' * 100}")
    print("INDIVIDUAL THRESHOLD TESTS")
    print(f"{'=' * 100}")
    
    thresholds_to_test = [
        ("range_percent", 5.0, ">="),
        ("range_percent", 4.0, ">="),
        ("lower_wick_body_ratio", 2.0, ">="),
        ("lower_wick_body_ratio", 1.5, ">="),
        ("lower_wick_range_ratio", 0.60, ">="),
        ("open_to_low_percent", -4.5, "<="),
        ("open_to_low_percent", -4.0, "<="),
        ("volume_ratio", 2.5, ">="),
        ("volume_ratio", 2.0, ">="),
    ]
    
    for metric, threshold, operator in thresholds_to_test:
        passed, failed = test_threshold(signals, metric, threshold, operator)
        effectiveness = analyze_filter_effectiveness(passed, signals)
        
        print(f"\n{metric} {operator} {threshold}:")
        print(f"  Passed: {len(passed)}/{len(signals)} ({len(passed)/len(signals)*100:.1f}%)")
        print(f"  SL_HIT reduced: {effectiveness['sl_hit_reduced']} ({effectiveness['sl_hit_reduction_pct']:.1f}%)")
        print(f"  SL_HIT remaining: {effectiveness['sl_hit_remaining']}")
        print(f"  HIGH_RISK reduced: {effectiveness['high_risk_reduced']}")
        print(f"  HIGH_RISK remaining: {effectiveness['high_risk_remaining']}")
    
    # Test combinations
    print(f"\n{'=' * 100}")
    print("COMBINATION TESTS")
    print(f"{'=' * 100}")
    
    combinations = [
        # Based on manual signal averages
        [
            ("range_percent", 5.0, ">="),
            ("open_to_low_percent", -4.5, "<="),
            ("volume_ratio", 2.5, ">=")
        ],
        # Moderate thresholds
        [
            ("range_percent", 4.0, ">="),
            ("open_to_low_percent", -4.0, "<="),
            ("volume_ratio", 2.0, ">=")
        ],
        # Focus on lower wick
        [
            ("lower_wick_body_ratio", 2.0, ">="),
            ("lower_wick_range_ratio", 0.60, ">="),
            ("open_to_low_percent", -4.5, "<=")
        ],
        # Conservative
        [
            ("range_percent", 5.0, ">="),
            ("lower_wick_body_ratio", 2.0, ">="),
            ("volume_ratio", 2.5, ">=")
        ],
        # Aggressive
        [
            ("range_percent", 4.0, ">="),
            ("lower_wick_body_ratio", 1.5, ">="),
            ("volume_ratio", 1.5, ">=")
        ],
    ]
    
    for i, conditions in enumerate(combinations, 1):
        passed, failed = evaluate_combination(signals, conditions)
        effectiveness = analyze_filter_effectiveness(passed, signals)
        
        print(f"\nCombination {i}:")
        for metric, threshold, operator in conditions:
            print(f"  {metric} {operator} {threshold}")
        print(f"  Passed: {len(passed)}/{len(signals)} ({len(passed)/len(signals)*100:.1f}%)")
        print(f"  SL_HIT reduced: {effectiveness['sl_hit_reduced']} ({effectiveness['sl_hit_reduction_pct']:.1f}%)")
        print(f"  SL_HIT remaining: {effectiveness['sl_hit_remaining']}")
        print(f"  HIGH_RISK reduced: {effectiveness['high_risk_reduced']}")
        print(f"  HIGH_RISK remaining: {effectiveness['high_risk_remaining']}")
        
        # Show which signals passed
        if passed:
            print(f"  Passed signals: {', '.join([s['symbol'] for s in passed])}")
    
    # Test pre-signal context filters
    print(f"\n{'=' * 100}")
    print("PRE-SIGNAL CONTEXT FILTERS")
    print(f"{'=' * 100}")
    
    # Test range position filter
    low_range_position = []
    for s in signals:
        if "pre_signal_context" in s and "range_position" in s["pre_signal_context"]:
            rp = s["pre_signal_context"]["range_position"].get("10_candles")
            if rp is not None and rp <= 0.3:  # Bottom 30% of range
                low_range_position.append(s)
    
    print(f"\nRange position <= 30% (bottom of range):")
    print(f"  Passed: {len(low_range_position)}/{len(signals)}")
    sl_hit_in_low = sum(1 for s in low_range_position if s.get("sl_risk_category") == "SL_HIT")
    print(f"  SL_HIT in this group: {sl_hit_in_low}")
    
    # Test previous movement filter
    strong_decline = []
    for s in signals:
        if "pre_signal_context" in s and "previous_movement" in s["pre_signal_context"]:
            pm = s["pre_signal_context"]["previous_movement"].get("10_candles")
            if pm is not None and pm <= -2.0:  # Declined 2%+ in last 10 candles
                strong_decline.append(s)
    
    print(f"\nPrevious movement <= -2% (strong decline):")
    print(f"  Passed: {len(strong_decline)}/{len(signals)}")
    sl_hit_in_decline = sum(1 for s in strong_decline if s.get("sl_risk_category") == "SL_HIT")
    print(f"  SL_HIT in this group: {sl_hit_in_decline}")
    
    print(f"\n{'=' * 100}")
    print("Testing complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
