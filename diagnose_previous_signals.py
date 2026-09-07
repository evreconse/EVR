#!/usr/bin/env python3
"""
Diagnose why previous 10 signals were incorrect.

Fetch actual OHLC data from BingX for each previously sent signal
and recalculate LW-001 conditions to identify the discrepancy.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from exchange.bingx_fetcher import BingXFetcher


async def diagnose_previous_signals():
    """Diagnose the previous 10 signals."""
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize BingX fetcher
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    # Previous signals that were sent
    previous_signals = [
        {"symbol": "BCH-USDT", "time": "2026-08-10T14:15:00Z"},
        {"symbol": "THETA-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "ALGO-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "AXS-USDT", "time": "2026-08-10T15:00:00Z"},
        {"symbol": "DYDX-USDT", "time": "2026-08-10T13:30:00Z"},
        {"symbol": "ICP-USDT", "time": "2026-08-09T21:00:00Z"},
        {"symbol": "SAND-USDT", "time": "2026-08-10T13:30:00Z"},
        {"symbol": "KSM-USDT", "time": "2026-08-10T15:15:00Z"},
        {"symbol": "VET-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "SUSHI-USDT", "time": "2026-08-10T16:00:00Z"},
    ]
    
    print("\n" + "="*100)
    print("DIAGNOSTIC REPORT: Previous 10 Signals")
    print("="*100)
    
    for i, signal_info in enumerate(previous_signals, 1):
        symbol = signal_info["symbol"]
        target_time_str = signal_info["time"]
        target_time = datetime.fromisoformat(target_time_str.replace("Z", "+00:00"))
        target_timestamp_ms = int(target_time.timestamp() * 1000)
        
        print(f"\n--- Signal {i}: {symbol} ---")
        print(f"Target Time (UTC): {target_time_str}")
        print(f"Target Timestamp (ms): {target_timestamp_ms}")
        
        # Fetch klines around the target time
        # Get 100 candles around the target time to find the exact match
        start_time = target_timestamp_ms - (100 * 15 * 60 * 1000)  # 100 candles before
        end_time = target_timestamp_ms + (100 * 15 * 60 * 1000)    # 100 candles after
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=200,
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines:
                print(f"ERROR: No klines found for {symbol}")
                continue
            
            # Find the candle closest to target time
            target_candle = None
            min_diff = float('inf')
            
            for kline in klines:
                kline_time = int(kline['time'])
                diff = abs(kline_time - target_timestamp_ms)
                if diff < min_diff:
                    min_diff = diff
                    target_candle = kline
            
            if target_candle:
                open_price = float(target_candle['open'])
                high_price = float(target_candle['high'])
                low_price = float(target_candle['low'])
                close_price = float(target_candle['close'])
                volume = float(target_candle['volume'])
                candle_time = int(target_candle['time'])
                candle_time_utc = datetime.fromtimestamp(candle_time / 1000, tz=UTC)
                
                print(f"\nActual Candle Found:")
                print(f"  Time (UTC): {candle_time_utc}")
                print(f"  Time (ms): {candle_time}")
                print(f"  Time difference: {min_diff/1000:.1f} seconds")
                print(f"  Open: {open_price}")
                print(f"  High: {high_price}")
                print(f"  Low: {low_price}")
                print(f"  Close: {close_price}")
                print(f"  Volume: {volume}")
                
                # Calculate LW-001 conditions
                is_red = close_price < open_price
                body = open_price - close_price if is_red else close_price - open_price
                lower_wick = close_price - low_price if is_red else open_price - low_price
                upper_wick = high_price - max(open_price, close_price)
                
                if body > 0:
                    ratio = lower_wick / body
                else:
                    ratio = 0.0
                
                qualified = is_red and ratio >= 2.0
                
                print(f"\nLW-001 Calculation:")
                print(f"  Red candle (Close < Open): {is_red}")
                print(f"  Body (Open - Close): {body:.6f}")
                print(f"  Lower Wick (Close - Low): {lower_wick:.6f}")
                print(f"  Upper Wick: {upper_wick:.6f}")
                print(f"  Lower Wick / Body: {ratio:.2f}x")
                print(f"  Qualified (red AND ratio >= 2.0): {qualified}")
                
                if not qualified:
                    print(f"\n  [FAIL] SIGNAL FAILS LW-001 CONDITIONS")
                    if not is_red:
                        print(f"     REASON: Not a red candle (Close >= Open)")
                    elif ratio < 2.0:
                        print(f"     REASON: Ratio {ratio:.2f}x < 2.0x")
                else:
                    print(f"\n  [PASS] SIGNAL PASSES LW-001 CONDITIONS")
            else:
                print(f"ERROR: Could not find candle near target time")
                
        except Exception as e:
            print(f"ERROR processing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*100)
    print("DIAGNOSTIC COMPLETE")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(diagnose_previous_signals())
