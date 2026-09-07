#!/usr/bin/env python3
"""
Compare validation sample results with original sample.

Research: Compare key metrics between validation sample and original research sample.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json


def main():
    """Main comparison function."""
    print("=" * 100)
    print("VALIDATION VS ORIGINAL SAMPLE COMPARISON")
    print("=" * 100)
    
    # Original sample results (from previous research)
    original_classification = {
        "VERY_FAST": 13,
        "FAST": 6,
        "SLOW": 6,
        "SL_HIT": 66,
        "WEAK_REVERSAL": 6,
        "NO_REVERSAL": 3
    }
    original_total = 100
    original_fast = original_classification["VERY_FAST"] + original_classification["FAST"]
    original_sl_hit = original_classification["SL_HIT"]
    
    # Validation sample results
    with open("validation_performance_filtered.json", "r") as f:
        validation_data = json.load(f)
    
    validation_classification = validation_data["classification"]
    validation_total = len(validation_data["candidates"])
    validation_very_fast = validation_classification.get("VERY_FAST", 0)
    validation_slow = validation_classification.get("SLOW", 0)
    validation_sl_hit = validation_classification.get("SL_HIT", 0)
    validation_no_reversal = validation_classification.get("NO_REVERSAL", 0)
    validation_fast = validation_very_fast  # Only VERY_FAST in validation
    
    print(f"\n{'=' * 100}")
    print("SAMPLE COMPARISON")
    print(f"{'=' * 100}")
    
    print(f"\nOriginal Sample:")
    print(f"  Total: {original_total} signals")
    print(f"  FAST/VERY_FAST: {original_fast} ({original_fast/original_total*100:.1f}%)")
    print(f"  SL_HIT: {original_sl_hit} ({original_sl_hit/original_total*100:.1f}%)")
    print(f"  SLOW: {original_classification['SLOW']} ({original_classification['SLOW']/original_total*100:.1f}%)")
    print(f"  NO_REVERSAL: {original_classification['NO_REVERSAL']} ({original_classification['NO_REVERSAL']/original_total*100:.1f}%)")
    
    print(f"\nValidation Sample:")
    print(f"  Total: {validation_total} signals (after filtering errors)")
    print(f"  VERY_FAST: {validation_very_fast} ({validation_very_fast/validation_total*100:.1f}%)")
    print(f"  SLOW: {validation_slow} ({validation_slow/validation_total*100:.1f}%)")
    print(f"  SL_HIT: {validation_sl_hit} ({validation_sl_hit/validation_total*100:.1f}%)")
    print(f"  NO_REVERSAL: {validation_no_reversal} ({validation_no_reversal/validation_total*100:.1f}%)")
    
    print(f"\n{'=' * 100}")
    print("KEY FINDINGS COMPARISON")
    print(f"{'=' * 100}")
    
    print(f"\n1. SL_HIT Rate:")
    print(f"   Original: {original_sl_hit/original_total*100:.1f}%")
    print(f"   Validation: {validation_sl_hit/validation_total*100:.1f}%")
    print(f"   Difference: {(validation_sl_hit/validation_total - original_sl_hit/original_total)*100:+.1f} percentage points")
    
    print(f"\n2. FAST Rate:")
    print(f"   Original: {original_fast/original_total*100:.1f}%")
    print(f"   Validation: {validation_fast/validation_total*100:.1f}%")
    print(f"   Difference: {(validation_fast/validation_total - original_fast/original_total)*100:+.1f} percentage points")
    
    print(f"\n{'=' * 100}")
    print("HYPOTHESIS VALIDATION SUMMARY")
    print(f"{'=' * 100}")
    
    print(f"\nOriginal Research Findings:")
    print(f"  - previous_movement_10: FAST +2.61%, SL_HIT -3.26%")
    print(f"  - range_position_20: FAST 58.6%, SL_HIT 45.0%")
    print(f"  - ema_21_slope: FAST +2.27, SL_HIT -2.99")
    print(f"  - Continuation hypothesis: 5/5 evidence supporting")
    
    print(f"\nValidation Sample Findings:")
    print(f"  - previous_movement_10: FAST +4.91%, SL_HIT -0.80%")
    print(f"  - short_term_direction == UP: 80% reached +2% before -3%")
    print(f"  - current_range_percent <= 4.0%: 0% VERY_FAST preserved (FAILED)")
    print(f"  - range_position_20 >= 0.5: 60% reached +2% before -3%")
    
    print(f"\n{'=' * 100}")
    print("COMBINATION PERFORMANCE COMPARISON")
    print(f"{'=' * 100}")
    
    print(f"\nOriginal Three-Factor Combination:")
    print(f"  previous_movement_10 >= 0.0 AND range_position_20 >= 0.5 AND current_range_percent <= 4.0")
    print(f"  Pass rate: 30%")
    print(f"  FAST preserved: 68.4%")
    print(f"  SL_HIT reduced: 78.8%")
    print(f"  SL_HIT in passed: 46.7%")
    
    print(f"\nValidation Three-Factor Combination:")
    print(f"  previous_movement_10 >= 0.0 AND range_position_20 >= 0.5 AND current_range_percent <= 4.0")
    print(f"  Pass rate: 13.3%")
    print(f"  VERY_FAST preserved: 0.0% (FAILED)")
    print(f"  SL_HIT reduced: 57.1%")
    print(f"  Reached +2% before -3%: 33.3%")
    
    print(f"\nBest Validation Combination:")
    print(f"  short_term_direction == UP")
    print(f"  Pass rate: 22.2%")
    print(f"  VERY_FAST preserved: 57.1%")
    print(f"  SL_HIT reduced: 57.1%")
    print(f"  Reached +2% before -3%: 80.0%")
    print(f"  Avg MAE before +2%: 1.01%")
    print(f"  Avg time to +2%: 1.2 candles")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
