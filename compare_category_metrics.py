#!/usr/bin/env python3
"""
Compare candle metrics between performance categories.

Research: Identify which candle characteristics distinguish FAST from SL_HIT.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def main():
    """Main analysis function."""
    print("=" * 100)
    print("CATEGORY METRICS COMPARISON")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load analysis results
    with open("large_sample_performance_analysis.json", "r") as f:
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
    
    # Metrics to compare
    metrics = [
        "body_percent",
        "range_percent",
        "lower_wick_body_ratio",
        "lower_wick_range_ratio",
        "open_to_low_percent",
        "volume_ratio"
    ]
    
    # Compare each category
    for cat, signals in sorted(categories.items()):
        print(f"\n{'=' * 100}")
        print(f"{cat} ({len(signals)} signals)")
        print(f"{'=' * 100}")
        
        for metric in metrics:
            values = []
            for s in signals:
                if metric in s["formula_details"]:
                    values.append(s["formula_details"][metric])
                elif metric == "lower_wick_body_ratio" and metric in s:
                    values.append(s[metric])
                elif metric == "lower_wick_range_ratio" and metric in s:
                    values.append(s[metric])
                elif metric == "volume_ratio" and metric in s:
                    values.append(s[metric])
            
            if values:
                print(f"{metric}:")
                print(f"  Mean: {mean(values):.4f}")
                print(f"  Median: {median(values):.4f}")
                print(f"  Min: {min(values):.4f}")
                print(f"  Max: {max(values):.4f}")
    
    # Focus on FAST vs SL_HIT comparison
    print(f"\n{'=' * 100}")
    print("FAST vs SL_HIT COMPARISON")
    print(f"{'=' * 100}")
    
    fast_signals = categories.get("VERY_FAST", []) + categories.get("FAST", [])
    sl_hit_signals = categories.get("SL_HIT", [])
    
    print(f"\nFAST/VERY_FAST ({len(fast_signals)} signals) vs SL_HIT ({len(sl_hit_signals)} signals)")
    
    for metric in metrics:
        fast_values = []
        sl_values = []
        
        for s in fast_signals:
            if metric in s["formula_details"]:
                fast_values.append(s["formula_details"][metric])
            elif metric == "lower_wick_body_ratio" and metric in s:
                fast_values.append(s[metric])
            elif metric == "lower_wick_range_ratio" and metric in s:
                fast_values.append(s[metric])
            elif metric == "volume_ratio" and metric in s:
                fast_values.append(s[metric])
        
        for s in sl_hit_signals:
            if metric in s["formula_details"]:
                sl_values.append(s["formula_details"][metric])
            elif metric == "lower_wick_body_ratio" and metric in s:
                sl_values.append(s[metric])
            elif metric == "lower_wick_range_ratio" and metric in s:
                sl_values.append(s[metric])
            elif metric == "volume_ratio" and metric in s:
                sl_values.append(s[metric])
        
        if fast_values and sl_values:
            fast_mean = mean(fast_values)
            sl_mean = mean(sl_values)
            diff = fast_mean - sl_mean
            diff_pct = (diff / sl_mean * 100) if sl_mean != 0 else 0
            
            print(f"\n{metric}:")
            print(f"  FAST: mean={fast_mean:.4f}, median={median(fast_values):.4f}")
            print(f"  SL_HIT: mean={sl_mean:.4f}, median={median(sl_values):.4f}")
            print(f"  Difference: {diff:+.4f} ({diff_pct:+.1f}%)")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
