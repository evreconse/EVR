#!/usr/bin/env python3
"""
Verify continuation vs reversal hypothesis.

Research: Analyze whether the strategy is trading continuation patterns rather than reversals.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def main():
    """Main analysis function."""
    print("=" * 100)
    print("CONTINUATION VS REVERSAL HYPOTHESIS VERIFICATION")
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
    no_reversal = categories.get("NO_REVERSAL", [])
    
    print(f"FAST/VERY_FAST: {len(fast_signals)} signals")
    print(f"SL_HIT: {len(sl_hit_signals)} signals")
    print(f"NO_REVERSAL: {len(no_reversal)} signals")
    
    print(f"\n{'=' * 100}")
    print("HYPOTHESIS: Strategy trades continuation patterns, not reversals")
    print(f"{'=' * 100}")
    
    print("\nExpected if CONTINUATION hypothesis is TRUE:")
    print("- FAST signals should have positive previous movement (rising)")
    print("- FAST signals should be in middle-to-top of range (not at bottom)")
    print("- FAST signals should have positive EMA slope (uptrend)")
    print("- FAST signals should have price above EMA (uptrend)")
    print("- NO_REVERSAL signals should be at bottom of range (support)")
    print("- NO_REVERSAL signals should have negative previous movement (downtrend)")
    
    print("\nExpected if REVERSAL hypothesis is TRUE:")
    print("- FAST signals should have negative previous movement (falling)")
    print("- FAST signals should be at bottom of range (support)")
    print("- FAST signals should have negative EMA slope (downtrend)")
    print("- FAST signals should have price below EMA (oversold)")
    
    print(f"\n{'=' * 100}")
    print("EVIDENCE ANALYSIS")
    print(f"{'=' * 100}")
    
    # Evidence 1: Previous movement
    print(f"\n--- Evidence 1: Previous Movement (10 candles) ---")
    
    fast_pm = []
    sl_pm = []
    no_pm = []
    
    for s in fast_signals:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            val = s["deep_features"]["short_term_trend"].get("10_candles")
            if val is not None:
                fast_pm.append(val)
    
    for s in sl_hit_signals:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            val = s["deep_features"]["short_term_trend"].get("10_candles")
            if val is not None:
                sl_pm.append(val)
    
    for s in no_reversal:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            val = s["deep_features"]["short_term_trend"].get("10_candles")
            if val is not None:
                no_pm.append(val)
    
    if fast_pm:
        print(f"FAST: mean={mean(fast_pm):.4f}%, median={median(fast_pm):.4f}%")
        print(f"  Positive: {sum(1 for x in fast_pm if x > 0)}/{len(fast_pm)} ({sum(1 for x in fast_pm if x > 0)/len(fast_pm)*100:.1f}%)")
    
    if sl_pm:
        print(f"SL_HIT: mean={mean(sl_pm):.4f}%, median={median(sl_pm):.4f}%")
        print(f"  Positive: {sum(1 for x in sl_pm if x > 0)}/{len(sl_pm)} ({sum(1 for x in sl_pm if x > 0)/len(sl_pm)*100:.1f}%)")
    
    if no_pm:
        print(f"NO_REVERSAL: mean={mean(no_pm):.4f}%, median={median(no_pm):.4f}%")
        print(f"  Positive: {sum(1 for x in no_pm if x > 0)}/{len(no_pm)} ({sum(1 for x in no_pm if x > 0)/len(no_pm)*100:.1f}%)")
    
    print(f"\nInterpretation: {'CONTINUATION' if mean(fast_pm) > 0 else 'REVERSAL'}")
    
    # Evidence 2: Range position
    print(f"\n--- Evidence 2: Range Position (20 candles) ---")
    
    fast_rp = []
    sl_rp = []
    no_rp = []
    
    for s in fast_signals:
        if "deep_features" in s and "distance_to_extremes" in s["deep_features"]:
            val = s["deep_features"]["distance_to_extremes"].get("range_position_20")
            if val is not None:
                fast_rp.append(val)
    
    for s in sl_hit_signals:
        if "deep_features" in s and "distance_to_extremes" in s["deep_features"]:
            val = s["deep_features"]["distance_to_extremes"].get("range_position_20")
            if val is not None:
                sl_rp.append(val)
    
    for s in no_reversal:
        if "deep_features" in s and "distance_to_extremes" in s["deep_features"]:
            val = s["deep_features"]["distance_to_extremes"].get("range_position_20")
            if val is not None:
                no_rp.append(val)
    
    if fast_rp:
        print(f"FAST: mean={mean(fast_rp):.4f}, median={median(fast_rp):.4f}")
        print(f"  In top 50%: {sum(1 for x in fast_rp if x > 0.5)}/{len(fast_rp)} ({sum(1 for x in fast_rp if x > 0.5)/len(fast_rp)*100:.1f}%)")
        print(f"  In bottom 20%: {sum(1 for x in fast_rp if x < 0.2)}/{len(fast_rp)} ({sum(1 for x in fast_rp if x < 0.2)/len(fast_rp)*100:.1f}%)")
    
    if sl_rp:
        print(f"SL_HIT: mean={mean(sl_rp):.4f}, median={median(sl_rp):.4f}")
        print(f"  In top 50%: {sum(1 for x in sl_rp if x > 0.5)}/{len(sl_rp)} ({sum(1 for x in sl_rp if x > 0.5)/len(sl_rp)*100:.1f}%)")
        print(f"  In bottom 20%: {sum(1 for x in sl_rp if x < 0.2)}/{len(sl_rp)} ({sum(1 for x in sl_rp if x < 0.2)/len(sl_rp)*100:.1f}%)")
    
    if no_rp:
        print(f"NO_REVERSAL: mean={mean(no_rp):.4f}, median={median(no_rp):.4f}")
        print(f"  In top 50%: {sum(1 for x in no_rp if x > 0.5)}/{len(no_rp)} ({sum(1 for x in no_rp if x > 0.5)/len(no_rp)*100:.1f}%)")
        print(f"  In bottom 20%: {sum(1 for x in no_rp if x < 0.2)}/{len(no_rp)} ({sum(1 for x in no_rp if x < 0.2)/len(no_rp)*100:.1f}%)")
    
    print(f"\nInterpretation: {'CONTINUATION' if mean(fast_rp) > 0.5 else 'REVERSAL'}")
    
    # Evidence 3: EMA slope
    print(f"\n--- Evidence 3: EMA 21 Slope ---")
    
    fast_slope = []
    sl_slope = []
    no_slope = []
    
    for s in fast_signals:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("ema_21_slope")
            if val is not None:
                fast_slope.append(val)
    
    for s in sl_hit_signals:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("ema_21_slope")
            if val is not None:
                sl_slope.append(val)
    
    for s in no_reversal:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("ema_21_slope")
            if val is not None:
                no_slope.append(val)
    
    if fast_slope:
        print(f"FAST: mean={mean(fast_slope):.4f}, median={median(fast_slope):.4f}")
        print(f"  Positive: {sum(1 for x in fast_slope if x > 0)}/{len(fast_slope)} ({sum(1 for x in fast_slope if x > 0)/len(fast_slope)*100:.1f}%)")
    
    if sl_slope:
        print(f"SL_HIT: mean={mean(sl_slope):.4f}, median={median(sl_slope):.4f}")
        print(f"  Positive: {sum(1 for x in sl_slope if x > 0)}/{len(sl_slope)} ({sum(1 for x in sl_slope if x > 0)/len(sl_slope)*100:.1f}%)")
    
    if no_slope:
        print(f"NO_REVERSAL: mean={mean(no_slope):.4f}, median={median(no_slope):.4f}")
        print(f"  Positive: {sum(1 for x in no_slope if x > 0)}/{len(no_slope)} ({sum(1 for x in no_slope if x > 0)/len(no_slope)*100:.1f}%)")
    
    print(f"\nInterpretation: {'CONTINUATION' if mean(fast_slope) > 0 else 'REVERSAL'}")
    
    # Evidence 4: Price above EMA
    print(f"\n--- Evidence 4: Price Above EMA 21 ---")
    
    fast_above = []
    sl_above = []
    no_above = []
    
    for s in fast_signals:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("price_above_ema_21")
            if val is not None:
                fast_above.append(val)
    
    for s in sl_hit_signals:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("price_above_ema_21")
            if val is not None:
                sl_above.append(val)
    
    for s in no_reversal:
        if "deep_features" in s and "ema_sma" in s["deep_features"]:
            val = s["deep_features"]["ema_sma"].get("price_above_ema_21")
            if val is not None:
                no_above.append(val)
    
    if fast_above:
        print(f"FAST: {sum(fast_above)}/{len(fast_above)} ({sum(fast_above)/len(fast_above)*100:.1f}%) above EMA 21")
    
    if sl_above:
        print(f"SL_HIT: {sum(sl_above)}/{len(sl_above)} ({sum(sl_above)/len(sl_above)*100:.1f}%) above EMA 21")
    
    if no_above:
        print(f"NO_REVERSAL: {sum(no_above)}/{len(no_above)} ({sum(no_above)/len(no_above)*100:.1f}%) above EMA 21")
    
    print(f"\nInterpretation: {'CONTINUATION' if sum(fast_above)/len(fast_above) > 0.5 else 'REVERSAL'}")
    
    # Evidence 5: Short-term direction
    print(f"\n--- Evidence 5: Short-term Direction ---")
    
    fast_dir = {}
    sl_dir = {}
    no_dir = {}
    
    for s in fast_signals:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            direction = s["deep_features"]["short_term_trend"].get("short_term_direction")
            if direction:
                fast_dir[direction] = fast_dir.get(direction, 0) + 1
    
    for s in sl_hit_signals:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            direction = s["deep_features"]["short_term_trend"].get("short_term_direction")
            if direction:
                sl_dir[direction] = sl_dir.get(direction, 0) + 1
    
    for s in no_reversal:
        if "deep_features" in s and "short_term_trend" in s["deep_features"]:
            direction = s["deep_features"]["short_term_trend"].get("short_term_direction")
            if direction:
                no_dir[direction] = no_dir.get(direction, 0) + 1
    
    print(f"FAST: {fast_dir}")
    print(f"SL_HIT: {sl_dir}")
    print(f"NO_REVERSAL: {no_dir}")
    
    fast_up_pct = fast_dir.get("UP", 0) / sum(fast_dir.values()) * 100 if fast_dir else 0
    print(f"\nInterpretation: {'CONTINUATION' if fast_up_pct > 50 else 'REVERSAL'}")
    
    # Summary
    print(f"\n{'=' * 100}")
    print("HYPOTHESIS VERIFICATION SUMMARY")
    print(f"{'=' * 100}")
    
    continuation_score = 0
    reversal_score = 0
    
    if mean(fast_pm) > 0:
        continuation_score += 1
    else:
        reversal_score += 1
    
    if mean(fast_rp) > 0.5:
        continuation_score += 1
    else:
        reversal_score += 1
    
    if mean(fast_slope) > 0:
        continuation_score += 1
    else:
        reversal_score += 1
    
    if sum(fast_above)/len(fast_above) > 0.5:
        continuation_score += 1
    else:
        reversal_score += 1
    
    if fast_up_pct > 50:
        continuation_score += 1
    else:
        reversal_score += 1
    
    print(f"\nCONTINUATION evidence: {continuation_score}/5")
    print(f"REVERSAL evidence: {reversal_score}/5")
    
    print(f"\nCONCLUSION: {'CONTINUATION pattern supported' if continuation_score > reversal_score else 'REVERSAL pattern supported'}")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
