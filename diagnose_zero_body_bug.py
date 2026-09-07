#!/usr/bin/env python3
"""
Diagnose why signals with Body=0 are passing qualification.

LUNC-USDT and MEW-USDT show Body=0 but still have Wick/Body ratio.
This is mathematically impossible.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def main():
    """Check LUNC-USDT and MEW-USDT candles."""
    print("=" * 80)
    print("DIAGNOSING ZERO BODY BUG")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # LUNC-USDT at 2026-08-12 11:00 UTC
    lunc_time = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)
    lunc_start = int((lunc_time - timedelta(hours=2)).timestamp() * 1000)
    lunc_end = int((lunc_time + timedelta(hours=2)).timestamp() * 1000)
    
    print("\n1. CHECKING LUNC-USDT")
    print("-" * 80)
    
    klines = await fetcher.get_klines(
        symbol="LUNC-USDT",
        interval="15m",
        limit=1000,
        start_time=lunc_start,
        end_time=lunc_end
    )
    
    for kline in klines:
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == lunc_time:
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            
            print(f"Time: {kline_datetime}")
            print(f"Raw BingX: O={kline['open']} H={kline['high']} L={kline['low']} C={kline['close']}")
            print(f"Parsed: O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f}")
            
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            print(f"\nCalculated:")
            print(f"  Red: {is_red}")
            print(f"  Body: {body:.6f}")
            print(f"  Lower Wick: {lower_wick:.6f}")
            print(f"  Upper Wick: {upper_wick:.6f}")
            
            if body > 0:
                ratio = lower_wick / body
                print(f"  Wick/Body: {ratio:.2f}x")
            else:
                print(f"  Wick/Body: CANNOT CALCULATE (body is {body:.6f})")
            
            print(f"\nTelegram showed:")
            print(f"  Body: 0.000000")
            print(f"  Lower Wick: 0.000000")
            print(f"  Wick/Body: 4.67x")
            
            print(f"\n!!! BUG: Telegram shows Body=0 but Wick/Body=4.67x !!!")
            print(f"This is mathematically impossible.")
            
            break
    
    # MEW-USDT at 2026-08-06 19:30 UTC
    mew_time = datetime(2026, 8, 6, 19, 30, tzinfo=UTC)
    mew_start = int((mew_time - timedelta(hours=2)).timestamp() * 1000)
    mew_end = int((mew_time + timedelta(hours=2)).timestamp() * 1000)
    
    print("\n" + "=" * 80)
    print("2. CHECKING MEW-USDT")
    print("-" * 80)
    
    klines = await fetcher.get_klines(
        symbol="MEW-USDT",
        interval="15m",
        limit=1000,
        start_time=mew_start,
        end_time=mew_end
    )
    
    for kline in klines:
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == mew_time:
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            
            print(f"Time: {kline_datetime}")
            print(f"Raw BingX: O={kline['open']} H={kline['high']} L={kline['low']} C={kline['close']}")
            print(f"Parsed: O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f}")
            
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            print(f"\nCalculated:")
            print(f"  Red: {is_red}")
            print(f"  Body: {body:.6f}")
            print(f"  Lower Wick: {lower_wick:.6f}")
            print(f"  Upper Wick: {upper_wick:.6f}")
            
            if body > 0:
                ratio = lower_wick / body
                print(f"  Wick/Body: {ratio:.2f}x")
            else:
                print(f"  Wick/Body: CANNOT CALCULATE (body is {body:.6f})")
            
            print(f"\nTelegram showed:")
            print(f"  Body: 0.000000")
            print(f"  Lower Wick: 0.000000")
            print(f"  Wick/Body: 2.00x")
            
            print(f"\n!!! BUG: Telegram shows Body=0 but Wick/Body=2.00x !!!")
            print(f"This is mathematically impossible.")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
