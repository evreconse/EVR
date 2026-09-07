#!/usr/bin/env python3
"""
Analyze post-signal performance for validation sample.

Research: Calculate MAE, time to targets, and classify behavior for validation sample.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
from statistics import mean, median
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def analyze_post_signal_performance(fetcher, signal):
    """Analyze detailed post-signal performance for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    signal_close = signal["close"]
    
    performance = {
        "max_up_pct": 0,
        "max_down_pct": 0,
        "time_to_1pct_candles": None,
        "time_to_2pct_candles": None,
        "time_to_3pct_candles": None,
        "max_adverse_before_1pct": 0,
        "max_adverse_before_2pct": 0,
        "max_adverse_before_3pct": 0,
        "max_adverse_overall": 0,
        "hit_sl_3pct": False,
        "candles_before_sl": None,
        "total_candles_analyzed": 0
    }
    
    try:
        # Get klines after signal time (4 hours forward = 16 candles)
        end_time = int((signal_time + timedelta(hours=4)).timestamp() * 1000)
        start_time = int(signal_time.timestamp() * 1000)
        
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines or len(klines) < 2:
            performance["error"] = "Not enough data"
            return performance
        
        # Find signal candle
        signal_idx = None
        for i, k in enumerate(klines):
            if abs(int(k['time']) - signal["timestamp_ms"]) < 900000:
                signal_idx = i
                break
        
        if signal_idx is None:
            performance["error"] = "Signal candle not found"
            return performance
        
        performance["total_candles_analyzed"] = len(klines) - signal_idx - 1
        
        # Analyze performance candle by candle
        for i in range(signal_idx + 1, len(klines)):
            k = klines[i]
            high = float(k['high'])
            low = float(k['low'])
            
            # Calculate moves from signal close
            up_move = (high - signal_close) / signal_close * 100
            down_move = (low - signal_close) / signal_close * 100
            
            performance["max_up_pct"] = max(performance["max_up_pct"], up_move)
            performance["max_down_pct"] = min(performance["max_down_pct"], down_move)
            performance["max_adverse_overall"] = max(performance["max_adverse_overall"], abs(down_move))
            
            # Track adverse before targets
            if performance["time_to_1pct_candles"] is None:
                performance["max_adverse_before_1pct"] = max(performance["max_adverse_before_1pct"], abs(down_move))
            if performance["time_to_2pct_candles"] is None:
                performance["max_adverse_before_2pct"] = max(performance["max_adverse_before_2pct"], abs(down_move))
            if performance["time_to_3pct_candles"] is None:
                performance["max_adverse_before_3pct"] = max(performance["max_adverse_before_3pct"], abs(down_move))
            
            # Check if SL hit
            if down_move <= -3.0 and not performance["hit_sl_3pct"]:
                performance["hit_sl_3pct"] = True
                performance["candles_before_sl"] = i - signal_idx
            
            # Track time to targets
            if performance["time_to_1pct_candles"] is None and up_move >= 1.0:
                performance["time_to_1pct_candles"] = i - signal_idx
            if performance["time_to_2pct_candles"] is None and up_move >= 2.0:
                performance["time_to_2pct_candles"] = i - signal_idx
            if performance["time_to_3pct_candles"] is None and up_move >= 3.0:
                performance["time_to_3pct_candles"] = i - signal_idx
        
        # If targets not reached, record final adverse
        if performance["time_to_1pct_candles"] is None:
            performance["max_adverse_before_1pct"] = performance["max_adverse_overall"]
        if performance["time_to_2pct_candles"] is None:
            performance["max_adverse_before_2pct"] = performance["max_adverse_overall"]
        if performance["time_to_3pct_candles"] is None:
            performance["max_adverse_before_3pct"] = performance["max_adverse_overall"]
        
    except Exception as e:
        performance["error"] = str(e)
    
    return performance


def classify_signal(performance):
    """Classify signal based on performance."""
    if "error" in performance:
        return "ERROR"
    
    if performance["hit_sl_3pct"]:
        return "SL_HIT"
    
    if performance["time_to_2pct_candles"] is None:
        # Didn't reach +2%
        if performance["max_up_pct"] >= 1.0:
            return "WEAK_REVERSAL"
        else:
            return "NO_REVERSAL"
    
    # Reached +2%
    if performance["time_to_2pct_candles"] <= 2:
        if performance["max_adverse_before_2pct"] < 1.0:
            return "VERY_FAST"
        else:
            return "FAST"
    elif performance["time_to_2pct_candles"] <= 4:
        if performance["max_adverse_before_2pct"] < 2.0:
            return "FAST"
        else:
            return "SLOW"
    else:
        return "SLOW"


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("VALIDATION SAMPLE POST-SIGNAL PERFORMANCE ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load candidates
    with open("validation_sample.json", "r") as f:
        candidates = json.load(f)
    
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze performance
    fetcher = BingXFetcher()
    print("\nAnalyzing post-signal performance...")
    
    for i, candidate in enumerate(candidates, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        performance = await analyze_post_signal_performance(fetcher, candidate)
        candidate["performance"] = performance
        candidate["category"] = classify_signal(performance)
    
    # Classification summary
    categories = {}
    for candidate in candidates:
        cat = candidate["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(candidate)
    
    print(f"\n{'=' * 100}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'=' * 100}")
    
    for cat, signals in sorted(categories.items()):
        print(f"\n{cat}: {len(signals)} signals ({len(signals)/len(candidates)*100:.1f}%)")
        
        if signals:
            max_ups = [s["performance"]["max_up_pct"] for s in signals if "max_up_pct" in s["performance"]]
            if max_ups:
                print(f"  Max Up: mean={mean(max_ups):.2f}%, median={median(max_ups):.2f}%")
            
            if cat == "SL_HIT":
                sl_times = [s["performance"]["candles_before_sl"] for s in signals if "candles_before_sl" in s["performance"]]
                if sl_times:
                    print(f"  Time to SL: mean={mean(sl_times):.1f} candles, median={median(sl_times):.1f} candles")
            
            if cat in ["FAST", "VERY_FAST", "SLOW"]:
                times_2pct = [s["performance"]["time_to_2pct_candles"] for s in signals if "time_to_2pct_candles" in s["performance"]]
                if times_2pct:
                    print(f"  Time to +2%: mean={mean(times_2pct):.1f} candles, median={median(times_2pct):.1f} candles")
                
                maes = [s["performance"]["max_adverse_before_2pct"] for s in signals if "max_adverse_before_2pct" in s["performance"]]
                if maes:
                    print(f"  MAE before +2%: mean={mean(maes):.2f}%, median={median(maes):.2f}%")
    
    # Save results
    results = {
        "candidates": candidates,
        "classification": {k: len(v) for k, v in categories.items()}
    }
    
    with open("validation_performance_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to validation_performance_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
