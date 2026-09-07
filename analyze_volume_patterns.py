#!/usr/bin/env python3
"""
Analyze volume patterns for large sample of candidates.

Research: Analyze previous candles, spikes, capitulation patterns.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
from statistics import mean, median


def main():
    """Main analysis function."""
    print("=" * 100)
    print("VOLUME PATTERNS ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load analysis results
    with open("large_sample_context_analysis.json", "r") as f:
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
    
    # Compare volume patterns by category
    print(f"\n{'=' * 100}")
    print("VOLUME PATTERNS BY CATEGORY")
    print(f"{'=' * 100}")
    
    for cat, signals in sorted(categories.items()):
        if not signals:
            continue
        
        print(f"\n{cat} ({len(signals)} signals):")
        
        # Signal candle volume ratio
        vol_ratios = [s.get("volume_ratio", 0) for s in signals if "volume_ratio" in s]
        if vol_ratios:
            print(f"  Signal volume ratio: mean={mean(vol_ratios):.4f}, median={median(vol_ratios):.4f}")
        
        # Previous volume analysis
        avg_vol_5 = []
        avg_vol_10 = []
        current_vol = []
        
        for s in signals:
            if "pre_signal_context" in s and "volume_analysis" in s["pre_signal_context"]:
                va = s["pre_signal_context"]["volume_analysis"]
                if "avg_volume_5" in va:
                    avg_vol_5.append(va["avg_volume_5"])
                if "avg_volume_10" in va:
                    avg_vol_10.append(va["avg_volume_10"])
                if "current_volume" in va:
                    current_vol.append(va["current_volume"])
        
        if avg_vol_5:
            print(f"  Avg volume (5 candles): mean={mean(avg_vol_5):.0f}, median={median(avg_vol_5):.0f}")
        if avg_vol_10:
            print(f"  Avg volume (10 candles): mean={mean(avg_vol_10):.0f}, median={median(avg_vol_10):.0f}")
        if current_vol:
            print(f"  Current volume: mean={mean(current_vol):.0f}, median={median(current_vol):.0f}")
        
        # Calculate volume spike ratio (current / avg_10)
        spike_ratios = []
        for s in signals:
            if "pre_signal_context" in s and "volume_analysis" in s["pre_signal_context"]:
                va = s["pre_signal_context"]["volume_analysis"]
                if "avg_volume_10" in va and "current_volume" in va and va["avg_volume_10"] > 0:
                    spike_ratios.append(va["current_volume"] / va["avg_volume_10"])
        
        if spike_ratios:
            print(f"  Volume spike ratio (current/avg_10): mean={mean(spike_ratios):.4f}, median={median(spike_ratios):.4f}")
    
    # Focus on FAST vs SL_HIT comparison
    print(f"\n{'=' * 100}")
    print("FAST vs SL_HIT VOLUME COMPARISON")
    print(f"{'=' * 100}")
    
    fast_signals = categories.get("VERY_FAST", []) + categories.get("FAST", [])
    sl_hit_signals = categories.get("SL_HIT", [])
    
    print(f"\nFAST/VERY_FAST ({len(fast_signals)} signals) vs SL_HIT ({len(sl_hit_signals)} signals)")
    
    # Signal volume ratio
    fast_vol = [s.get("volume_ratio", 0) for s in fast_signals if "volume_ratio" in s]
    sl_vol = [s.get("volume_ratio", 0) for s in sl_hit_signals if "volume_ratio" in s]
    
    if fast_vol and sl_vol:
        print(f"\nSignal volume ratio:")
        print(f"  FAST: mean={mean(fast_vol):.4f}, median={median(fast_vol):.4f}")
        print(f"  SL_HIT: mean={mean(sl_vol):.4f}, median={median(sl_vol):.4f}")
    
    # Volume spike ratio
    fast_spike = []
    sl_spike = []
    for s in fast_signals:
        if "pre_signal_context" in s and "volume_analysis" in s["pre_signal_context"]:
            va = s["pre_signal_context"]["volume_analysis"]
            if "avg_volume_10" in va and "current_volume" in va and va["avg_volume_10"] > 0:
                fast_spike.append(va["current_volume"] / va["avg_volume_10"])
    for s in sl_hit_signals:
        if "pre_signal_context" in s and "volume_analysis" in s["pre_signal_context"]:
            va = s["pre_signal_context"]["volume_analysis"]
            if "avg_volume_10" in va and "current_volume" in va and va["avg_volume_10"] > 0:
                sl_spike.append(va["current_volume"] / va["avg_volume_10"])
    
    if fast_spike and sl_spike:
        print(f"\nVolume spike ratio (current/avg_10):")
        print(f"  FAST: mean={mean(fast_spike):.4f}, median={median(fast_spike):.4f}")
        print(f"  SL_HIT: mean={mean(sl_spike):.4f}, median={median(sl_spike):.4f}")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
