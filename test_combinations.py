#!/usr/bin/env python3
"""
Test feature combinations systematically.

Research: Test various filter combinations to find promising candidates.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def passes_filter(signal, filter_def):
    """Check if a signal passes a filter definition."""
    for feature_path, condition in filter_def.items():
        # Extract value
        parts = feature_path.split(".")
        value = signal
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return False
        
        if value is None:
            return False
        
        # Check condition
        if isinstance(condition, str):
            # String comparison
            if condition.startswith(">="):
                threshold = float(condition[2:])
                if not (value >= threshold):
                    return False
            elif condition.startswith("<="):
                threshold = float(condition[2:])
                if not (value <= threshold):
                    return False
            elif condition.startswith(">"):
                threshold = float(condition[1:])
                if not (value > threshold):
                    return False
            elif condition.startswith("<"):
                threshold = float(condition[1:])
                if not (value < threshold):
                    return False
            elif condition.startswith("=="):
                expected = condition[2:]
                if str(value) != expected:
                    return False
            elif condition.startswith("!="):
                expected = condition[2:]
                if str(value) == expected:
                    return False
        elif isinstance(condition, bool):
            if value != condition:
                return False
        else:
            if value != condition:
                return False
    
    return True


def analyze_filter_performance(signals, filter_def):
    """Analyze performance of a filter."""
    passed = [s for s in signals if passes_filter(s, filter_def)]
    
    if not passed:
        return None
    
    total = len(passed)
    fast = [s for s in passed if s.get("category") in ["VERY_FAST", "FAST"]]
    sl_hit = [s for s in passed if s.get("category") == "SL_HIT"]
    no_reversal = [s for s in passed if s.get("category") == "NO_REVERSAL"]
    
    hit_tp_before_sl = [s for s in passed if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in passed if s["performance"].get("hit_sl_before_tp", False)]
    
    maes = [s["performance"]["max_adverse_before_2pct"] for s in passed if s["performance"]["max_adverse_before_2pct"] is not None]
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in passed if s["performance"]["time_to_2pct_candles"] is not None]
    
    return {
        "pass_rate": total / len(signals) * 100,
        "total": total,
        "fast_count": len(fast),
        "fast_pct": len(fast) / total * 100,
        "sl_hit_count": len(sl_hit),
        "sl_hit_pct": len(sl_hit) / total * 100,
        "no_reversal_count": len(no_reversal),
        "no_reversal_pct": len(no_reversal) / total * 100,
        "tp_before_sl_count": len(hit_tp_before_sl),
        "tp_before_sl_pct": len(hit_tp_before_sl) / total * 100,
        "sl_before_tp_count": len(hit_sl_before_tp),
        "sl_before_tp_pct": len(hit_sl_before_tp) / total * 100,
        "avg_mae": mean(maes) if maes else None,
        "median_mae": median(maes) if maes else None,
        "avg_time_2pct": mean(times_2pct) if times_2pct else None,
        "median_time_2pct": median(times_2pct) if times_2pct else None
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("SYSTEMATIC FEATURE COMBINATION TESTING")
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
    
    # Define filter combinations to test
    filters = {
        "PM10 >= 0": {"comprehensive_features.previous_movement.10_candles": ">=0"},
        "PM10 >= -1%": {"comprehensive_features.previous_movement.10_candles": ">=-1"},
        "PM10 >= 1%": {"comprehensive_features.previous_movement.10_candles": ">=1"},
        "PM10 >= 2%": {"comprehensive_features.previous_movement.10_candles": ">=2"},
        "PM10 <= -1%": {"comprehensive_features.previous_movement.10_candles": "<=-1"},
        "PM10 <= -2%": {"comprehensive_features.previous_movement.10_candles": "<=-2"},
        "EMA21 Slope >= 0": {"comprehensive_features.ema_structure.ema_21_slope": ">=0"},
        "EMA21 Slope >= 1%": {"comprehensive_features.ema_structure.ema_21_slope": ">=1"},
        "Price > EMA21": {"comprehensive_features.ema_structure.price_above_ema_21": True},
        "Price > EMA50": {"comprehensive_features.ema_structure.price_above_ema_50": True},
        "Range Position < 0.3": {"comprehensive_features.range_positions.range_position_20": "<0.3"},
        "Range Position > 0.7": {"comprehensive_features.range_positions.range_position_20": ">0.7"},
        "Range Position 0.4-0.6": {"comprehensive_features.range_positions.range_position_20": ">=0.4", "comprehensive_features.range_positions.range_position_20": "<=0.6"},
        "1H Direction DOWN": {"higher_timeframes.1H.direction": "==DOWN"},
        "1H Direction UP": {"higher_timeframes.1H.direction": "==UP"},
        "4H Direction DOWN": {"higher_timeframes.4H.direction": "==DOWN"},
        "4H Direction UP": {"higher_timeframes.4H.direction": "==UP"},
        "1D Direction DOWN": {"higher_timeframes.1D.direction": "==DOWN"},
        "1D Direction UP": {"higher_timeframes.1D.direction": "==UP"},
        "1H Price > EMA21": {"higher_timeframes.1H.price_above_ema_21": True},
        "1H Price < EMA21": {"higher_timeframes.1H.price_above_ema_21": False},
        "4H Price > EMA21": {"higher_timeframes.4H.price_above_ema_21": True},
        "4H Price < EMA21": {"higher_timeframes.4H.price_above_ema_21": False},
        "1D Price > EMA21": {"higher_timeframes.1D.price_above_ema_21": True},
        "1D Price < EMA21": {"higher_timeframes.1D.price_above_ema_21": False},
        "PM10 >= 0 AND EMA21 Slope >= 0": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "comprehensive_features.ema_structure.ema_21_slope": ">=0"
        },
        "PM10 >= 0 AND Price > EMA21": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "comprehensive_features.ema_structure.price_above_ema_21": True
        },
        "PM10 >= 0 AND 1H DOWN": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.1H.direction": "==DOWN"
        },
        "PM10 >= 0 AND 4H DOWN": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.4H.direction": "==DOWN"
        },
        "PM10 >= 0 AND 1D DOWN": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.1D.direction": "==DOWN"
        },
        "PM10 >= 0 AND 1H Price < EMA21": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.1H.price_above_ema_21": False
        },
        "PM10 >= 0 AND 4H Price < EMA21": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.4H.price_above_ema_21": False
        },
        "PM10 >= 0 AND 1D Price < EMA21": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.1D.price_above_ema_21": False
        },
        "EMA21 Slope >= 0 AND 1H DOWN": {
            "comprehensive_features.ema_structure.ema_21_slope": ">=0",
            "higher_timeframes.1H.direction": "==DOWN"
        },
        "Price > EMA21 AND 1H DOWN": {
            "comprehensive_features.ema_structure.price_above_ema_21": True,
            "higher_timeframes.1H.direction": "==DOWN"
        },
        "PM10 >= 0 AND EMA21 Slope >= 0 AND 1H DOWN": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "comprehensive_features.ema_structure.ema_21_slope": ">=0",
            "higher_timeframes.1H.direction": "==DOWN"
        },
        "PM10 >= 0 AND 1H DOWN AND 4H DOWN": {
            "comprehensive_features.previous_movement.10_candles": ">=0",
            "higher_timeframes.1H.direction": "==DOWN",
            "higher_timeframes.4H.direction": "==DOWN"
        },
    }
    
    # Test all filters
    print(f"\n{'=' * 100}")
    print("FILTER COMBINATION RESULTS")
    print(f"{'=' * 100}")
    
    print(f"\n{'Filter':<45} {'Pass%':>8} {'Total':>6} {'FAST%':>8} {'SL%':>8} {'TP%':>8} {'MAE':>8} {'Time+2%':>10}")
    print("-" * 110)
    
    results = {}
    for filter_name, filter_def in filters.items():
        perf = analyze_filter_performance(candidates, filter_def)
        if perf:
            results[filter_name] = perf
            pass_rate = f"{perf['pass_rate']:>7.1f}%"
            fast_pct = f"{perf['fast_pct']:>7.1f}%"
            sl_pct = f"{perf['sl_hit_pct']:>7.1f}%"
            tp_pct = f"{perf['tp_before_sl_pct']:>7.1f}%"
            mae_str = f"{perf['avg_mae']:>7.2f}%" if perf['avg_mae'] is not None else "N/A"
            time_str = f"{perf['avg_time_2pct']:>9.1f}" if perf['avg_time_2pct'] is not None else "N/A"
            print(f"{filter_name:<45} {pass_rate:>8} {perf['total']:>6} {fast_pct:>8} {sl_pct:>8} {tp_pct:>8} {mae_str:>8} {time_str:>10}")
    
    # Save results
    with open("combination_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to combination_test_results.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
