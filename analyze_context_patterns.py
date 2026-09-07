#!/usr/bin/env python3
"""
Analyze patterns from pre-signal context data.

Research: Find patterns that distinguish fast reversals from slow ones.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median, stdev


def analyze_range_positions(contexts, timeframe):
    """Analyze range position percentages for a timeframe."""
    positions = []
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            if "range_position_pct" in tf_data and tf_data["range_position_pct"] is not None:
                positions.append(tf_data["range_position_pct"])
    
    if not positions:
        return None
    
    return {
        "count": len(positions),
        "min": min(positions),
        "max": max(positions),
        "mean": mean(positions),
        "median": median(positions),
        "stdev": stdev(positions) if len(positions) > 1 else 0,
        "percentiles": {
            "10": sorted(positions)[int(len(positions) * 0.1)] if len(positions) >= 10 else min(positions),
            "20": sorted(positions)[int(len(positions) * 0.2)] if len(positions) >= 5 else min(positions),
            "30": sorted(positions)[int(len(positions) * 0.3)] if len(positions) >= 4 else min(positions),
            "40": sorted(positions)[int(len(positions) * 0.4)] if len(positions) >= 3 else min(positions),
            "50": median(positions),
        }
    }


def analyze_previous_movement(contexts, timeframe):
    """Analyze previous downward movement for a timeframe."""
    movements = {
        "prev_1": [],
        "prev_3": [],
        "prev_5": [],
        "prev_10": []
    }
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            
            if "prev_1_candle_change_pct" in tf_data and tf_data["prev_1_candle_change_pct"] is not None:
                movements["prev_1"].append(tf_data["prev_1_candle_change_pct"])
            
            if "prev_3_candles_change_pct" in tf_data and tf_data["prev_3_candles_change_pct"] is not None:
                movements["prev_3"].append(tf_data["prev_3_candles_change_pct"])
            
            if "prev_5_candles_change_pct" in tf_data and tf_data["prev_5_candles_change_pct"] is not None:
                movements["prev_5"].append(tf_data["prev_5_candles_change_pct"])
            
            if "prev_10_candles_change_pct" in tf_data and tf_data["prev_10_candles_change_pct"] is not None:
                movements["prev_10"].append(tf_data["prev_10_candles_change_pct"])
    
    results = {}
    for key, values in movements.items():
        if values:
            results[key] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": mean(values),
                "median": median(values),
                "stdev": stdev(values) if len(values) > 1 else 0
            }
    
    return results


def analyze_support_levels(contexts, timeframe):
    """Analyze support levels and local minimums."""
    stats = {
        "at_local_min": 0,
        "total": 0,
        "broke_swing_low": 0,
        "closed_above_swing_low": 0,
        "swing_low_break_pcts": []
    }
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            stats["total"] += 1
            
            if "is_at_local_min" in tf_data and tf_data["is_at_local_min"]:
                stats["at_local_min"] += 1
            
            if "broke_previous_swing_low" in tf_data and tf_data["broke_previous_swing_low"]:
                stats["broke_swing_low"] += 1
            
            if "closed_above_swing_low" in tf_data and tf_data["closed_above_swing_low"]:
                stats["closed_above_swing_low"] += 1
            
            if "swing_low_break_pct" in tf_data and tf_data["swing_low_break_pct"] is not None:
                stats["swing_low_break_pcts"].append(tf_data["swing_low_break_pct"])
    
    if stats["total"] > 0:
        stats["at_local_min_pct"] = stats["at_local_min"] / stats["total"] * 100
        stats["broke_swing_low_pct"] = stats["broke_swing_low"] / stats["total"] * 100
        stats["closed_above_swing_low_pct"] = stats["closed_above_swing_low"] / stats["total"] * 100
    
    if stats["swing_low_break_pcts"]:
        stats["avg_swing_low_break_pct"] = mean(stats["swing_low_break_pcts"])
    
    return stats


def analyze_trend_structure(contexts, timeframe):
    """Analyze trend structure (consecutive reds, descending patterns)."""
    red_counts = []
    descending_highs = 0
    descending_lows = 0
    total = 0
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            total += 1
            
            if "consecutive_red_candles" in tf_data:
                red_counts.append(tf_data["consecutive_red_candles"])
            
            if "descending_highs" in tf_data and tf_data["descending_highs"]:
                descending_highs += 1
            
            if "descending_lows" in tf_data and tf_data["descending_lows"]:
                descending_lows += 1
    
    results = {
        "total": total,
        "descending_highs_pct": descending_highs / total * 100 if total > 0 else 0,
        "descending_lows_pct": descending_lows / total * 100 if total > 0 else 0
    }
    
    if red_counts:
        results["consecutive_red_candles"] = {
            "count": len(red_counts),
            "min": min(red_counts),
            "max": max(red_counts),
            "mean": mean(red_counts),
            "median": median(red_counts)
        }
    
    return results


def analyze_volatility(contexts, timeframe):
    """Analyze volatility (ATR, range expansion)."""
    range_expansions = []
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            
            if "range_expansion_ratio" in tf_data and tf_data["range_expansion_ratio"] is not None:
                range_expansions.append(tf_data["range_expansion_ratio"])
    
    if not range_expansions:
        return None
    
    return {
        "count": len(range_expansions),
        "min": min(range_expansions),
        "max": max(range_expansions),
        "mean": mean(range_expansions),
        "median": median(range_expansions)
    }


def analyze_ema_position(contexts, timeframe):
    """Analyze EMA position."""
    ema_20_diffs = []
    ema_50_diffs = []
    ema_200_diffs = []
    
    for ctx in contexts:
        if "timeframes" in ctx and timeframe in ctx["timeframes"]:
            tf_data = ctx["timeframes"][timeframe]
            
            if "price_vs_ema_20_pct" in tf_data and tf_data["price_vs_ema_20_pct"] is not None:
                ema_20_diffs.append(tf_data["price_vs_ema_20_pct"])
            
            if "price_vs_ema_50_pct" in tf_data and tf_data["price_vs_ema_50_pct"] is not None:
                ema_50_diffs.append(tf_data["price_vs_ema_50_pct"])
            
            if "price_vs_ema_200_pct" in tf_data and tf_data["price_vs_ema_200_pct"] is not None:
                ema_200_diffs.append(tf_data["price_vs_ema_200_pct"])
    
    results = {}
    
    if ema_20_diffs:
        results["ema_20"] = {
            "count": len(ema_20_diffs),
            "min": min(ema_20_diffs),
            "max": max(ema_20_diffs),
            "mean": mean(ema_20_diffs),
            "median": median(ema_20_diffs),
            "below_ema_pct": sum(1 for x in ema_20_diffs if x < 0) / len(ema_20_diffs) * 100
        }
    
    if ema_50_diffs:
        results["ema_50"] = {
            "count": len(ema_50_diffs),
            "min": min(ema_50_diffs),
            "max": max(ema_50_diffs),
            "mean": mean(ema_50_diffs),
            "median": median(ema_50_diffs),
            "below_ema_pct": sum(1 for x in ema_50_diffs if x < 0) / len(ema_50_diffs) * 100
        }
    
    if ema_200_diffs:
        results["ema_200"] = {
            "count": len(ema_200_diffs),
            "min": min(ema_200_diffs),
            "max": max(ema_200_diffs),
            "mean": mean(ema_200_diffs),
            "median": median(ema_200_diffs),
            "below_ema_pct": sum(1 for x in ema_200_diffs if x < 0) / len(ema_200_diffs) * 100
        }
    
    return results


def main():
    """Main analysis function."""
    print("=" * 100)
    print("PRE-SIGNAL CONTEXT PATTERN ANALYSIS")
    print("=" * 100)
    
    # Load context data
    with open("pre_signal_context_analysis.json", "r") as f:
        contexts = json.load(f)
    
    print(f"\nLoaded {len(contexts)} signal contexts")
    
    timeframes = ["15m", "1h", "4h", "1d"]
    
    report = {
        "total_signals": len(contexts),
        "timeframes": {}
    }
    
    for tf in timeframes:
        print(f"\n{'=' * 100}")
        print(f"ANALYZING {tf.upper()} TIMEFRAME")
        print(f"{'=' * 100}")
        
        tf_report = {}
        
        # 1. Range position
        range_pos = analyze_range_positions(contexts, tf)
        if range_pos:
            print(f"\n1. Range Position %:")
            print(f"   Count: {range_pos['count']}")
            print(f"   Min: {range_pos['min']:.2f}%")
            print(f"   Max: {range_pos['max']:.2f}%")
            print(f"   Mean: {range_pos['mean']:.2f}%")
            print(f"   Median: {range_pos['median']:.2f}%")
            print(f"   Percentiles: {range_pos['percentiles']}")
            tf_report["range_position"] = range_pos
        
        # 2. Previous movement
        prev_move = analyze_previous_movement(contexts, tf)
        if prev_move:
            print(f"\n2. Previous Downward Movement:")
            for key, stats in prev_move.items():
                print(f"   {key}: mean={stats['mean']:.2f}%, median={stats['median']:.2f}%, min={stats['min']:.2f}%, max={stats['max']:.2f}%")
            tf_report["previous_movement"] = prev_move
        
        # 3. Support levels
        support = analyze_support_levels(contexts, tf)
        print(f"\n3. Support Levels:")
        print(f"   At local min: {support['at_local_min']}/{support['total']} ({support['at_local_min_pct']:.1f}%)")
        print(f"   Broke swing low: {support['broke_swing_low']}/{support['total']} ({support['broke_swing_low_pct']:.1f}%)")
        print(f"   Closed above swing low: {support['closed_above_swing_low']}/{support['total']} ({support['closed_above_swing_low_pct']:.1f}%)")
        if "avg_swing_low_break_pct" in support:
            print(f"   Avg swing low break: {support['avg_swing_low_break_pct']:.2f}%")
        tf_report["support_levels"] = support
        
        # 4. Trend structure
        trend = analyze_trend_structure(contexts, tf)
        print(f"\n4. Trend Structure:")
        print(f"   Descending highs: {trend['descending_highs_pct']:.1f}%")
        print(f"   Descending lows: {trend['descending_lows_pct']:.1f}%")
        if "consecutive_red_candles" in trend:
            print(f"   Consecutive red candles: mean={trend['consecutive_red_candles']['mean']:.1f}, max={trend['consecutive_red_candles']['max']}")
        tf_report["trend_structure"] = trend
        
        # 5. Volatility
        vol = analyze_volatility(contexts, tf)
        if vol:
            print(f"\n5. Volatility (Range Expansion):")
            print(f"   Mean: {vol['mean']:.2f}x")
            print(f"   Median: {vol['median']:.2f}x")
            print(f"   Max: {vol['max']:.2f}x")
            tf_report["volatility"] = vol
        
        # 6. EMA position
        ema = analyze_ema_position(contexts, tf)
        if ema:
            print(f"\n6. EMA Position:")
            for ema_key, stats in ema.items():
                print(f"   {ema_key}: below={stats['below_ema_pct']:.1f}%, mean_diff={stats['mean']:.2f}%")
            tf_report["ema_position"] = ema
        
        report["timeframes"][tf] = tf_report
    
    # Save report
    with open("context_pattern_analysis_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Report saved to context_pattern_analysis_report.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
