#!/usr/bin/env python3
"""
Compare FAST vs SL_HIT vs NO_REVERSAL for each feature.

Research: Analyze which features distinguish good signals from bad signals.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def extract_feature_value(signal, feature_path):
    """Extract a feature value from a signal using a path like 'previous_movement.10_candles'."""
    parts = feature_path.split(".")
    value = signal
    
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    
    return value


def analyze_feature_group(signals, feature_path):
    """Analyze a feature across a group of signals."""
    values = []
    for signal in signals:
        value = extract_feature_value(signal, feature_path)
        if value is not None and isinstance(value, (int, float)):
            values.append(value)
    
    if not values:
        return None
    
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values)
    }


def analyze_categorical_feature(signals, feature_path):
    """Analyze a categorical feature across a group of signals."""
    counts = {}
    for signal in signals:
        value = extract_feature_value(signal, feature_path)
        if value is not None:
            str_value = str(value)
            counts[str_value] = counts.get(str_value, 0) + 1
    
    if not counts:
        return None
    
    total = sum(counts.values())
    return {k: {"count": v, "percent": v/total*100} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)}


def main():
    """Main analysis function."""
    print("=" * 100)
    print("FEATURE GROUP COMPARISON: FAST vs SL_HIT vs NO_REVERSAL")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load comprehensive data with higher timeframes
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
    
    # Group by category
    fast_signals = [c for c in candidates if c.get("category") in ["VERY_FAST", "FAST"]]
    sl_hit_signals = [c for c in candidates if c.get("category") == "SL_HIT"]
    no_reversal_signals = [c for c in candidates if c.get("category") == "NO_REVERSAL"]
    
    print(f"\nGroup sizes:")
    print(f"  FAST (VERY_FAST + FAST): {len(fast_signals)}")
    print(f"  SL_HIT: {len(sl_hit_signals)}")
    print(f"  NO_REVERSAL: {len(no_reversal_signals)}")
    
    # Define features to analyze
    numeric_features = [
        "previous_movement.5_candles",
        "previous_movement.10_candles",
        "previous_movement.20_candles",
        "previous_movement.30_candles",
        "previous_movement.green_count_30",
        "previous_movement.red_count_30",
        "previous_movement.green_red_ratio_30",
        "previous_movement.max_up_30",
        "previous_movement.max_down_30",
        "previous_movement.growth_10",
        "ema_structure.price_ema_9_distance",
        "ema_structure.ema_9_slope",
        "ema_structure.price_ema_21_distance",
        "ema_structure.ema_21_slope",
        "ema_structure.price_ema_50_distance",
        "ema_structure.ema_50_slope",
        "ema_structure.price_ema_100_distance",
        "ema_structure.ema_100_slope",
        "ema_structure.higher_highs_20",
        "ema_structure.higher_lows_20",
        "range_positions.range_position_10",
        "range_positions.range_position_20",
        "range_positions.range_position_50",
        "range_positions.range_position_100",
        "volatility.current_range_percent",
        "volatility.avg_range_20",
        "volatility.atr_percent",
        "volume.volume_relative_avg",
        "volume.volume_growth_5",
        "higher_timeframes.1H.pm10",
        "higher_timeframes.1H.pm20",
        "higher_timeframes.4H.pm10",
        "higher_timeframes.4H.pm20",
        "higher_timeframes.1D.pm10",
        "higher_timeframes.1D.pm20",
    ]
    
    categorical_features = [
        "previous_movement.was_growth_10",
        "ema_structure.price_above_ema_9",
        "ema_structure.price_above_ema_21",
        "ema_structure.price_above_ema_50",
        "ema_structure.price_above_ema_100",
        "ema_structure.ema_9_21_alignment",
        "ema_structure.ema_21_50_alignment",
        "ema_structure.ema_50_100_alignment",
        "range_positions.recent_high_breakout_20",
        "range_positions.recent_low_breakout_20",
        "volatility.volatility_regime",
        "higher_timeframes.1H.direction",
        "higher_timeframes.4H.direction",
        "higher_timeframes.1D.direction",
        "higher_timeframes.1H.price_above_ema_21",
        "higher_timeframes.4H.price_above_ema_21",
        "higher_timeframes.1D.price_above_ema_21",
    ]
    
    # Analyze numeric features
    print(f"\n{'=' * 100}")
    print("NUMERIC FEATURES COMPARISON")
    print(f"{'=' * 100}")
    
    print(f"\n{'Feature':<40} {'FAST Mean':>12} {'SL Mean':>12} {'NR Mean':>12} {'Diff FAST-SL':>15}")
    print("-" * 100)
    
    for feature in numeric_features:
        fast_stats = analyze_feature_group(fast_signals, feature)
        sl_stats = analyze_feature_group(sl_hit_signals, feature)
        nr_stats = analyze_feature_group(no_reversal_signals, feature)
        
        if fast_stats and sl_stats:
            fast_mean = f"{fast_stats['mean']:>10.2f}"
            sl_mean = f"{sl_stats['mean']:>10.2f}"
            nr_mean = f"{nr_stats['mean']:>10.2f}" if nr_stats else "N/A"
            diff = fast_stats['mean'] - sl_stats['mean']
            diff_str = f"{diff:>+13.2f}"
            print(f"{feature:<40} {fast_mean:>12} {sl_mean:>12} {nr_mean:>12} {diff_str:>15}")
    
    # Analyze categorical features
    print(f"\n{'=' * 100}")
    print("CATEGORICAL FEATURES COMPARISON")
    print(f"{'=' * 100}")
    
    for feature in categorical_features:
        fast_stats = analyze_categorical_feature(fast_signals, feature)
        sl_stats = analyze_categorical_feature(sl_hit_signals, feature)
        
        if fast_stats or sl_stats:
            print(f"\n{feature}:")
            if fast_stats:
                print(f"  FAST: {fast_stats}")
            if sl_stats:
                print(f"  SL_HIT: {sl_stats}")
    
    # Save results
    results = {
        "candidates": candidates,
        "numeric_features": {f: {"fast": analyze_feature_group(fast_signals, f), "sl_hit": analyze_feature_group(sl_hit_signals, f), "no_reversal": analyze_feature_group(no_reversal_signals, f)} for f in numeric_features},
        "categorical_features": {f: {"fast": analyze_categorical_feature(fast_signals, f), "sl_hit": analyze_categorical_feature(sl_hit_signals, f)} for f in categorical_features}
    }
    
    with open("feature_groups_comparison.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to feature_groups_comparison.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
