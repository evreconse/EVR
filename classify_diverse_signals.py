#!/usr/bin/env python3
"""
Classify diverse sample signals by behavior.

Research: Classify signals into VERY_FAST, FAST, SLOW, SL_HIT, NO_REVERSAL categories.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json


def classify_signal(performance):
    """Classify signal based on performance metrics."""
    # Check for errors
    if "error" in performance:
        return "ERROR"
    
    hit_tp_before_sl = performance.get("hit_tp_before_sl", False)
    hit_sl_before_tp = performance.get("hit_sl_before_tp", False)
    hit_tp_3pct = performance.get("hit_tp_3pct", False)
    hit_sl_3pct = performance.get("hit_sl_3pct", False)
    time_to_2pct = performance.get("time_to_2pct_candles")
    time_to_3pct = performance.get("time_to_3pct_candles")
    max_up_pct = performance.get("max_up_pct", 0)
    
    # Classification logic (consistent with previous research)
    
    # SL_HIT: Hit -3% before +3%
    if hit_sl_before_tp:
        return "SL_HIT"
    
    # NO_REVERSAL: Neither TP nor SL hit, and max up < 2%
    if not hit_tp_3pct and not hit_sl_3pct and max_up_pct < 2.0:
        return "NO_REVERSAL"
    
    # VERY_FAST: Hit +2% within 2 candles AND hit +3% before SL
    if hit_tp_before_sl and time_to_2pct is not None and time_to_2pct <= 2:
        return "VERY_FAST"
    
    # FAST: Hit +2% within 4 candles AND hit +3% before SL
    if hit_tp_before_sl and time_to_2pct is not None and time_to_2pct <= 4:
        return "FAST"
    
    # SLOW: Hit +3% but took more than 4 candles to reach +2%
    if hit_tp_before_sl and time_to_2pct is not None and time_to_2pct > 4:
        return "SLOW"
    
    # WEAK_REVERSAL: Hit TP but didn't meet time criteria
    if hit_tp_before_sl:
        return "WEAK_REVERSAL"
    
    # Default: NO_REVERSAL
    return "NO_REVERSAL"


def main():
    """Main classification function."""
    print("=" * 100)
    print("DIVERSE SAMPLE SIGNAL CLASSIFICATION")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load complete data
    with open("diverse_complete.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Classify signals
    categories = {}
    for candidate in candidates:
        category = classify_signal(candidate["performance"])
        candidate["category"] = category
        
        if category not in categories:
            categories[category] = []
        categories[category].append(candidate)
    
    # Print classification summary
    print(f"\n{'=' * 100}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'=' * 100}")
    
    for category in ["VERY_FAST", "FAST", "SLOW", "WEAK_REVERSAL", "SL_HIT", "NO_REVERSAL", "ERROR"]:
        count = len(categories.get(category, []))
        if count > 0:
            print(f"{category}: {count} ({count/len(candidates)*100:.1f}%)")
    
    # Save results
    results = {
        "candidates": candidates,
        "classification": {k: len(v) for k, v in categories.items()},
        "summary": data["summary"]
    }
    
    with open("diverse_classified.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Classification complete. Results saved to diverse_classified.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
