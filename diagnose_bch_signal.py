#!/usr/bin/env python3
"""
Diagnostic test to investigate why BCH-USDT was sent with Ratio 1.20x.
Fetches the actual candle from BingX and recalculates LW-001 conditions.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def diagnose_bch_signal():
    """Diagnose the BCH-USDT signal that was sent with Ratio 1.20x."""
    
    print("="*80)
    print("DIAGNOSING BCH-USDT SIGNAL")
    print("="*80)
    
    # Initialize fetcher
    api_key = os.getenv("BINGX_API_KEY")
    api_secret = os.getenv("BINGX_API_SECRET")
    
    if not api_key or not api_secret:
        print("ERROR: BingX API credentials not found in .env")
        return
    
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    # The signal was at 2026-08-11 16:00:00 UTC (19:00:00 MSK)
    # Fetch candles around this time
    target_time = datetime(2026, 8, 11, 16, 0, 0, tzinfo=UTC)
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    print(f"\nFetching BCH-USDT candles around {target_time}")
    print(f"Start: {datetime.fromtimestamp(start_time/1000, UTC)}")
    print(f"End: {datetime.fromtimestamp(end_time/1000, UTC)}")
    
    try:
        klines = await fetcher.get_klines(
            symbol="BCH-USDT",
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"\nFetched {len(klines)} candles")
        
        # Find the candle at the target time
        target_candle = None
        for kline in klines:
            candle_time = datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC)
            if abs(candle_time - target_time) < timedelta(minutes=1):
                target_candle = kline
                break
        
        if target_candle:
            print(f"\n=== TARGET CANDLE FOUND ===")
            print(f"Time (UTC): {datetime.fromtimestamp(int(target_candle['time'])/1000, UTC)}")
            print(f"Time (MSK): {datetime.fromtimestamp(int(target_candle['time'])/1000, UTC).replace(hour=(datetime.fromtimestamp(int(target_candle['time'])/1000, UTC).hour + 3) % 24)}")
            print(f"Open: {target_candle['open']}")
            print(f"High: {target_candle['high']}")
            print(f"Low: {target_candle['low']}")
            print(f"Close: {target_candle['close']}")
            print(f"Volume: {target_candle['volume']}")
            
            # Calculate LW-001 conditions
            open_price = float(target_candle['open'])
            high_price = float(target_candle['high'])
            low_price = float(target_candle['low'])
            close_price = float(target_candle['close'])
            
            print(f"\n=== LW-001 CALCULATION ===")
            
            # User's specified formula
            body_abs = abs(open_price - close_price)
            lower_wick_min = min(open_price, close_price) - low_price
            upper_wick_max = high_price - max(open_price, close_price)
            ratio_min = lower_wick_min / body_abs if body_abs > 0 else 0.0
            
            is_red = close_price < open_price
            qualified = is_red and ratio_min >= 2.0
            
            print(f"Red Candle (Close < Open): {is_red}")
            print(f"Body (abs(Open - Close)): {body_abs:.4f}")
            print(f"Lower Wick (min(Open, Close) - Low): {lower_wick_min:.4f}")
            print(f"Upper Wick (High - max(Open, Close)): {upper_wick_max:.4f}")
            print(f"Ratio (Lower Wick / Body): {ratio_min:.2f}x")
            print(f"Qualified (Red AND Ratio >= 2.0): {qualified}")
            
            # Current implementation formula
            body_current = open_price - close_price if is_red else close_price - open_price
            lower_wick_current = close_price - low_price if is_red else open_price - low_price
            ratio_current = lower_wick_current / body_current if body_current > 0 else 0.0
            qualified_current = is_red and ratio_current >= 2.0
            
            print(f"\n=== CURRENT IMPLEMENTATION ===")
            print(f"Body (Open - Close for red): {body_current:.4f}")
            print(f"Lower Wick (Close - Low for red): {lower_wick_current:.4f}")
            print(f"Ratio: {ratio_current:.2f}x")
            print(f"Qualified: {qualified_current}")
            
            print(f"\n=== COMPARISON ===")
            print(f"User formula ratio: {ratio_min:.2f}x")
            print(f"Current formula ratio: {ratio_current:.2f}x")
            print(f"Match: {abs(ratio_min - ratio_current) < 0.01}")
            
        else:
            print(f"\nTarget candle not found. Showing all candles:")
            for kline in klines:
                candle_time = datetime.fromtimestamp(int(kline['time']) / 1000, UTC)
                print(f"{candle_time}: O={kline['open']} H={kline['high']} L={kline['low']} C={kline['close']}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose_bch_signal())
