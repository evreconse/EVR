#!/usr/bin/env python3
"""
Retry performance calculation for signals that failed.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def calculate_signal_performance(fetcher, signal):
    """Calculate post-signal performance for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    signal_close = signal["close"]
    
    # Get klines after signal (up to 100 candles = 25 hours)
    start_time = int(signal_time.timestamp() * 1000)
    end_time = int((signal_time + timedelta(hours=25)).timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines:
            return {
                "result": "ERROR",
                "time_to_result_candles": None,
                "max_adverse": None,
                "error": "No klines returned"
            }
        
        tp_3pct = signal_close * 1.03
        sl_3pct = signal_close * 0.97
        
        hit_tp = False
        hit_sl = False
        time_to_result = None
        max_adverse = 0
        
        for i, kline in enumerate(klines, 1):
            high = float(kline['high'])
            low = float(kline['low'])
            
            # Track max adverse
            drawdown = (signal_close - low) / signal_close * 100
            max_adverse = max(max_adverse, drawdown)
            
            # Check TP
            if high >= tp_3pct:
                hit_tp = True
                time_to_result = i
                break
            
            # Check SL
            if low <= sl_3pct:
                hit_sl = True
                time_to_result = i
                break
        
        if hit_tp:
            result = "TP"
        elif hit_sl:
            result = "SL"
        else:
            result = "NO_REVERSAL"
        
        return {
            "result": result,
            "time_to_result_candles": time_to_result,
            "max_adverse": max_adverse
        }
        
    except Exception as e:
        return {
            "result": "ERROR",
            "time_to_result_candles": None,
            "max_adverse": None,
            "error": str(e)
        }


async def main():
    """Main function."""
    print("=" * 100)
    print("RETRYING PERFORMANCE CALCULATION")
    print("=" * 100)
    
    # Load results
    with open("new_historical_signals.json", "r") as f:
        data = json.load(f)
    
    signals = data["signals"]
    
    print(f"\nLoaded {len(signals)} signals")
    
    # Count errors
    error_signals = [s for s in signals if s['performance']['result'] == "ERROR"]
    print(f"Signals with errors: {len(error_signals)}")
    
    # Retry performance calculation for error signals
    fetcher = BingXFetcher()
    
    for i, signal in enumerate(error_signals, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(error_signals)}")
        
        perf = await calculate_signal_performance(fetcher, signal)
        signal["performance"] = perf
    
    # Save updated results
    with open("new_historical_signals.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Performance retry complete. Results saved.")
    print(f"{'=' * 100}")
    
    # Print summary
    tp_count = sum(1 for s in signals if s['performance']['result'] == "TP")
    sl_count = sum(1 for s in signals if s['performance']['result'] == "SL")
    no_rev_count = sum(1 for s in signals if s['performance']['result'] == "NO_REVERSAL")
    error_count = sum(1 for s in signals if s['performance']['result'] == "ERROR")
    
    print(f"\nTotal signals: {len(signals)}")
    print(f"TP: {tp_count} ({tp_count/len(signals)*100:.1f}%)")
    print(f"SL: {sl_count} ({sl_count/len(signals)*100:.1f}%)")
    print(f"NO_REVERSAL: {no_rev_count} ({no_rev_count/len(signals)*100:.1f}%)")
    print(f"ERROR: {error_count}")


if __name__ == "__main__":
    asyncio.run(main())
