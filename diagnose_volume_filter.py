#!/usr/bin/env python3
"""
Diagnose why FLOW-USDT was sent despite failing volume filter.

The candle has Volume Ratio = 1.00x but needs >= 1.5x.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def main():
    """Check volume filter calculation for FLOW-USDT."""
    print("=" * 80)
    print("DIAGNOSING VOLUME FILTER FOR FLOW-USDT")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    
    # Fetch more candles to get 48 previous
    start_time = int((target_time - timedelta(days=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Find the target candle
    target_index = -1
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == target_time:
            target_index = i
            break
    
    if target_index == -1:
        print("Target candle not found")
        return
    
    print(f"\nTarget candle index: {target_index}")
    
    # Check if we have 48 previous candles
    if target_index < 48:
        print(f"Not enough previous candles: {target_index} < 48")
        return
    
    # Get previous 48 volumes
    previous_volumes = [float(klines[j]['volume']) for j in range(target_index - 48, target_index)]
    current_volume = float(klines[target_index]['volume'])
    
    print(f"\nPrevious 48 volumes:")
    for j in range(target_index - 48, target_index):
        kline_time = int(klines[j]['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        vol = float(klines[j]['volume'])
        print(f"  [{j}] {kline_datetime}: {vol:.0f}")
    
    print(f"\nCurrent candle (index {target_index}):")
    kline_datetime = datetime.fromtimestamp(int(klines[target_index]['time']) / 1000, tz=UTC)
    print(f"  {kline_datetime}: {current_volume:.0f}")
    
    max_previous = max(previous_volumes)
    volume_ratio = current_volume / max_previous if max_previous > 0 else 0.0
    
    print(f"\nVolume Filter Calculation:")
    print(f"  Current Volume: {current_volume:.0f}")
    print(f"  Max Previous 48: {max_previous:.0f}")
    print(f"  Volume Ratio: {volume_ratio:.2f}x")
    print(f"  Threshold: 1.5x")
    print(f"  Qualified: {volume_ratio >= 1.5}")
    
    # Now check what find_10_signals_v6.py would do
    print(f"\n" + "=" * 80)
    print("SIMULATING find_10_signals_v6.py LOGIC")
    print("=" * 80)
    
    # The script iterates from end backwards
    print(f"\nScript iterates from index {len(klines) - 1} down to 48")
    
    # Find what happens when it reaches the target candle
    for i in range(len(klines) - 1, 48, -1):
        kline_time = int(klines[i]['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == target_time:
            print(f"\nAt index {i} (target candle):")
            
            # Get previous volumes as the script does
            script_previous_volumes = [float(klines[j]['volume']) for j in range(i - 48, i)]
            script_current_volume = float(klines[i]['volume'])
            
            script_max_previous = max(script_previous_volumes)
            script_volume_ratio = script_current_volume / script_max_previous if script_max_previous > 0 else 0.0
            
            print(f"  Previous volumes range: [{i - 48}, {i})")
            print(f"  Current Volume: {script_current_volume:.0f}")
            print(f"  Max Previous 48: {script_max_previous:.0f}")
            print(f"  Volume Ratio: {script_volume_ratio:.2f}x")
            print(f"  Volume Qualified: {script_volume_ratio >= 1.5}")
            
            # Check if the script would have enough previous candles
            if len(script_previous_volumes) < 48:
                print(f"  !!! ERROR: Not enough previous candles ({len(script_previous_volumes)} < 48)")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
