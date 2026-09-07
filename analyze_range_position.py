#!/usr/bin/env python3
"""
Analyze range position contradiction.

Research: Determine where good signals are located in the range (bottom/middle/top).

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def classify_range_position(value):
    """Classify range position into zones."""
    if value is None:
        return "UNKNOWN"
    if value < 0.33:
        return "BOTTOM"
    elif value < 0.66:
        return "MIDDLE"
    else:
        return "TOP"


def analyze_range_by_category(signals, category):
    """Analyze range position for a specific category."""
    cat_signals = [s for s in signals if s.get("category") == category]
    
    if not cat_signals:
        return None
    
    range_values = []
    for signal in cat_signals:
        rp = signal.get("comprehensive_features", {}).get("range_positions", {}).get("range_position_20")
        if rp is not None:
            range_values.append(rp)
    
    if not range_values:
        return None
    
    positions = [classify_range_position(v) for v in range_values]
    bottom_count = positions.count("BOTTOM")
    middle_count = positions.count("MIDDLE")
    top_count = positions.count("TOP")
    
    return {
        "count": len(range_values),
        "mean": mean(range_values),
        "median": median(range_values),
        "min": min(range_values),
        "max": max(range_values),
        "bottom_pct": bottom_count / len(positions) * 100,
        "middle_pct": middle_count / len(positions) * 100,
        "top_pct": top_count / len(positions) * 100
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("RANGE POSITION ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load comprehensive data
    with open("large_with_ht.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    
    # Load performance and classification data
    with open("diverse_performance.json", "r") as f:
        perf_data = json.load(f)
    
    with open("diverse_classified.json", "r") as f:
        class_data = json.load(f)
    
    # Merge data
    perf_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["performance"] for c in perf_data["candidates"]}
    class_map = {c["symbol"] + "_" + str(c["timestamp_ms"]): c["category"] for c in class_data["candidates"]}
    
    for candidate in candidates:
        key = candidate["symbol"] + "_" + str(candidate["timestamp_ms"])
        if key in perf_map:
            candidate["performance"] = perf_map[key]
        if key in class_map:
            candidate["category"] = class_map[key]
    
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze range position by category
    print(f"\n{'=' * 100}")
    print("RANGE POSITION BY CATEGORY")
    print(f"{'=' * 100}")
    
    categories = ["VERY_FAST", "FAST", "SLOW", "SL_HIT", "NO_REVERSAL"]
    
    print(f"\n{'Category':<15} {'Count':>6} {'Mean RP':>10} {'Bottom%':>10} {'Middle%':>10} {'Top%':>10}")
    print("-" * 70)
    
    results = {}
    for category in categories:
        stats = analyze_range_by_category(candidates, category)
        if stats:
            results[category] = stats
            print(f"{category:<15} {stats['count']:>6} {stats['mean']:>10.3f} {stats['bottom_pct']:>9.1f}% {stats['middle_pct']:>9.1f}% {stats['top_pct']:>9.1f}%")
    
    # Analyze range position by PM10 group
    print(f"\n{'=' * 100}")
    print("RANGE POSITION BY PM10 GROUP")
    print(f"{'=' * 100}")
    
    pm10_positive = [s for s in candidates if s.get("comprehensive_features", {}).get("previous_movement", {}).get("10_candles", -999) >= 0]
    pm10_negative = [s for s in candidates if s.get("comprehensive_features", {}).get("previous_movement", {}).get("10_candles", 999) < 0]
    
    def analyze_range_group(signals, group_name):
        range_values = []
        for signal in signals:
            rp = signal.get("comprehensive_features", {}).get("range_positions", {}).get("range_position_20")
            if rp is not None:
                range_values.append(rp)
        
        if not range_values:
            return None
        
        positions = [classify_range_position(v) for v in range_values]
        bottom_count = positions.count("BOTTOM")
        middle_count = positions.count("MIDDLE")
        top_count = positions.count("TOP")
        
        return {
            "group": group_name,
            "count": len(range_values),
            "mean": mean(range_values),
            "median": median(range_values),
            "bottom_pct": bottom_count / len(positions) * 100,
            "middle_pct": middle_count / len(positions) * 100,
            "top_pct": top_count / len(positions) * 100
        }
    
    print(f"\n{'Group':<15} {'Count':>6} {'Mean RP':>10} {'Bottom%':>10} {'Middle%':>10} {'Top%':>10}")
    print("-" * 70)
    
    for group_name, signals in [("PM10 >= 0", pm10_positive), ("PM10 < 0", pm10_negative)]:
        stats = analyze_range_group(signals, group_name)
        if stats:
            print(f"{group_name:<15} {stats['count']:>6} {stats['mean']:>10.3f} {stats['bottom_pct']:>9.1f}% {stats['middle_pct']:>9.1f}% {stats['top_pct']:>9.1f}%")
    
    # Save results
    with open("range_position_analysis.json", "w") as f:
        json.dump({"by_category": results, "by_pm10": {"pm10_positive": analyze_range_group(pm10_positive, "PM10 >= 0"), "pm10_negative": analyze_range_group(pm10_negative, "PM10 < 0")}}, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to range_position_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
