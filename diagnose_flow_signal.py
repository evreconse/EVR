#!/usr/bin/env python3
"""
Diagnose the FLOW-USDT signal that was sent in the previous batch.

From the report:
Signal #4: FLOW-USDT
Time MSK: 10.08.2026 10:15 MSK
Time UTC: 10.08.2026 07:15 UTC
Open: 0.029750
High: 0.029750
Low: 0.029720
Close: 0.029750
Body: 0.000000
Lower Wick: 0.000030
Upper Wick: 0.000000
Wick/Body: 3.00x

This is suspicious: Body = 0.000000 but Wick/Body = 3.00x is impossible.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def main():
    """Fetch the exact FLOW-USDT candle from BingX."""
    print("=" * 80)
    print("DIAGNOSING FLOW-USDT SIGNAL")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    # Convert to timestamp
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    target_timestamp_ms = int(target_time.timestamp() * 1000)
    
    print(f"\nTarget Time UTC: {target_time}")
    print(f"Target Timestamp (ms): {target_timestamp_ms}")
    
    # Fetch klines around that time
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    print(f"Fetching FLOW-USDT klines from {datetime.fromtimestamp(start_time/1000, tz=UTC)} to {datetime.fromtimestamp(end_time/1000, tz=UTC)}")
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Find the candle at the exact timestamp
    found = False
    for kline in klines:
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_time == target_timestamp_ms:
            found = True
            print("\n" + "=" * 80)
            print("FOUND EXACT CANDLE")
            print("=" * 80)
            print(f"Symbol: FLOW-USDT")
            print(f"Timestamp UTC: {kline_datetime}")
            print(f"Timestamp MSK: {kline_datetime.replace(hour=(kline_datetime.hour + 3) % 24)}")
            print(f"\nRAW DATA FROM BINGX:")
            print(f"Open:  {float(kline['open']):.6f}")
            print(f"High:  {float(kline['high']):.6f}")
            print(f"Low:   {float(kline['low']):.6f}")
            print(f"Close: {float(kline['close']):.6f}")
            print(f"Volume: {float(kline['volume']):.0f}")
            
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            
            # Manual calculation
            print("\n" + "=" * 80)
            print("MANUAL CALCULATION")
            print("=" * 80)
            
            is_red = close_price < open_price
            print(f"\nRED CANDLE:")
            print(f"Close < Open = {is_red}")
            print(f"  {close_price:.6f} < {open_price:.6f} = {is_red}")
            
            body = open_price - close_price if is_red else 0.0
            print(f"\nBODY:")
            print(f"Open - Close = {open_price:.6f} - {close_price:.6f} = {body:.6f}")
            
            lower_wick = close_price - low_price
            print(f"\nLOWER WICK:")
            print(f"Close - Low = {close_price:.6f} - {low_price:.6f} = {lower_wick:.6f}")
            
            upper_wick = high_price - open_price
            print(f"\nUPPER WICK:")
            print(f"High - Open = {high_price:.6f} - {open_price:.6f} = {upper_wick:.6f}")
            
            if body > 0:
                ratio = lower_wick / body
                print(f"\nLOWER WICK / BODY:")
                print(f"{lower_wick:.6f} / {body:.6f} = {ratio:.2f}x")
            else:
                print(f"\nLOWER WICK / BODY:")
                print(f"Cannot calculate - body is {body:.6f}")
                ratio = 0.0
            
            print(f"\nLOWER WICK >= 2 * BODY:")
            if body > 0:
                print(f"{lower_wick:.6f} >= 2 * {body:.6f} = {lower_wick:.6f} >= {2 * body:.6f} = {lower_wick >= 2 * body}")
            else:
                print(f"Cannot check - body is {body:.6f}")
            
            print(f"\nFINAL QUALIFICATION:")
            qualified = is_red and body > 0 and lower_wick > 0 and lower_wick >= 2 * body
            print(f"qualified = {is_red} and {body > 0} and {lower_wick > 0} and {lower_wick >= 2 * body}")
            print(f"qualified = {qualified}")
            
            break
    
    if not found:
        print("\nCandle not found at exact timestamp.")
        print("\nSearching for nearby candles...")
        for kline in klines:
            kline_time = int(kline['time'])
            kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
            
            if abs(kline_time - target_timestamp_ms) <= 15 * 60 * 1000:  # Within 15 minutes
                print(f"\nNearby candle at {kline_datetime}:")
                print(f"Open:  {float(kline['open']):.6f}")
                print(f"High:  {float(kline['high']):.6f}")
                print(f"Low:   {float(kline['low']):.6f}")
                print(f"Close: {float(kline['close']):.6f}")


if __name__ == "__main__":
    asyncio.run(main())
