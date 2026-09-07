#!/usr/bin/env python3
"""
Diagnose recent signals to check for the lower wick issue.

This script will:
1. Fetch recent M15 candles from the coins we sent signals for
2. Check if any of them have Close == Low (no lower wick)
3. Verify the calculations
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# The symbols we sent signals for
TEST_SYMBOLS = [
    "SUSHI-USDT",
    "COMP-USDT",
    "DASH-USDT",
    "FLOW-USDT",
    "RUNE-USDT",
]


async def diagnose_symbol(symbol: str, fetcher: BingXFetcher):
    """Diagnose a specific symbol for recent signals."""
    print(f"\n{'=' * 80}")
    print(f"Analyzing: {symbol}")
    print(f"{'=' * 80}")
    
    # Fetch recent klines (last 7 days)
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
    
    # Check each candle for LW-001 conditions
    signals_found = []
    candles_with_no_lower_wick = []
    
    for i in range(len(klines) - 1, 48, -1):  # Need at least 48 previous for volume
        open_price = float(klines[i]['open'])
        high_price = float(klines[i]['high'])
        low_price = float(klines[i]['low'])
        close_price = float(klines[i]['close'])
        volume = float(klines[i]['volume'])
        
        is_red = close_price < open_price
        body = open_price - close_price
        lower_wick = close_price - low_price
        upper_wick = high_price - open_price
        
        # Check for no lower wick
        if is_red and close_price == low_price:
            candles_with_no_lower_wick.append({
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
        
        # Check LW-001 qualification
        if is_red and body > 0:
            wick_body_ratio = lower_wick / body
            if wick_body_ratio >= 2.0:
                signals_found.append({
                    "index": i,
                    "time": int(klines[i]['time']),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "body": body,
                    "lower_wick": lower_wick,
                    "upper_wick": upper_wick,
                    "ratio": wick_body_ratio,
                })
    
    print(f"\nCandles with NO lower wick (Close == Low): {len(candles_with_no_lower_wick)}")
    if candles_with_no_lower_wick:
        print("These candles have NO lower wick:")
        for candle in candles_with_no_lower_wick[:5]:  # Show first 5
            print(f"  Time: {datetime.fromtimestamp(candle['time'] / 1000, tz=UTC)}")
            print(f"    O={candle['open']:.4f} H={candle['high']:.4f} L={candle['low']:.4f} C={candle['close']:.4f}")
            print(f"    Body={candle['body']:.4f} LowerWick={candle['lower_wick']:.4f} UpperWick={candle['upper_wick']:.4f}")
    
    print(f"\nLW-001 signals found (wick/body >= 2.0): {len(signals_found)}")
    if signals_found:
        print("These candles would qualify by wick/body ratio:")
        for signal in signals_found[:5]:  # Show first 5
            print(f"  Time: {datetime.fromtimestamp(signal['time'] / 1000, tz=UTC)}")
            print(f"    O={signal['open']:.4f} H={signal['high']:.4f} L={signal['low']:.4f} C={signal['close']:.4f}")
            print(f"    Body={signal['body']:.4f} LowerWick={signal['lower_wick']:.4f} UpperWick={signal['upper_wick']:.4f} Ratio={signal['ratio']:.2f}x")
            
            # Check if this is a false positive (no lower wick)
            if signal['close'] == signal['low']:
                print(f"    ⚠️  WARNING: This candle has NO lower wick but would qualify!")
    
    # Check for the specific bug: candles that would qualify but have no lower wick
    false_positives = [s for s in signals_found if s['close'] == s['low']]
    if false_positives:
        print(f"\n{'!' * 80}")
        print(f"CRITICAL: Found {len(false_positives)} false positives!")
        print("These candles have NO lower wick but would qualify by the formula:")
        for fp in false_positives:
            print(f"  Time: {datetime.fromtimestamp(fp['time'] / 1000, tz=UTC)}")
            print(f"    O={fp['open']:.4f} H={fp['high']:.4f} L={fp['low']:.4f} C={fp['close']:.4f}")
            print(f"    Body={fp['body']:.4f} LowerWick={fp['lower_wick']:.4f} UpperWick={fp['upper_wick']:.4f} Ratio={fp['ratio']:.2f}x")
        print(f"{'!' * 80}")
    else:
        print(f"\n✅ No false positives found (no candles with no lower wick would qualify)")


async def main():
    """Main execution."""
    load_dotenv()
    
    print("=" * 80)
    print("DIAGNOSING RECENT SIGNALS FOR LOWER WICK ISSUE")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    for symbol in TEST_SYMBOLS:
        try:
            await diagnose_symbol(symbol, fetcher)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
