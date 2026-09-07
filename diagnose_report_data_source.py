#!/usr/bin/env python3
"""
Check where the report data came from.

The report showed Open=0.029750 but BingX has Open=0.029760.
This suggests the report was generated from a different run or there's a data corruption issue.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def main():
    """Check all candles around the target time to see if any match the report data."""
    print("=" * 80)
    print("CHECKING ALL CANDLES AROUND TARGET TIME")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    
    # Fetch a wider range
    start_time = int((target_time - timedelta(days=1)).timestamp() * 1000)
    end_time = int((target_time + timedelta(days=1)).timestamp() * 1000)
    
    print(f"Fetching FLOW-USDT klines from {datetime.fromtimestamp(start_time/1000, tz=UTC)} to {datetime.fromtimestamp(end_time/1000, tz=UTC)}")
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=2000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Report data
    report_open = 0.029750
    report_high = 0.029750
    report_low = 0.029720
    report_close = 0.029750
    
    print(f"\nLooking for candle with Open={report_open:.6f}, High={report_high:.6f}, Low={report_low:.6f}, Close={report_close:.6f}")
    
    found_match = False
    for kline in klines:
        open_price = float(kline['open'])
        high_price = float(kline['high'])
        low_price = float(kline['low'])
        close_price = float(kline['close'])
        
        # Check if this matches the report data
        if (abs(open_price - report_open) < 0.000001 and
            abs(high_price - report_high) < 0.000001 and
            abs(low_price - report_low) < 0.000001 and
            abs(close_price - report_close) < 0.000001):
            
            found_match = True
            kline_time = int(kline['time'])
            kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
            
            print(f"\n!!! FOUND MATCHING CANDLE !!!")
            print(f"Time UTC: {kline_datetime}")
            print(f"Time MSK: {kline_datetime.replace(hour=(kline_datetime.hour + 3) % 24)}")
            print(f"Open:  {open_price:.6f}")
            print(f"High:  {high_price:.6f}")
            print(f"Low:   {low_price:.6f}")
            print(f"Close: {close_price:.6f}")
            
            # Calculate LW-001 for this candle
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            print(f"\nLW-001 CALCULATION FOR REPORT CANDLE:")
            print(f"Red Candle: {is_red}")
            print(f"Body: {body:.6f}")
            print(f"Lower Wick: {lower_wick:.6f}")
            print(f"Upper Wick: {upper_wick:.6f}")
            
            if body > 0:
                ratio = lower_wick / body
                print(f"Lower Wick / Body: {ratio:.2f}x")
                print(f"Lower Wick >= 2 * Body: {lower_wick >= 2 * body}")
            
            qualified = is_red and body > 0 and lower_wick > 0 and lower_wick >= 2 * body
            print(f"Qualified: {qualified}")
            
            break
    
    if not found_match:
        print("\nNo candle found matching the report data.")
        print("This means the report data was CORRUPTED or from a DIFFERENT RUN.")
        print("\nThe actual candle at the target time has different OHLC values.")
        print("This explains why the user saw incorrect signals - the report showed wrong data.")


if __name__ == "__main__":
    asyncio.run(main())
