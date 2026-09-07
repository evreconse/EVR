#!/usr/bin/env python3
"""
Find real BingX candles to test upper wick influence.

Scenario A: Huge upper wick + small lower wick → FAIL
Scenario B: Large lower wick + any upper wick → PASS
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Check LW-001 conditions."""
    is_red = close_price < open_price
    
    if not is_red:
        return {"qualified": False, "reason": "Not red", "is_red": is_red, "body": None, "lower_wick": None, "upper_wick": None, "ratio": None}
    
    if close_price == low_price:
        return {"qualified": False, "reason": "Close == Low", "is_red": is_red, "body": None, "lower_wick": None, "upper_wick": None, "ratio": None}
    
    body = open_price - close_price if is_red else 0.0
    
    if body <= 0:
        return {"qualified": False, "reason": "Zero body", "is_red": is_red, "body": body, "lower_wick": None, "upper_wick": None, "ratio": None}
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    return {
        "qualified": qualified,
        "reason": "Qualified" if qualified else "Lower Wick < 2x Body",
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
    }


async def main():
    """Find test candles."""
    print("=" * 80)
    print("FINDING TEST CANDLES FROM BINGX")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # Test a few symbols
    test_symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
    
    scenario_a_found = False
    scenario_b_found = False
    
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    for symbol in test_symbols:
        if scenario_a_found and scenario_b_found:
            break
        
        print(f"\n{'=' * 80}")
        print(f"Testing {symbol}")
        print(f"{'=' * 80}")
        
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"Fetched {len(klines)} klines")
        
        for i in range(len(klines) - 1, 48, -1):
            if scenario_a_found and scenario_b_found:
                break
            
            open_price = float(klines[i]['open'])
            high_price = float(klines[i]['high'])
            low_price = float(klines[i]['low'])
            close_price = float(klines[i]['close'])
            
            result = check_lw001_strict(open_price, high_price, low_price, close_price)
            
            if result['body'] is None or result['body'] <= 0:
                continue
            
            # Scenario A: Huge upper wick + small lower wick
            if not scenario_a_found:
                upper_wick = result['upper_wick']
                lower_wick = result['lower_wick']
                body = result['body']
                
                # Upper wick is huge (> 5x body) but lower wick is small (< 0.5x body)
                if upper_wick > 5 * body and lower_wick < 0.5 * body:
                    scenario_a_found = True
                    kline_time = int(klines[i]['time'])
                    kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
                    
                    print(f"\n{'=' * 80}")
                    print(f"SCENARIO A FOUND: Huge upper wick + small lower wick")
                    print(f"{'=' * 80}")
                    print(f"Symbol: {symbol}")
                    print(f"Time: {kline_datetime}")
                    print(f"\nRAW BINGX DATA:")
                    print(f"  Open:  {open_price:.6f}")
                    print(f"  High:  {high_price:.6f}")
                    print(f"  Low:   {low_price:.6f}")
                    print(f"  Close: {close_price:.6f}")
                    print(f"\nCALCULATED:")
                    print(f"  Body: {body:.6f}")
                    print(f"  Lower Wick: {lower_wick:.6f} ({lower_wick / body:.2f}x body)")
                    print(f"  Upper Wick: {upper_wick:.6f} ({upper_wick / body:.2f}x body)")
                    print(f"\nQUALIFICATION:")
                    print(f"  Red Candle: {result['is_red']}")
                    print(f"  Lower Wick / Body: {result['ratio']:.2f}x")
                    print(f"  Lower Wick >= 2 * Body: {result['qualified']}")
                    print(f"  FINAL: {'PASS' if result['qualified'] else 'FAIL'}")
                    print(f"\nEXPECTED: FAIL (because lower wick is small)")
                    print(f"ACTUAL: {'PASS' if result['qualified'] else 'FAIL'}")
                    
                    if result['qualified']:
                        print(f"\n!!! ERROR: This should FAIL but it PASSED !!!")
                    else:
                        print(f"\n[OK] CORRECT: This correctly FAILS")
            
            # Scenario B: Large lower wick + any upper wick
            if not scenario_b_found:
                upper_wick = result['upper_wick']
                lower_wick = result['lower_wick']
                body = result['body']
                
                # Lower wick is >= 2x body, regardless of upper wick
                if lower_wick >= 2 * body:
                    scenario_b_found = True
                    kline_time = int(klines[i]['time'])
                    kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
                    
                    print(f"\n{'=' * 80}")
                    print(f"SCENARIO B FOUND: Large lower wick + any upper wick")
                    print(f"{'=' * 80}")
                    print(f"Symbol: {symbol}")
                    print(f"Time: {kline_datetime}")
                    print(f"\nRAW BINGX DATA:")
                    print(f"  Open:  {open_price:.6f}")
                    print(f"  High:  {high_price:.6f}")
                    print(f"  Low:   {low_price:.6f}")
                    print(f"  Close: {close_price:.6f}")
                    print(f"\nCALCULATED:")
                    print(f"  Body: {body:.6f}")
                    print(f"  Lower Wick: {lower_wick:.6f} ({lower_wick / body:.2f}x body)")
                    print(f"  Upper Wick: {upper_wick:.6f} ({upper_wick / body:.2f}x body)")
                    print(f"\nQUALIFICATION:")
                    print(f"  Red Candle: {result['is_red']}")
                    print(f"  Lower Wick / Body: {result['ratio']:.2f}x")
                    print(f"  Lower Wick >= 2 * Body: {result['qualified']}")
                    print(f"  FINAL: {'PASS' if result['qualified'] else 'FAIL'}")
                    print(f"\nEXPECTED: PASS (because lower wick >= 2x body)")
                    print(f"ACTUAL: {'PASS' if result['qualified'] else 'FAIL'}")
                    
                    if not result['qualified']:
                        print(f"\n!!! ERROR: This should PASS but it FAILED !!!")
                    else:
                        print(f"\n[OK] CORRECT: This correctly PASSES")
    
    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Scenario A (huge upper + small lower): {'FOUND' if scenario_a_found else 'NOT FOUND'}")
    print(f"Scenario B (large lower + any upper): {'FOUND' if scenario_b_found else 'NOT FOUND'}")


if __name__ == "__main__":
    asyncio.run(main())
