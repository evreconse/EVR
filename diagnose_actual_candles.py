#!/usr/bin/env python3
"""
Fetch actual candle data from BingX to investigate zero-body candles.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def diagnose_candles():
    """Diagnose actual candles from BingX."""
    
    print("="*80)
    print("DIAGNOSING ACTUAL CANDLES FROM BINGX")
    print("="*80)
    
    api_key = os.getenv("EVRECONSE_EXCHANGE_API_KEY")
    api_secret = os.getenv("EVRECONSE_EXCHANGE_API_SECRET")
    
    if not api_key or not api_secret:
        print("ERROR: BingX API credentials not found")
        return
    
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    # Test the candles that were flagged as having zero body
    test_symbols = [
        ("VET-USDT", datetime(2026, 8, 11, 11, 45, 0, tzinfo=UTC)),
        ("ALGO-USDT", datetime(2026, 8, 11, 17, 0, 0, tzinfo=UTC)),
        ("SAND-USDT", datetime(2026, 8, 11, 17, 0, 0, tzinfo=UTC)),
    ]
    
    for symbol, target_time in test_symbols:
        print(f"\n{'='*80}")
        print(f"Symbol: {symbol}")
        print(f"Target Time: {target_time}")
        print(f"{'='*80}")
        
        start_time = int((target_time - timedelta(hours=1)).timestamp() * 1000)
        end_time = int((target_time + timedelta(hours=1)).timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=50,
                start_time=start_time,
                end_time=end_time
            )
            
            print(f"Fetched {len(klines)} candles")
            
            # Find the candle at the target time
            target_candle = None
            for kline in klines:
                candle_time = datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC)
                if abs(candle_time - target_time) < timedelta(minutes=1):
                    target_candle = kline
                    break
            
            if target_candle:
                open_price = float(target_candle['open'])
                high_price = float(target_candle['high'])
                low_price = float(target_candle['low'])
                close_price = float(target_candle['close'])
                volume = float(target_candle['volume'])
                
                print(f"\n=== TARGET CANDLE ===")
                print(f"Time (UTC): {datetime.fromtimestamp(int(target_candle['time'])/1000, UTC)}")
                print(f"Open: {open_price}")
                print(f"High: {high_price}")
                print(f"Low: {low_price}")
                print(f"Close: {close_price}")
                print(f"Volume: {volume}")
                
                # Calculate LW-001
                is_red = close_price < open_price
                body = abs(open_price - close_price)
                lower_wick = min(open_price, close_price) - low_price
                upper_wick = high_price - max(open_price, close_price)
                ratio = lower_wick / body if body > 0 else 0.0
                qualified = is_red and ratio >= 2.0
                
                print(f"\n=== LW-001 CALCULATION ===")
                print(f"Red Candle: {is_red}")
                print(f"Body: {body:.6f}")
                print(f"Lower Wick: {lower_wick:.6f}")
                print(f"Upper Wick: {upper_wick:.6f}")
                print(f"Ratio: {ratio:.2f}x")
                print(f"Qualified: {qualified}")
                
            else:
                print(f"\nTarget candle not found. Showing nearby candles:")
                for kline in klines[:5]:
                    candle_time = datetime.fromtimestamp(int(kline['time']) / 1000, UTC)
                    print(f"{candle_time}: O={kline['open']} H={kline['high']} L={kline['low']} C={kline['close']}")
        
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose_candles())
