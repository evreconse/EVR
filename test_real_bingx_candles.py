#!/usr/bin/env python3
"""
Test with real historical candles from BingX to verify the formula.

This script fetches actual candles from BingX and calculates LW-001 conditions
using both production and corrected formulas to identify any discrepancies.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def check_lw001_production(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Check using PRODUCTION formula from src/strategy/lw_001.py."""
    is_red = close_price < open_price
    body = abs(close_price - open_price)
    lower_wick = close_price - low_price
    upper_wick = high_price - max(open_price, close_price)
    wick_body_ratio = lower_wick / body if body > 0 else 0.0
    qualified = is_red and wick_body_ratio >= 2.0
    
    return {
        "qualified": qualified,
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "wick_body_ratio": wick_body_ratio,
    }


def check_lw001_corrected(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Check using CORRECTED formula per user's specification."""
    is_red = close_price < open_price
    
    if not is_red:
        return {
            "qualified": False,
            "reason": "Not a red candle",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    if close_price == low_price:
        return {
            "qualified": False,
            "reason": "Close == Low (no lower wick)",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    body = open_price - close_price
    
    if body <= 0:
        return {
            "qualified": False,
            "reason": "Zero or negative body",
            "is_red": is_red,
            "body": body,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    wick_body_ratio = lower_wick / body
    qualified = wick_body_ratio >= 2.0
    
    return {
        "qualified": qualified,
        "reason": "Qualified" if qualified else "Lower Wick < 2 * Body",
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "wick_body_ratio": wick_body_ratio,
    }


async def test_symbol(symbol: str, fetcher: BingXFetcher):
    """Test a specific symbol with real BingX data."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {symbol}")
    print(f"{'=' * 80}")
    
    # Fetch recent klines
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Find candles with large upper wick but small lower wick
    large_upper_wick_candles = []
    
    for i in range(len(klines) - 1, 48, -1):
        open_price = float(klines[i]['open'])
        high_price = float(klines[i]['high'])
        low_price = float(klines[i]['low'])
        close_price = float(klines[i]['close'])
        
        is_red = close_price < open_price
        
        if is_red:
            body = open_price - close_price
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            # Check if upper wick is large but lower wick is small
            if upper_wick > 2 * body and lower_wick < 0.5 * body:
                large_upper_wick_candles.append({
                    "index": i,
                    "time": int(klines[i]['time']),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "body": body,
                    "lower_wick": lower_wick,
                    "upper_wick": upper_wick,
                })
    
    print(f"\nFound {len(large_upper_wick_candles)} candles with large upper wick but small lower wick")
    
    # Test a few of these candles
    test_count = min(5, len(large_upper_wick_candles))
    for i in range(test_count):
        candle = large_upper_wick_candles[i]
        
        print(f"\n{'-' * 80}")
        print(f"Candle {i+1}: {datetime.fromtimestamp(candle['time'] / 1000, tz=UTC)}")
        print(f"Open: {candle['open']:.6f}")
        print(f"High: {candle['high']:.6f}")
        print(f"Low: {candle['low']:.6f}")
        print(f"Close: {candle['close']:.6f}")
        print(f"Body: {candle['body']:.6f}")
        print(f"Lower Wick: {candle['lower_wick']:.6f}")
        print(f"Upper Wick: {candle['upper_wick']:.6f}")
        print(f"Upper/Body: {candle['upper_wick'] / candle['body']:.2f}x")
        print(f"Lower/Body: {candle['lower_wick'] / candle['body']:.2f}x")
        
        # Test with both formulas
        prod_result = check_lw001_production(candle['open'], candle['high'], candle['low'], candle['close'])
        corr_result = check_lw001_corrected(candle['open'], candle['high'], candle['low'], candle['close'])
        
        print(f"\nProduction: {'PASS' if prod_result['qualified'] else 'FAIL'}")
        print(f"  Body: {prod_result['body']:.6f}")
        print(f"  Lower Wick: {prod_result['lower_wick']:.6f}")
        print(f"  Ratio: {prod_result['wick_body_ratio']:.2f}x")
        
        print(f"\nCorrected: {'PASS' if corr_result['qualified'] else 'FAIL'}")
        if corr_result['body'] is not None:
            print(f"  Body: {corr_result['body']:.6f}")
            print(f"  Lower Wick: {corr_result['lower_wick']:.6f}")
            print(f"  Ratio: {corr_result['wick_body_ratio']:.2f}x")
        else:
            print(f"  Reason: {corr_result['reason']}")
        
        if prod_result['qualified'] != corr_result['qualified']:
            print(f"\n!!! DISCREPANCY DETECTED !!!")
            print(f"Production says: {'PASS' if prod_result['qualified'] else 'FAIL'}")
            print(f"Corrected says: {'PASS' if corr_result['qualified'] else 'FAIL'}")


async def main():
    """Main execution."""
    load_dotenv()
    
    print("=" * 80)
    print("TESTING REAL BINGX CANDLES")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # Test a few symbols
    test_symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    
    for symbol in test_symbols:
        try:
            await test_symbol(symbol, fetcher)
        except Exception as e:
            print(f"Error testing {symbol}: {e}")
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
