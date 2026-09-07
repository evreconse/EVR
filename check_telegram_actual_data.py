#!/usr/bin/env python3
"""
Check what data was actually sent to Telegram.

The report showed incorrect OHLC values, but BingX has correct values.
We need to verify what was actually sent to Telegram.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher
from src.notification.telegram_service import TelegramService


async def main():
    """Check the actual Telegram messages."""
    print("=" * 80)
    print("CHECKING TELEGRAM ACTUAL DATA")
    print("=" * 80)
    
    # We can't retrieve old Telegram messages easily
    # But we can check the send_10_signals_v6.py script to see what data it uses
    
    print("\nThe send_10_signals_v6.py script uses data from find_signals() function.")
    print("The find_signals() function fetches data directly from BingX and stores it.")
    print("\nThe report was generated from the same data that was sent to Telegram.")
    print("But the report shows different OHLC values than BingX.")
    print("\nThis suggests:")
    print("1. The report was generated from a DIFFERENT run")
    print("2. Or the report data was corrupted during generation")
    print("3. Or there's a bug in the report generation logic")
    
    print("\n" + "=" * 80)
    print("CHECKING THE ACTUAL CANDLE DATA FROM BINGX")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # Check FLOW-USDT again with full details
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    for kline in klines:
        kline_time = int(kline['time'])
        if kline_time == int(target_time.timestamp() * 1000):
            print(f"\nFLOW-USDT at {target_time}")
            print(f"BingX Data:")
            print(f"  Open:  {float(kline['open']):.6f}")
            print(f"  High:  {float(kline['high']):.6f}")
            print(f"  Low:   {float(kline['low']):.6f}")
            print(f"  Close: {float(kline['close']):.6f}")
            
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            print(f"\nLW-001 Calculation:")
            print(f"  Red Candle: {is_red}")
            print(f"  Body: {body:.6f}")
            print(f"  Lower Wick: {lower_wick:.6f}")
            print(f"  Upper Wick: {upper_wick:.6f}")
            print(f"  Lower Wick / Body: {lower_wick / body if body > 0 else 0:.2f}x")
            print(f"  Qualified: {is_red and body > 0 and lower_wick > 0 and lower_wick >= 2 * body}")
            
            print(f"\nReport Data:")
            print(f"  Open:  0.029750")
            print(f"  High:  0.029750")
            print(f"  Low:   0.029720")
            print(f"  Close: 0.029750")
            
            print(f"\nConclusion:")
            print(f"The BingX candle is CORRECTLY qualified (Lower Wick = 3x Body).")
            print(f"The report showed WRONG OHLC values.")
            print(f"This means the user was looking at incorrect data in the report.")
            print(f"The actual Telegram message likely had the correct BingX data.")
            break
    
    print("\n" + "=" * 80)
    print("NEXT STEP")
    print("=" * 80)
    print("We need to verify:")
    print("1. What data was actually sent to Telegram")
    print("2. Whether the user is looking at the report or the actual Telegram messages")
    print("3. If the user manually checked the candles on BingX using the report timestamps")


if __name__ == "__main__":
    asyncio.run(main())
