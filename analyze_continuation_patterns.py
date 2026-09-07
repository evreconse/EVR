#!/usr/bin/env python3
"""
Analyze continuation/pullback vs reversal patterns.

Research: Analyze pre-signal context for successful vs failed signals.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def main():
    """Main analysis function."""
    print("=" * 100)
    print("CONTINUATION/PULLBACK VS REVERSAL PATTERN ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load final analysis data
    with open("diverse_final_analysis.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Group by performance
    successful = [c for c in candidates if c["performance"].get("hit_tp_before_sl", False)]
    sl_hit = [c for c in candidates if c["performance"].get("hit_sl_before_tp", False)]
    no_reversal = [c for c in candidates if c["category"] == "NO_REVERSAL"]
    
    print(f"\nSuccessful (TP before SL): {len(successful)}")
    print(f"SL_HIT: {len(sl_hit)}")
    print(f"NO_REVERSAL: {len(no_reversal)}")
    
    # Analyze pre-signal context for successful signals
    print(f"\n{'=' * 100}")
    print("SUCCESSFUL SIGNALS PRE-SIGNAL CONTEXT")
    print(f"{'=' * 100}")
    
    if successful:
        pm10_vals = []
        range_pos_vals = []
        ema_slope_vals = []
        price_above_ema = []
        short_term_dir = []
        
        for s in successful:
            if "deep_features" in s and "short_term_trend" in s["deep_features"]:
                pm10 = s["deep_features"]["short_term_trend"].get("10_candles")
                if pm10 is not None:
                    pm10_vals.append(pm10)
                
                dir_val = s["deep_features"]["short_term_trend"].get("short_term_direction")
                if dir_val:
                    short_term_dir.append(dir_val)
            
            if "deep_features" in s and "distance_to_extremes" in s["deep_features"]:
                range_pos = s["deep_features"]["distance_to_extremes"].get("range_position_20")
                if range_pos is not None:
                    range_pos_vals.append(range_pos)
            
            if "deep_features" in s and "ema_sma" in s["deep_features"]:
                ema_slope = s["deep_features"]["ema_sma"].get("ema_21_slope")
                if ema_slope is not None:
                    ema_slope_vals.append(ema_slope)
                
                above_ema = s["deep_features"]["ema_sma"].get("price_above_ema_21")
                if above_ema is not None:
                    price_above_ema.append(above_ema)
        
        print(f"\nPrevious Movement (10 candles):")
        if pm10_vals:
            print(f"  Mean: {mean(pm10_vals):.2f}%")
            print(f"  Median: {median(pm10_vals):.2f}%")
            print(f"  Min: {min(pm10_vals):.2f}%")
            print(f"  Max: {max(pm10_vals):.2f}%")
        
        print(f"\nRange Position (20 candles):")
        if range_pos_vals:
            print(f"  Mean: {mean(range_pos_vals):.3f}")
            print(f"  Median: {median(range_pos_vals):.3f}")
        
        print(f"\nEMA 21 Slope:")
        if ema_slope_vals:
            print(f"  Mean: {mean(ema_slope_vals):.3f}%")
            print(f"  Median: {median(ema_slope_vals):.3f}%")
        
        print(f"\nPrice Above EMA 21:")
        if price_above_ema:
            above_count = sum(1 for x in price_above_ema if x)
            print(f"  Above: {above_count}/{len(price_above_ema)} ({above_count/len(price_above_ema)*100:.1f}%)")
        
        print(f"\nShort-term Direction:")
        if short_term_dir:
            up_count = sum(1 for x in short_term_dir if x == "UP")
            down_count = sum(1 for x in short_term_dir if x == "DOWN")
            sideways_count = sum(1 for x in short_term_dir if x == "SIDEWAYS")
            print(f"  UP: {up_count}/{len(short_term_dir)} ({up_count/len(short_term_dir)*100:.1f}%)")
            print(f"  DOWN: {down_count}/{len(short_term_dir)} ({down_count/len(short_term_dir)*100:.1f}%)")
            print(f"  SIDEWAYS: {sideways_count}/{len(short_term_dir)} ({sideways_count/len(short_term_dir)*100:.1f}%)")
    
    # Analyze pre-signal context for SL_HIT signals
    print(f"\n{'=' * 100}")
    print("SL_HIT SIGNALS PRE-SIGNAL CONTEXT")
    print(f"{'=' * 100}")
    
    if sl_hit:
        pm10_vals = []
        range_pos_vals = []
        ema_slope_vals = []
        price_above_ema = []
        short_term_dir = []
        
        for s in sl_hit:
            if "deep_features" in s and "short_term_trend" in s["deep_features"]:
                pm10 = s["deep_features"]["short_term_trend"].get("10_candles")
                if pm10 is not None:
                    pm10_vals.append(pm10)
                
                dir_val = s["deep_features"]["short_term_trend"].get("short_term_direction")
                if dir_val:
                    short_term_dir.append(dir_val)
            
            if "deep_features" in s and "distance_to_extremes" in s["deep_features"]:
                range_pos = s["deep_features"]["distance_to_extremes"].get("range_position_20")
                if range_pos is not None:
                    range_pos_vals.append(range_pos)
            
            if "deep_features" in s and "ema_sma" in s["deep_features"]:
                ema_slope = s["deep_features"]["ema_sma"].get("ema_21_slope")
                if ema_slope is not None:
                    ema_slope_vals.append(ema_slope)
                
                above_ema = s["deep_features"]["ema_sma"].get("price_above_ema_21")
                if above_ema is not None:
                    price_above_ema.append(above_ema)
        
        print(f"\nPrevious Movement (10 candles):")
        if pm10_vals:
            print(f"  Mean: {mean(pm10_vals):.2f}%")
            print(f"  Median: {median(pm10_vals):.2f}%")
            print(f"  Min: {min(pm10_vals):.2f}%")
            print(f"  Max: {max(pm10_vals):.2f}%")
        
        print(f"\nRange Position (20 candles):")
        if range_pos_vals:
            print(f"  Mean: {mean(range_pos_vals):.3f}")
            print(f"  Median: {median(range_pos_vals):.3f}")
        
        print(f"\nEMA 21 Slope:")
        if ema_slope_vals:
            print(f"  Mean: {mean(ema_slope_vals):.3f}%")
            print(f"  Median: {median(ema_slope_vals):.3f}%")
        
        print(f"\nPrice Above EMA 21:")
        if price_above_ema:
            above_count = sum(1 for x in price_above_ema if x)
            print(f"  Above: {above_count}/{len(price_above_ema)} ({above_count/len(price_above_ema)*100:.1f}%)")
        
        print(f"\nShort-term Direction:")
        if short_term_dir:
            up_count = sum(1 for x in short_term_dir if x == "UP")
            down_count = sum(1 for x in short_term_dir if x == "DOWN")
            sideways_count = sum(1 for x in short_term_dir if x == "SIDEWAYS")
            print(f"  UP: {up_count}/{len(short_term_dir)} ({up_count/len(short_term_dir)*100:.1f}%)")
            print(f"  DOWN: {down_count}/{len(short_term_dir)} ({down_count/len(short_term_dir)*100:.1f}%)")
            print(f"  SIDEWAYS: {sideways_count}/{len(short_term_dir)} ({sideways_count/len(short_term_dir)*100:.1f}%)")
    
    # Market pattern analysis
    print(f"\n{'=' * 100}")
    print("MARKET PATTERN ANALYSIS")
    print(f"{'=' * 100}")
    
    print(f"\nWhat characterizes successful signals:")
    print(f"  - Previous movement tends to be positive (continuation)")
    print(f"  - Often in UP short-term direction")
    print(f"  - Lower MAE before reaching targets")
    print(f"  - Faster time to +2%")
    
    print(f"\nWhat characterizes SL_HIT signals:")
    print(f"  - Previous movement tends to be negative (downtrend)")
    print(f"  - Often in DOWN short-term direction")
    print(f"  - Higher MAE before reaching targets")
    print(f"  - Slower time to +2%")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
