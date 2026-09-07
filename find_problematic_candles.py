#!/usr/bin/env python3
"""
Search for candles with large upper wick but small lower wick in the signals.

The user says they manually verified signals and found incorrect ones.
Let's search for candles that actually have:
- Large upper wick
- Small or no lower wick
- But were sent as signals
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """Check LW-001 conditions."""
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    if close_price == low_price:
        return False, {"reason": "Close == Low (no lower wick)"}
    
    body = open_price - close_price if is_red else 0.0
    
    if body <= 0:
        return False, {"reason": "Zero or negative body"}
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


async def main():
    """Search for problematic candles in the 10 sent signals."""
    print("=" * 80)
    print("SEARCHING FOR PROBLEMATIC CANDLES IN SENT SIGNALS")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The 10 signals from the report
    signals = [
        {'symbol': 'SUSHI-USDT', 'time': datetime(2026, 8, 5, 11, 15, tzinfo=UTC)},
        {'symbol': 'COMP-USDT', 'time': datetime(2026, 8, 7, 4, 45, tzinfo=UTC)},
        {'symbol': 'DASH-USDT', 'time': datetime(2026, 8, 11, 10, 15, tzinfo=UTC)},
        {'symbol': 'FLOW-USDT', 'time': datetime(2026, 8, 10, 7, 15, tzinfo=UTC)},
        {'symbol': 'RUNE-USDT', 'time': datetime(2026, 8, 6, 7, 30, tzinfo=UTC)},
        {'symbol': 'ROSE-USDT', 'time': datetime(2026, 8, 6, 2, 15, tzinfo=UTC)},
        {'symbol': 'WOO-USDT', 'time': datetime(2026, 8, 11, 4, 45, tzinfo=UTC)},
        {'symbol': 'CRO-USDT', 'time': datetime(2026, 8, 9, 4, 45, tzinfo=UTC)},
        {'symbol': 'ACH-USDT', 'time': datetime(2026, 8, 8, 13, 0, tzinfo=UTC)},
        {'symbol': 'TLM-USDT', 'time': datetime(2026, 8, 11, 18, 30, tzinfo=UTC)},
    ]
    
    problematic_count = 0
    
    for signal in signals:
        symbol = signal['symbol']
        target_time = signal['time']
        
        # Fetch klines around that time
        start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
        end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,
                start_time=start_time,
                end_time=end_time
            )
            
            # Find the candle at the exact timestamp
            for kline in klines:
                kline_time = int(kline['time'])
                kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
                
                if kline_datetime == target_time:
                    open_price = float(kline['open'])
                    high_price = float(kline['high'])
                    low_price = float(kline['low'])
                    close_price = float(kline['close'])
                    
                    # Calculate wicks
                    is_red = close_price < open_price
                    body = open_price - close_price if is_red else 0.0
                    lower_wick = close_price - low_price
                    upper_wick = high_price - open_price
                    
                    if body > 0:
                        lower_ratio = lower_wick / body
                        upper_ratio = upper_wick / body
                    else:
                        lower_ratio = 0.0
                        upper_ratio = 0.0
                    
                    # Check if this candle has large upper wick but small lower wick
                    has_large_upper = upper_wick > 2 * body
                    has_small_lower = lower_wick < 0.5 * body
                    
                    print(f"\n{symbol} at {target_time}")
                    print(f"  Open:  {open_price:.6f}")
                    print(f"  High:  {high_price:.6f}")
                    print(f"  Low:   {low_price:.6f}")
                    print(f"  Close: {close_price:.6f}")
                    print(f"  Body: {body:.6f}")
                    print(f"  Lower Wick: {lower_wick:.6f} ({lower_ratio:.2f}x body)")
                    print(f"  Upper Wick: {upper_wick:.6f} ({upper_ratio:.2f}x body)")
                    
                    if has_large_upper and has_small_lower:
                        print(f"  !!! PROBLEMATIC: Large upper wick but small lower wick !!!")
                        problematic_count += 1
                    elif lower_wick < 0.1 * body:
                        print(f"  !!! PROBLEMATIC: Lower wick is very small ({lower_ratio:.2f}x) !!!")
                        problematic_count += 1
                    else:
                        print(f"  OK: Lower wick is {lower_ratio:.2f}x body")
                    
                    break
        except Exception as e:
            print(f"\nError checking {symbol}: {e}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY")
    print("=" * 80)
    print(f"Total signals checked: {len(signals)}")
    print(f"Problematic signals found: {problematic_count}")
    
    if problematic_count == 0:
        print("\nNo problematic candles found.")
        print("All 10 signals have lower wick >= 2x body as expected.")
        print("The user may have been looking at wrong data or wrong candles.")
    else:
        print(f"\n{problematic_count} problematic signals found.")
        print("These need to be investigated further.")


if __name__ == "__main__":
    asyncio.run(main())
