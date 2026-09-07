#!/usr/bin/env python3
"""
Statistical analysis of corrected red candles.
"""

import json
from collections import defaultdict


def load_corrected_signals():
    """Load corrected signals from JSON."""
    with open("corrected_signals_analysis.json", "r") as f:
        data = json.load(f)
    return data["found_signals"]


def analyze_statistics(signals):
    """Perform statistical analysis on corrected signals."""
    print("=" * 120)
    print("STATISTICAL ANALYSIS OF CORRECTED RED CANDLES")
    print("=" * 120)
    print(f"Total signals: {len(signals)}")
    print()
    
    # 1. Lower Wick / Body Ratio
    lw_body_ratios = [sig["lower_wick_body_ratio"] for sig in signals]
    
    print("1. LOWER WICK / BODY RATIO DISTRIBUTION:")
    print("-" * 120)
    
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
    
    print(f"\n  Statistics:")
    print(f"    Average: {sum(lw_body_ratios) / len(lw_body_ratios):.2f}x")
    print(f"    Min: {min(lw_body_ratios):.2f}x")
    print(f"    Max: {max(lw_body_ratios):.2f}x")
    print(f"    >= 2.0x (current LW-001): {sum(1 for r in lw_body_ratios if r >= 2.0)}/{len(signals)} ({sum(1 for r in lw_body_ratios if r >= 2.0)/len(signals)*100:.1f}%)")
    
    # 2. Upper Wick / Body Ratio
    uw_body_ratios = [sig["upper_wick_body_ratio"] for sig in signals]
    
    print("\n2. UPPER WICK / BODY RATIO DISTRIBUTION:")
    print("-" * 120)
    
    for min_r, max_r, label in ranges:
        count = sum(1 for r in uw_body_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    print(f"\n  Statistics:")
    print(f"    Average: {sum(uw_body_ratios) / len(uw_body_ratios):.2f}x")
    print(f"    Min: {min(uw_body_ratios):.2f}x")
    print(f"    Max: {max(uw_body_ratios):.2f}x")
    
    # 3. Lower Wick / Range Ratio
    lw_range_ratios = [sig["lower_wick_range_ratio"] for sig in signals]
    
    print("\n3. LOWER WICK / RANGE RATIO DISTRIBUTION:")
    print("-" * 120)
    
    ranges_range = [
        (0, 0.1, "0 - 10%"),
        (0.1, 0.2, "10 - 20%"),
        (0.2, 0.3, "20 - 30%"),
        (0.3, 0.4, "30 - 40%"),
        (0.4, 0.5, "40 - 50%"),
        (0.5, 0.6, "50 - 60%"),
        (0.6, 0.7, "60 - 70%"),
        (0.7, 0.8, "70 - 80%"),
        (0.8, float('inf'), "80%+"),
    ]
    
    for min_r, max_r, label in ranges_range:
        count = sum(1 for r in lw_range_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    print(f"\n  Statistics:")
    print(f"    Average: {sum(lw_range_ratios) / len(lw_range_ratios):.2f}")
    print(f"    Min: {min(lw_range_ratios):.2f}")
    print(f"    Max: {max(lw_range_ratios):.2f}")
    print(f"    >= 30%: {sum(1 for r in lw_range_ratios if r >= 0.3)}/{len(signals)} ({sum(1 for r in lw_range_ratios if r >= 0.3)/len(signals)*100:.1f}%)")
    print(f"    >= 40%: {sum(1 for r in lw_range_ratios if r >= 0.4)}/{len(signals)} ({sum(1 for r in lw_range_ratios if r >= 0.4)/len(signals)*100:.1f}%)")
    print(f"    >= 50%: {sum(1 for r in lw_range_ratios if r >= 0.5)}/{len(signals)} ({sum(1 for r in lw_range_ratios if r >= 0.5)/len(signals)*100:.1f}%)")
    
    # 4. Body / Range Ratio
    body_range_ratios = [sig["body_range_ratio"] for sig in signals]
    
    print("\n4. BODY / RANGE RATIO DISTRIBUTION:")
    print("-" * 120)
    
    ranges_br = [
        (0, 0.1, "0 - 10%"),
        (0.1, 0.2, "10 - 20%"),
        (0.2, 0.3, "20 - 30%"),
        (0.3, 0.4, "30 - 40%"),
        (0.4, 0.5, "40 - 50%"),
        (0.5, float('inf'), "50%+"),
    ]
    
    for min_r, max_r, label in ranges_br:
        count = sum(1 for r in body_range_ratios if min_r <= r < max_r)
        pct = count / len(signals) * 100
        print(f"  {label:<15} {count:2d}/{len(signals)} ({pct:5.1f}%)")
    
    # 5. Volume Ratio
    vol_ratios = [sig["volume_ratio"] for sig in signals if sig["previous_volume"] > 0]
    
    print("\n5. VOLUME RATIO (Current / Previous) DISTRIBUTION:")
    print("-" * 120)
    
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
    
    print(f"\n  Statistics:")
    print(f"    Average: {sum(vol_ratios) / len(vol_ratios):.2f}x")
    print(f"    Min: {min(vol_ratios):.2f}x")
    print(f"    Max: {max(vol_ratios):.2f}x")
    print(f"    >= 1.5x: {sum(1 for r in vol_ratios if r >= 1.5)}/{len(vol_ratios)} ({sum(1 for r in vol_ratios if r >= 1.5)/len(vol_ratios)*100:.1f}%)")
    
    # 6. Combined conditions
    print("\n6. COMBINED CONDITIONS ANALYSIS:")
    print("-" * 120)
    
    # Current LW-001: Red + LW/Body >= 2.0
    lw001_count = sum(1 for sig in signals if sig["lower_wick_body_ratio"] >= 2.0)
    print(f"  Current LW-001 (LW/Body >= 2.0): {lw001_count}/{len(signals)} ({lw001_count/len(signals)*100:.1f}%)")
    
    # LW/Body >= 1.0
    lw1_count = sum(1 for sig in signals if sig["lower_wick_body_ratio"] >= 1.0)
    print(f"  LW/Body >= 1.0: {lw1_count}/{len(signals)} ({lw1_count/len(signals)*100:.1f}%)")
    
    # LW/Body >= 1.5
    lw15_count = sum(1 for sig in signals if sig["lower_wick_body_ratio"] >= 1.5)
    print(f"  LW/Body >= 1.5: {lw15_count}/{len(signals)} ({lw15_count/len(signals)*100:.1f}%)")
    
    # LW/Range >= 30%
    lw_range30_count = sum(1 for sig in signals if sig["lower_wick_range_ratio"] >= 0.3)
    print(f"  LW/Range >= 30%: {lw_range30_count}/{len(signals)} ({lw_range30_count/len(signals)*100:.1f}%)")
    
    # LW/Range >= 40%
    lw_range40_count = sum(1 for sig in signals if sig["lower_wick_range_ratio"] >= 0.4)
    print(f"  LW/Range >= 40%: {lw_range40_count}/{len(signals)} ({lw_range40_count/len(signals)*100:.1f}%)")
    
    # LW/Range >= 50%
    lw_range50_count = sum(1 for sig in signals if sig["lower_wick_range_ratio"] >= 0.5)
    print(f"  LW/Range >= 50%: {lw_range50_count}/{len(signals)} ({lw_range50_count/len(signals)*100:.1f}%)")
    
    # Volume >= 1.5x
    vol15_count = sum(1 for sig in signals if sig["volume_ratio"] >= 1.5)
    print(f"  Volume >= 1.5x: {vol15_count}/{len(signals)} ({vol15_count/len(signals)*100:.1f}%)")
    
    # Combined: LW/Body >= 1.0 + Volume >= 1.5x
    combo1_count = sum(1 for sig in signals 
                       if sig["lower_wick_body_ratio"] >= 1.0 and sig["volume_ratio"] >= 1.5)
    print(f"  LW/Body >= 1.0 + Volume >= 1.5x: {combo1_count}/{len(signals)} ({combo1_count/len(signals)*100:.1f}%)")
    
    # Combined: LW/Body >= 1.5 + Volume >= 1.5x
    combo2_count = sum(1 for sig in signals 
                       if sig["lower_wick_body_ratio"] >= 1.5 and sig["volume_ratio"] >= 1.5)
    print(f"  LW/Body >= 1.5 + Volume >= 1.5x: {combo2_count}/{len(signals)} ({combo2_count/len(signals)*100:.1f}%)")
    
    # Combined: LW/Range >= 30% + Volume >= 1.5x
    combo3_count = sum(1 for sig in signals 
                       if sig["lower_wick_range_ratio"] >= 0.3 and sig["volume_ratio"] >= 1.5)
    print(f"  LW/Range >= 30% + Volume >= 1.5x: {combo3_count}/{len(signals)} ({combo3_count/len(signals)*100:.1f}%)")
    
    # Combined: LW/Range >= 40% + Volume >= 1.5x
    combo4_count = sum(1 for sig in signals 
                       if sig["lower_wick_range_ratio"] >= 0.4 and sig["volume_ratio"] >= 1.5)
    print(f"  LW/Range >= 40% + Volume >= 1.5x: {combo4_count}/{len(signals)} ({combo4_count/len(signals)*100:.1f}%)")
    
    # Combined: LW/Range >= 50% + Volume >= 1.5x
    combo5_count = sum(1 for sig in signals 
                       if sig["lower_wick_range_ratio"] >= 0.5 and sig["volume_ratio"] >= 1.5)
    print(f"  LW/Range >= 50% + Volume >= 1.5x: {combo5_count}/{len(signals)} ({combo5_count/len(signals)*100:.1f}%)")
    
    # 7. Group analysis by LW/Body ratio
    print("\n7. GROUPING BY LOWER WICK / BODY RATIO:")
    print("-" * 120)
    
    groups = {
        "Small LW/Body (0-1x)": [],
        "Medium LW/Body (1-2x)": [],
        "Large LW/Body (2-5x)": [],
        "Very Large LW/Body (5x+)": [],
    }
    
    for sig in signals:
        ratio = sig["lower_wick_body_ratio"]
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
                print(f"    - {sig['symbol']}: LW/Body={sig['lower_wick_body_ratio']:.2f}x, "
                      f"LW/Range={sig['lower_wick_range_ratio']:.2f}, Vol Ratio={sig['volume_ratio']:.2f}x")


def main():
    """Main analysis."""
    signals = load_corrected_signals()
    print(f"Loaded {len(signals)} corrected signals from corrected_signals_analysis.json")
    analyze_statistics(signals)


if __name__ == "__main__":
    main()
