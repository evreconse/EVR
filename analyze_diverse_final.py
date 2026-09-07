#!/usr/bin/env python3
"""
Final analysis of diverse sample - PM10 >= 0 filter validation.

Research: Compare GROUP A vs GROUP B, per-coin stability, test thresholds, generate report.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median
from collections import defaultdict


def test_condition(signals, feature_path, threshold, operator):
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


def evaluate_filter(passed_signals, all_signals):
    """Evaluate filter effectiveness with TP +3% / SL -3% model."""
    total = len(all_signals)
    
    hit_tp_before_sl = [s for s in passed_signals if s["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [s for s in passed_signals if s["performance"].get("hit_sl_before_tp", False)]
    hit_tp = [s for s in passed_signals if s["performance"].get("hit_tp_3pct", False)]
    hit_sl = [s for s in passed_signals if s["performance"].get("hit_sl_3pct", False)]
    
    # Calculate +2% before -3% rate
    reached_2pct_before_sl = 0
    total_passed = len(passed_signals)
    
    for s in passed_signals:
        if s["performance"]["time_to_2pct_candles"] is not None and not s["performance"]["hit_sl_3pct"]:
            reached_2pct_before_sl += 1
        elif s["performance"]["time_to_2pct_candles"] is not None and s["performance"]["hit_sl_3pct"]:
            if s["performance"]["time_to_2pct_candles"] < s["performance"]["candles_before_sl"]:
                reached_2pct_before_sl += 1
    
    # Calculate +3% before -3% rate
    reached_3pct_before_sl = 0
    
    for s in passed_signals:
        if s["performance"]["time_to_3pct_candles"] is not None and not s["performance"]["hit_sl_3pct"]:
            reached_3pct_before_sl += 1
        elif s["performance"]["time_to_3pct_candles"] is not None and s["performance"]["hit_sl_3pct"]:
            if s["performance"]["time_to_3pct_candles"] < s["performance"]["candles_before_sl"]:
                reached_3pct_before_sl += 1
    
    # Calculate MAE before +2% and +3%
    maes_2pct = [s["performance"]["max_adverse_before_2pct"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    maes_3pct = [s["performance"]["max_adverse_before_3pct"] for s in passed_signals if s["performance"]["time_to_3pct_candles"] is not None]
    
    # Calculate time to +2% and +3%
    times_2pct = [s["performance"]["time_to_2pct_candles"] for s in passed_signals if s["performance"]["time_to_2pct_candles"] is not None]
    times_3pct = [s["performance"]["time_to_3pct_candles"] for s in passed_signals if s["performance"]["time_to_3pct_candles"] is not None]
    
    return {
        "total_signals": total,
        "passed_signals": len(passed_signals),
        "pass_rate": len(passed_signals) / total * 100 if total > 0 else 0,
        "hit_tp_before_sl": len(hit_tp_before_sl),
        "hit_sl_before_tp": len(hit_sl_before_tp),
        "hit_tp": len(hit_tp),
        "hit_sl": len(hit_sl),
        "reached_2pct_before_sl_pct": reached_2pct_before_sl / total_passed * 100 if total_passed > 0 else 0,
        "reached_3pct_before_sl_pct": reached_3pct_before_sl / total_passed * 100 if total_passed > 0 else 0,
        "hit_sl_pct": len(hit_sl) / total_passed * 100 if total_passed > 0 else 0,
        "avg_mae_before_2pct": mean(maes_2pct) if maes_2pct else None,
        "median_mae_before_2pct": median(maes_2pct) if maes_2pct else None,
        "avg_mae_before_3pct": mean(maes_3pct) if maes_3pct else None,
        "median_mae_before_3pct": median(maes_3pct) if maes_3pct else None,
        "avg_time_to_2pct": mean(times_2pct) if times_2pct else None,
        "median_time_to_2pct": median(times_2pct) if times_2pct else None,
        "avg_time_to_3pct": mean(times_3pct) if times_3pct else None,
        "median_time_to_3pct": median(times_3pct) if times_3pct else None
    }


def analyze_per_coin_stability(signals):
    """Analyze filter stability per coin."""
    coin_stats = defaultdict(lambda: {"pm10_ge_0": [], "pm10_lt_0": []})
    
    for s in signals:
        symbol = s["symbol"]
        pm10 = s["deep_features"]["short_term_trend"].get("10_candles")
        
        if pm10 is not None:
            if pm10 >= 0:
                coin_stats[symbol]["pm10_ge_0"].append(s)
            else:
                coin_stats[symbol]["pm10_lt_0"].append(s)
    
    # Calculate success rates per coin
    results = []
    for symbol, stats in coin_stats.items():
        pm10_ge_0_success = sum(1 for s in stats["pm10_ge_0"] if s["performance"].get("hit_tp_before_sl", False))
        pm10_lt_0_success = sum(1 for s in stats["pm10_lt_0"] if s["performance"].get("hit_tp_before_sl", False))
        
        pm10_ge_0_rate = pm10_ge_0_success / len(stats["pm10_ge_0"]) * 100 if stats["pm10_ge_0"] else None
        pm10_lt_0_rate = pm10_lt_0_success / len(stats["pm10_lt_0"]) * 100 if stats["pm10_lt_0"] else None
        
        diff = None
        if pm10_ge_0_rate is not None and pm10_lt_0_rate is not None:
            diff = pm10_ge_0_rate - pm10_lt_0_rate
        
        results.append({
            "symbol": symbol,
            "pm10_ge_0_count": len(stats["pm10_ge_0"]),
            "pm10_lt_0_count": len(stats["pm10_lt_0"]),
            "pm10_ge_0_success": pm10_ge_0_success,
            "pm10_lt_0_success": pm10_lt_0_success,
            "pm10_ge_0_rate": pm10_ge_0_rate,
            "pm10_lt_0_rate": pm10_lt_0_rate,
            "difference": diff
        })
    
    return results


def main():
    """Main analysis function."""
    print("=" * 100)
    print("DIVERSE SAMPLE FINAL ANALYSIS - PM10 >= 0 FILTER")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load classified data
    with open("diverse_classified.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    print(f"Unique symbols: {data['summary']['unique_symbols']}")
    
    # Print classification
    print(f"\n{'=' * 100}")
    print("CLASSIFICATION")
    print(f"{'=' * 100}")
    for category, count in data["classification"].items():
        print(f"{category}: {count} ({count/len(candidates)*100:.1f}%)")
    
    # Group by PM10
    print(f"\n{'=' * 100}")
    print("GROUP A vs GROUP B COMPARISON")
    print(f"{'=' * 100}")
    
    pm10_ge_0 = test_condition(candidates, ["deep_features", "short_term_trend", "10_candles"], 0.0, ">=")
    pm10_lt_0 = test_condition(candidates, ["deep_features", "short_term_trend", "10_candles"], 0.0, "<")
    
    print(f"\nGROUP A (PM10 >= 0): {len(pm10_ge_0)} signals ({len(pm10_ge_0)/len(candidates)*100:.1f}%)")
    print(f"GROUP B (PM10 < 0): {len(pm10_lt_0)} signals ({len(pm10_lt_0)/len(candidates)*100:.1f}%)")
    
    # Evaluate GROUP A
    group_a_eval = evaluate_filter(pm10_ge_0, pm10_ge_0)
    print(f"\nGROUP A Performance:")
    print(f"  +2% before -3%: {group_a_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {group_a_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {group_a_eval['hit_sl_pct']:.1f}%")
    if group_a_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {group_a_eval['avg_mae_before_2pct']:.2f}%")
    if group_a_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {group_a_eval['avg_time_to_2pct']:.1f} candles")
    
    # Evaluate GROUP B
    group_b_eval = evaluate_filter(pm10_lt_0, pm10_lt_0)
    print(f"\nGROUP B Performance:")
    print(f"  +2% before -3%: {group_b_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {group_b_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {group_b_eval['hit_sl_pct']:.1f}%")
    if group_b_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {group_b_eval['avg_mae_before_2pct']:.2f}%")
    if group_b_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {group_b_eval['avg_time_to_2pct']:.1f} candles")
    
    # Per-coin stability
    print(f"\n{'=' * 100}")
    print("PER-COIN STABILITY")
    print(f"{'=' * 100}")
    
    coin_results = analyze_per_coin_stability(candidates)
    
    print(f"\n{'Symbol':<20} {'PM10>=0':>10} {'PM10<0':>10} {'Diff':>10}")
    print("-" * 60)
    
    better_count = 0
    worse_count = 0
    similar_count = 0
    
    for r in coin_results:
        diff_str = f"{r['difference']:.1f}%" if r['difference'] is not None else "N/A"
        pm10_ge_0_str = f"{r['pm10_ge_0_rate']:.1f}%" if r['pm10_ge_0_rate'] is not None else "N/A"
        pm10_lt_0_str = f"{r['pm10_lt_0_rate']:.1f}%" if r['pm10_lt_0_rate'] is not None else "N/A"
        print(f"{r['symbol']:<20} {pm10_ge_0_str:>10} {pm10_lt_0_str:>10} {diff_str:>10}")
        
        if r['difference'] is not None:
            if r['difference'] > 10:
                better_count += 1
            elif r['difference'] < -10:
                worse_count += 1
            else:
                similar_count += 1
    
    print(f"\nStability Summary:")
    print(f"  PM10 >= 0 better: {better_count} coins")
    print(f"  PM10 >= 0 worse: {worse_count} coins")
    print(f"  Similar: {similar_count} coins")
    
    # Test alternative thresholds
    print(f"\n{'=' * 100}")
    print("ALTERNATIVE THRESHOLDS")
    print(f"{'=' * 100}")
    
    thresholds = [-1.0, 0.0, 1.0, 2.0]
    results = []
    
    for thresh in thresholds:
        passed = test_condition(candidates, ["deep_features", "short_term_trend", "10_candles"], thresh, ">=")
        eval_result = evaluate_filter(passed, candidates)
        results.append((f"PM10 >= {thresh}%", eval_result))
        
        print(f"\nPM10 >= {thresh}%:")
        print(f"  Pass Rate: {eval_result['pass_rate']:.1f}%")
        print(f"  +2% before -3%: {eval_result['reached_2pct_before_sl_pct']:.1f}%")
        print(f"  +3% before -3%: {eval_result['reached_3pct_before_sl_pct']:.1f}%")
        print(f"  SL -3%: {eval_result['hit_sl_pct']:.1f}%")
        if eval_result['avg_mae_before_2pct']:
            print(f"  Avg MAE: {eval_result['avg_mae_before_2pct']:.2f}%")
        if eval_result['avg_time_to_2pct']:
            print(f"  Avg time to +2%: {eval_result['avg_time_to_2pct']:.1f} candles")
    
    # Test short_term_direction
    print(f"\n{'=' * 100}")
    print("SHORT_TERM_DIRECTION TEST")
    print(f"{'=' * 100}")
    
    up_passed = test_condition(candidates, ["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
    up_eval = evaluate_filter(up_passed, candidates)
    
    print(f"\nshort_term_direction == UP:")
    print(f"  Pass Rate: {up_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {up_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {up_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {up_eval['hit_sl_pct']:.1f}%")
    if up_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {up_eval['avg_mae_before_2pct']:.2f}%")
    if up_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {up_eval['avg_time_to_2pct']:.1f} candles")
    
    results.append(("short_term_direction == UP", up_eval))
    
    # Test combination
    print(f"\n{'=' * 100}")
    print("COMBINATION TEST")
    print(f"{'=' * 100}")
    
    combo_passed = test_condition(pm10_ge_0, ["deep_features", "short_term_trend", "short_term_direction"], "UP", "==")
    combo_eval = evaluate_filter(combo_passed, candidates)
    
    print(f"\nPM10 >= 0 AND short_term_direction == UP:")
    print(f"  Pass Rate: {combo_eval['pass_rate']:.1f}%")
    print(f"  +2% before -3%: {combo_eval['reached_2pct_before_sl_pct']:.1f}%")
    print(f"  +3% before -3%: {combo_eval['reached_3pct_before_sl_pct']:.1f}%")
    print(f"  SL -3%: {combo_eval['hit_sl_pct']:.1f}%")
    if combo_eval['avg_mae_before_2pct']:
        print(f"  Avg MAE: {combo_eval['avg_mae_before_2pct']:.2f}%")
    if combo_eval['avg_time_to_2pct']:
        print(f"  Avg time to +2%: {combo_eval['avg_time_to_2pct']:.1f} candles")
    
    results.append(("PM10 >= 0 AND UP", combo_eval))
    
    # Final comparison table
    print(f"\n{'=' * 100}")
    print("FINAL COMPARISON TABLE")
    print(f"{'=' * 100}")
    print(f"\n{'Filter':<40} {'Pass Rate':>10} {'+2% before -3%':>15} {'+3% before -3%':>15} {'SL -3%':>10} {'Avg MAE':>10} {'Time +2%':>10}")
    print("-" * 120)
    
    for name, eval_result in results:
        print(f"{name:<40} {eval_result['pass_rate']:>9.1f}% {eval_result['reached_2pct_before_sl_pct']:>14.1f}% {eval_result['reached_3pct_before_sl_pct']:>14.1f}% {eval_result['hit_sl_pct']:>9.1f}% {eval_result['avg_mae_before_2pct']:>9.2f}% {eval_result['avg_time_to_2pct']:>9.1f}")
    
    # Save results
    final_results = {
        "candidates": candidates,
        "group_a_eval": group_a_eval,
        "group_b_eval": group_b_eval,
        "coin_stability": coin_results,
        "threshold_results": results,
        "summary": data["summary"]
    }
    
    with open("diverse_final_analysis.json", "w") as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to diverse_final_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
