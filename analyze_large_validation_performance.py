#!/usr/bin/env python3
"""
Analyze post-signal performance for large validation sample with TP +3% / SL -3% model.

Research: Calculate detailed performance metrics for TP +3% / SL -3% model.

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


async def analyze_post_signal_performance_tp_sl(fetcher, signal):
    """Analyze detailed post-signal performance with TP +3% / SL -3% model."""
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
        "hit_tp_3pct": False,
        "candles_before_sl": None,
        "candles_before_tp": None,
        "hit_sl_before_tp": False,
        "hit_tp_before_sl": False,
        "total_candles_analyzed": 0
    }
    
    try:
        # Get klines after signal time (6 hours forward = 24 candles)
        end_time = int((signal_time + timedelta(hours=6)).timestamp() * 1000)
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
                if not performance["hit_tp_3pct"]:
                    performance["hit_sl_before_tp"] = True
            
            # Check if TP hit
            if up_move >= 3.0 and not performance["hit_tp_3pct"]:
                performance["hit_tp_3pct"] = True
                performance["candles_before_tp"] = i - signal_idx
                if not performance["hit_sl_3pct"]:
                    performance["hit_tp_before_sl"] = True
            
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


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("LARGE VALIDATION SAMPLE POST-SIGNAL PERFORMANCE (TP +3% / SL -3%)")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load candidates
    with open("large_validation_sample.json", "r") as f:
        candidates = json.load(f)
    
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze performance
    fetcher = BingXFetcher()
    print("\nAnalyzing post-signal performance...")
    
    for i, candidate in enumerate(candidates, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        performance = await analyze_post_signal_performance_tp_sl(fetcher, candidate)
        candidate["performance"] = performance
    
    # Classification summary
    hit_tp_before_sl = [c for c in candidates if c["performance"].get("hit_tp_before_sl", False)]
    hit_sl_before_tp = [c for c in candidates if c["performance"].get("hit_sl_before_tp", False)]
    hit_tp = [c for c in candidates if c["performance"].get("hit_tp_3pct", False)]
    hit_sl = [c for c in candidates if c["performance"].get("hit_sl_3pct", False)]
    neither = [c for c in candidates if not c["performance"].get("hit_tp_3pct", False) and not c["performance"].get("hit_sl_3pct", False)]
    
    print(f"\n{'=' * 100}")
    print("PERFORMANCE SUMMARY (TP +3% / SL -3%)")
    print(f"{'=' * 100}")
    
    print(f"\nTotal signals: {len(candidates)}")
    print(f"Hit TP before SL: {len(hit_tp_before_sl)} ({len(hit_tp_before_sl)/len(candidates)*100:.1f}%)")
    print(f"Hit SL before TP: {len(hit_sl_before_tp)} ({len(hit_sl_before_tp)/len(candidates)*100:.1f}%)")
    print(f"Hit TP (overall): {len(hit_tp)} ({len(hit_tp)/len(candidates)*100:.1f}%)")
    print(f"Hit SL (overall): {len(hit_sl)} ({len(hit_sl)/len(candidates)*100:.1f}%)")
    print(f"Neither TP nor SL: {len(neither)} ({len(neither)/len(candidates)*100:.1f}%)")
    
    # Calculate metrics for TP before SL group
    if hit_tp_before_sl:
        times_2pct = [c["performance"]["time_to_2pct_candles"] for c in hit_tp_before_sl if c["performance"]["time_to_2pct_candles"] is not None]
        times_3pct = [c["performance"]["time_to_3pct_candles"] for c in hit_tp_before_sl if c["performance"]["time_to_3pct_candles"] is not None]
        maes_2pct = [c["performance"]["max_adverse_before_2pct"] for c in hit_tp_before_sl if c["performance"]["time_to_2pct_candles"] is not None]
        maes_3pct = [c["performance"]["max_adverse_before_3pct"] for c in hit_tp_before_sl if c["performance"]["time_to_3pct_candles"] is not None]
        
        print(f"\nTP before SL group metrics:")
        if times_2pct:
            print(f"  Time to +2%: mean={mean(times_2pct):.1f}, median={median(times_2pct):.1f} candles")
        if times_3pct:
            print(f"  Time to +3%: mean={mean(times_3pct):.1f}, median={median(times_3pct):.1f} candles")
        if maes_2pct:
            print(f"  MAE before +2%: mean={mean(maes_2pct):.2f}%, median={median(maes_2pct):.2f}%")
        if maes_3pct:
            print(f"  MAE before +3%: mean={mean(maes_3pct):.2f}%, median={median(maes_3pct):.2f}%")
    
    # Save results
    results = {
        "candidates": candidates,
        "summary": {
            "total": len(candidates),
            "hit_tp_before_sl": len(hit_tp_before_sl),
            "hit_sl_before_tp": len(hit_sl_before_tp),
            "hit_tp": len(hit_tp),
            "hit_sl": len(hit_sl),
            "neither": len(neither)
        }
    }
    
    with open("large_validation_performance.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to large_validation_performance.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
