#!/usr/bin/env python3
"""
Diagnose the data mismatch between what was reported and what's in BingX.

Report showed:
Open: 0.029750
High: 0.029750
Low: 0.029720
Close: 0.029750
Body: 0.000000
Lower Wick: 0.000030
Upper Wick: 0.000000

BingX actual:
Open: 0.029760
High: 0.029900
Low: 0.029720
Close: 0.029750

There's a DATA MISMATCH. The Open and High values are different.
This means the historical search is fetching one candle but storing/displaying different values.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def main():
    """Check if there's a data mismatch in the historical search."""
    print("=" * 80)
    print("DIAGNOSING DATA MISMATCH")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    target_timestamp_ms = int(target_time.timestamp() * 1000)
    
    print(f"\nTarget Time UTC: {target_time}")
    print(f"Target Timestamp (ms): {target_timestamp_ms}")
    
    # Fetch klines
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"\nFetched {len(klines)} klines")
    
    # Find the candle at the exact timestamp
    for kline in klines:
        kline_time = int(kline['time'])
        
        if kline_time == target_timestamp_ms:
            print("\n" + "=" * 80)
            print("BINGX ACTUAL DATA")
            print("=" * 80)
            print(f"Open:  {float(kline['open']):.6f}")
            print(f"High:  {float(kline['high']):.6f}")
            print(f"Low:   {float(kline['low']):.6f}")
            print(f"Close: {float(kline['close']):.6f}")
            
            print("\n" + "=" * 80)
            print("REPORT DATA (from previous report)")
            print("=" * 80)
            print(f"Open:  0.029750")
            print(f"High:  0.029750")
            print(f"Low:   0.029720")
            print(f"Close: 0.029750")
            
            print("\n" + "=" * 80)
            print("MISMATCH ANALYSIS")
            print("=" * 80)
            
            open_mismatch = abs(float(kline['open']) - 0.029750)
            high_mismatch = abs(float(kline['high']) - 0.029750)
            low_mismatch = abs(float(kline['low']) - 0.029720)
            close_mismatch = abs(float(kline['close']) - 0.029750)
            
            print(f"Open mismatch:  {open_mismatch:.6f}")
            print(f"High mismatch:  {high_mismatch:.6f}")
            print(f"Low mismatch:   {low_mismatch:.6f}")
            print(f"Close mismatch: {close_mismatch:.6f}")
            
            if open_mismatch > 0.000001 or high_mismatch > 0.000001:
                print("\n!!! CRITICAL DATA MISMATCH DETECTED !!!")
                print("The historical search is using different OHLC values than BingX.")
                print("This means the signal finding script has a bug in data handling.")
            else:
                print("\nNo significant mismatch found.")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
