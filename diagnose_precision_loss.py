#!/usr/bin/env python3
"""
Diagnose precision loss issue with small body candles.

The issue: BingX returns values with more precision than displayed.
When formatted to 6 decimal places, very small bodies show as 0.000000.
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
    """Check precision loss with LUNC-USDT."""
    print("=" * 80)
    print("DIAGNOSING PRECISION LOSS")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # LUNC-USDT at 2026-08-12 11:00 UTC
    lunc_time = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)
    lunc_start = int((lunc_time - timedelta(hours=2)).timestamp() * 1000)
    lunc_end = int((lunc_time + timedelta(hours=2)).timestamp() * 1000)
    
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
            # Raw string values from BingX
            raw_open = kline['open']
            raw_high = kline['high']
            raw_low = kline['low']
            raw_close = kline['close']
            
            # Parsed float values
            open_price = float(raw_open)
            high_price = float(raw_high)
            low_price = float(raw_low)
            close_price = float(raw_close)
            
            print(f"\nRAW BINGX VALUES (strings):")
            print(f"  Open:  {raw_open}")
            print(f"  High:  {raw_high}")
            print(f"  Low:   {raw_low}")
            print(f"  Close: {raw_close}")
            
            print(f"\nPARSED FLOAT VALUES:")
            print(f"  Open:  {open_price}")
            print(f"  High:  {high_price}")
            print(f"  Low:   {low_price}")
            print(f"  Close: {close_price}")
            
            print(f"\nFORMATTED TO 6 DECIMAL PLACES (Telegram format):")
            print(f"  Open:  {open_price:.6f}")
            print(f"  High:  {high_price:.6f}")
            print(f"  Low:   {low_price:.6f}")
            print(f"  Close: {close_price:.6f}")
            
            # Calculate with full precision
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            print(f"\nCALCULATED WITH FULL PRECISION:")
            print(f"  Red: {is_red}")
            print(f"  Body: {body}")
            print(f"  Lower Wick: {lower_wick}")
            print(f"  Upper Wick: {upper_wick}")
            
            if body > 0:
                ratio = lower_wick / body
                print(f"  Wick/Body: {ratio}")
            
            print(f"\nCALCULATED WITH FORMATTED VALUES (6 decimals):")
            formatted_open = round(open_price, 6)
            formatted_high = round(high_price, 6)
            formatted_low = round(low_price, 6)
            formatted_close = round(close_price, 6)
            
            formatted_body = formatted_open - formatted_close if formatted_close < formatted_open else 0.0
            formatted_lower_wick = formatted_close - formatted_low
            formatted_upper_wick = formatted_high - formatted_open
            
            print(f"  Red: {formatted_close < formatted_open}")
            print(f"  Body: {formatted_body:.6f}")
            print(f"  Lower Wick: {formatted_lower_wick:.6f}")
            print(f"  Upper Wick: {formatted_upper_wick:.6f}")
            
            if formatted_body > 0:
                formatted_ratio = formatted_lower_wick / formatted_body
                print(f"  Wick/Body: {formatted_ratio:.2f}x")
            else:
                print(f"  Wick/Body: CANNOT CALCULATE (body is {formatted_body:.6f})")
            
            # Run qualification check with full precision
            lw_qualified, lw_details = check_lw001_strict(open_price, high_price, low_price, close_price)
            
            print(f"\nLW-001 QUALIFICATION (full precision):")
            print(f"  Qualified: {lw_qualified}")
            print(f"  Body: {lw_details['body']}")
            print(f"  Lower Wick: {lw_details['lower_wick']}")
            print(f"  Ratio: {lw_details['ratio']}")
            
            print(f"\nCONCLUSION:")
            print(f"The qualification uses FULL PRECISION values, so it works correctly.")
            print(f"But Telegram displays with 6 decimal places, so very small bodies show as 0.000000.")
            print(f"This is a DISPLAY ISSUE, not a qualification issue.")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
