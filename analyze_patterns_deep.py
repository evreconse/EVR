#!/usr/bin/env python3
"""
Deep pattern analysis of 29 found manual signals.
"""

import json
from collections import defaultdict


def load_signals():
    """Load the analyzed signals from JSON."""
    with open("manual_signals_analysis.json", "r") as f:
        data = json.load(f)
    return data["found_signals"]


def analyze_patterns(signals):
    """Perform deep pattern analysis."""
    print("=" * 100)
    print("DEEP PATTERN ANALYSIS")
    print("=" * 100)
    
    # 1. Analyze Lower Wick / Body ratio ranges
    lw_body_ratios = [sig["geometry"]["lower_wick_body_ratio"] for sig in signals]
    
    print("\n1. LOWER WICK / BODY RATIO DISTRIBUTION:")
    print("-" * 100)
    
    ranges = [
        (0, 0.5, "0.0 - 0.5x"),
        (0.5, 1.0, "0.5 - 1.0x"),
        (1.0, 1.5, "1.0 - 1.5x"),
        (1.5, 2.0, "1.5 - 2.0x"),
        (2.0, 3.0, "2.0 - 3.0x"),
        (3.0, 5.0, "3.0 - 5.0x"),
        (5.0, float('inf'), "5.0x+"),
    ]
    
    for min_r, max_r, label in ranges:
        count = sum(1 for r in lw_body_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    # 2. Analyze Upper Wick / Body ratio
    uw_body_ratios = [sig["geometry"]["upper_wick_body_ratio"] for sig in signals]
    
    print("\n2. UPPER WICK / BODY RATIO DISTRIBUTION:")
    print("-" * 100)
    
    for min_r, max_r, label in ranges:
        count = sum(1 for r in uw_body_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    # 3. Analyze Body / Range ratio
    body_range_ratios = [sig["geometry"]["body_range_ratio"] for sig in signals]
    
    print("\n3. BODY / RANGE RATIO DISTRIBUTION:")
    print("-" * 100)
    
    ranges_br = [
        (0, 0.1, "0 - 10%"),
        (0.1, 0.2, "10 - 20%"),
        (0.2, 0.3, "20 - 30%"),
        (0.3, 0.4, "30 - 40%"),
        (0.4, 0.5, "40 - 50%"),
        (0.5, 1.0, "50%+"),
    ]
    
    for min_r, max_r, label in ranges_br:
        count = sum(1 for r in body_range_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    # 4. Analyze Lower Wick / Range ratio
    lw_range_ratios = [sig["geometry"]["lower_wick_range_ratio"] for sig in signals]
    
    print("\n4. LOWER WICK / RANGE RATIO DISTRIBUTION:")
    print("-" * 100)
    
    for min_r, max_r, label in ranges_br:
        count = sum(1 for r in lw_range_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    # 5. Analyze Volume Ratio ranges
    vol_ratios = [sig["volume_metrics"]["volume_ratio_previous"] for sig in signals 
                  if sig["volume_metrics"]["previous_candle_volume"] > 0]
    
    print("\n5. VOLUME RATIO (Current / Previous) DISTRIBUTION:")
    print("-" * 100)
    
    ranges_vol = [
        (0, 0.5, "0.0 - 0.5x"),
        (0.5, 1.0, "0.5 - 1.0x"),
        (1.0, 1.5, "1.0 - 1.5x"),
        (1.5, 2.0, "1.5 - 2.0x"),
        (2.0, 3.0, "2.0 - 3.0x"),
        (3.0, 5.0, "3.0 - 5.0x"),
        (5.0, float('inf'), "5.0x+"),
    ]
    
    for min_r, max_r, label in ranges_vol:
        count = sum(1 for r in vol_ratios if min_r <= r < max_r)
        pct = count / len(vol_ratios) * 100
        print(f"  {label:<15} {count:2d}/{len(vol_ratios)} ({pct:5.1f}%)")
    
    # 6. Combined conditions analysis
    print("\n6. COMBINED CONDITIONS ANALYSIS:")
    print("-" * 100)
    
    # Current LW-001: Red + LW/Body >= 2.0
    lw001_count = sum(1 for sig in signals 
                      if sig["geometry"]["is_red"] and sig["geometry"]["lower_wick_body_ratio"] >= 2.0)
    print(f"  Current LW-001 (Red + LW/Body >= 2.0): {lw001_count}/{len(signals)} ({lw001_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Body >= 1.0
    lw1_count = sum(1 for sig in signals 
                    if sig["geometry"]["is_red"] and sig["geometry"]["lower_wick_body_ratio"] >= 1.0)
    print(f"  Red + LW/Body >= 1.0: {lw1_count}/{len(signals)} ({lw1_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Body >= 1.5
    lw15_count = sum(1 for sig in signals 
                     if sig["geometry"]["is_red"] and sig["geometry"]["lower_wick_body_ratio"] >= 1.5)
    print(f"  Red + LW/Body >= 1.5: {lw15_count}/{len(signals)} ({lw15_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Range >= 0.3
    lw_range_count = sum(1 for sig in signals 
                         if sig["geometry"]["is_red"] and sig["geometry"]["lower_wick_range_ratio"] >= 0.3)
    print(f"  Red + LW/Range >= 30%: {lw_range_count}/{len(signals)} ({lw_range_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Range >= 0.4
    lw_range40_count = sum(1 for sig in signals 
                          if sig["geometry"]["is_red"] and sig["geometry"]["lower_wick_range_ratio"] >= 0.4)
    print(f"  Red + LW/Range >= 40%: {lw_range40_count}/{len(signals)} ({lw_range40_count/len(signals)*100:.1f}%)")
    
    # Red + Volume >= 1.5x
    vol15_count = sum(1 for sig in signals 
                      if sig["geometry"]["is_red"] and sig["volume_metrics"]["volume_ratio_previous"] >= 1.5)
    print(f"  Red + Volume >= 1.5x: {vol15_count}/{len(signals)} ({vol15_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Body >= 1.0 + Volume >= 1.5x
    combo1_count = sum(1 for sig in signals 
                       if sig["geometry"]["is_red"] 
                       and sig["geometry"]["lower_wick_body_ratio"] >= 1.0
                       and sig["volume_metrics"]["volume_ratio_previous"] >= 1.5)
    print(f"  Red + LW/Body >= 1.0 + Volume >= 1.5x: {combo1_count}/{len(signals)} ({combo1_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Body >= 1.5 + Volume >= 1.5x
    combo2_count = sum(1 for sig in signals 
                       if sig["geometry"]["is_red"] 
                       and sig["geometry"]["lower_wick_body_ratio"] >= 1.5
                       and sig["volume_metrics"]["volume_ratio_previous"] >= 1.5)
    print(f"  Red + LW/Body >= 1.5 + Volume >= 1.5x: {combo2_count}/{len(signals)} ({combo2_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Range >= 0.3 + Volume >= 1.5x
    combo3_count = sum(1 for sig in signals 
                       if sig["geometry"]["is_red"] 
                       and sig["geometry"]["lower_wick_range_ratio"] >= 0.3
                       and sig["volume_metrics"]["volume_ratio_previous"] >= 1.5)
    print(f"  Red + LW/Range >= 30% + Volume >= 1.5x: {combo3_count}/{len(signals)} ({combo3_count/len(signals)*100:.1f}%)")
    
    # Red + LW/Range >= 0.4 + Volume >= 1.5x
    combo4_count = sum(1 for sig in signals 
                       if sig["geometry"]["is_red"] 
                       and sig["geometry"]["lower_wick_range_ratio"] >= 0.4
                       and sig["volume_metrics"]["volume_ratio_previous"] >= 1.5)
    print(f"  Red + LW/Range >= 40% + Volume >= 1.5x: {combo4_count}/{len(signals)} ({combo4_count/len(signals)*100:.1f}%)")
    
    # 7. Group analysis by LW/Body ratio
    print("\n7. GROUPING BY LOWER WICK / BODY RATIO:")
    print("-" * 100)
    
    groups = {
        "Small LW/Body (0-1x)": [],
        "Medium LW/Body (1-2x)": [],
        "Large LW/Body (2-5x)": [],
        "Very Large LW/Body (5x+)": [],
    }
    
    for sig in signals:
        ratio = sig["geometry"]["lower_wick_body_ratio"]
        if ratio < 1.0:
            groups["Small LW/Body (0-1x)"].append(sig)
        elif ratio < 2.0:
            groups["Medium LW/Body (1-2x)"].append(sig)
        elif ratio < 5.0:
            groups["Large LW/Body (2-5x)"].append(sig)
        else:
            groups["Very Large LW/Body (5x+)"].append(sig)
    
    for group_name, group_signals in groups.items():
        if group_signals:
            print(f"\n  {group_name}: {len(group_signals)} signals")
            for sig in group_signals:
                print(f"    - {sig['symbol']}: LW/Body={sig['geometry']['lower_wick_body_ratio']:.2f}x, "
                      f"Vol Ratio={sig['volume_metrics']['volume_ratio_previous']:.2f}x")
    
    # 8. Check for green candles
    print("\n8. GREEN CANDLES ANALYSIS:")
    print("-" * 100)
    
    green_signals = [sig for sig in signals if sig["geometry"]["is_green"]]
    print(f"  Total green candles: {len(green_signals)}")
    
    for sig in green_signals:
        print(f"  - {sig['symbol']}: LW/Body={sig['geometry']['lower_wick_body_ratio']:.2f}x, "
              f"Vol Ratio={sig['volume_metrics']['volume_ratio_previous']:.2f}x")


def main():
    """Main analysis."""
    signals = load_signals()
    print(f"Loaded {len(signals)} signals from manual_signals_analysis.json")
    analyze_patterns(signals)


if __name__ == "__main__":
    main()
