#!/usr/bin/env python3
"""
Diagnose the signal pipeline to find why incorrect signals are being sent.

This script will:
1. Fetch one of the previously sent signals from BingX
2. Compare the OHLC values with what was sent to Telegram
3. Verify the calculations
4. Check for any data transformation issues
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# One of the signals from the previous batch
TEST_SIGNAL = {
    "symbol": "SUSHI-USDT",
    "timestamp_ms": 1722845700000,  # 2026-08-05 11:15:00 UTC
}


async def diagnose_signal():
    """Diagnose a specific signal from BingX."""
    load_dotenv()
    
    print("=" * 80)
    print("SIGNAL PIPELINE DIAGNOSIS")
    print("=" * 80)
    
    print(f"\nAnalyzing signal: {TEST_SIGNAL['symbol']}")
    print(f"Timestamp (ms): {TEST_SIGNAL['timestamp_ms']}")
    print(f"Timestamp (UTC): {datetime.fromtimestamp(TEST_SIGNAL['timestamp_ms'] / 1000, tz=UTC)}")
    
    fetcher = BingXFetcher()
    
    # Fetch klines around the timestamp
    end_time = TEST_SIGNAL['timestamp_ms'] + 15 * 60 * 1000  # +15 minutes
    start_time = TEST_SIGNAL['timestamp_ms'] - 30 * 60 * 1000  # -30 minutes
    
    print(f"\nFetching klines from {datetime.fromtimestamp(start_time / 1000, tz=UTC)} to {datetime.fromtimestamp(end_time / 1000, tz=UTC)}")
    
    klines = await fetcher.get_klines(
        symbol=TEST_SIGNAL['symbol'],
        interval="15m",
        limit=100,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Find the candle with the exact timestamp
    target_candle = None
    for kline in klines:
        kline_time = int(kline['time'])
        if kline_time == TEST_SIGNAL['timestamp_ms']:
            target_candle = kline
            break
    
    if not target_candle:
        print("\nERROR: Could not find candle with exact timestamp")
        print("Available timestamps:")
        for kline in klines[:5]:
            print(f"  {int(kline['time'])}: {datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC)}")
        return
    
    print("\n" + "=" * 80)
    print("FOUND TARGET CANDLE")
    print("=" * 80)
    
    open_price = float(target_candle['open'])
    high_price = float(target_candle['high'])
    low_price = float(target_candle['low'])
    close_price = float(target_candle['close'])
    volume = float(target_candle['volume'])
    
    print(f"\nRaw data from BingX:")
    print(f"  time: {target_candle['time']}")
    print(f"  open: {target_candle['open']}")
    print(f"  high: {target_candle['high']}")
    print(f"  low: {target_candle['low']}")
    print(f"  close: {target_candle['close']}")
    print(f"  volume: {target_candle['volume']}")
    
    print(f"\nParsed values:")
    print(f"  Open: {open_price}")
    print(f"  High: {high_price}")
    print(f"  Low: {low_price}")
    print(f"  Close: {close_price}")
    print(f"  Volume: {volume}")
    
    # Calculate LW-001 conditions
    is_red = close_price < open_price
    body = open_price - close_price
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    wick_body_ratio = lower_wick / body if body > 0 else 0.0
    
    print(f"\nLW-001 Calculations:")
    print(f"  Is Red: {is_red}")
    print(f"  Body (Open - Close): {body}")
    print(f"  Lower Wick (Close - Low): {lower_wick}")
    print(f"  Upper Wick (High - Open): {upper_wick}")
    print(f"  Wick/Body Ratio: {wick_body_ratio:.4f}")
    
    print(f"\nQualification:")
    print(f"  Red Candle: {'PASS' if is_red else 'FAIL'}")
    print(f"  Lower Wick >= 2x Body: {'PASS' if wick_body_ratio >= 2.0 else 'FAIL'} ({wick_body_ratio:.4f}x)")
    
    # Check for the specific issue: Close == Low
    if close_price == low_price:
        print("\n" + "!" * 80)
        print("CRITICAL ISSUE DETECTED: Close == Low")
        print("This candle has NO lower wick!")
        print("!" * 80)
    else:
        print(f"\nLower wick exists: Close ({close_price}) > Low ({low_price})")
    
    # Check if this was actually sent as a signal
    qualified = is_red and wick_body_ratio >= 2.0
    print(f"\nOverall Qualified: {qualified}")
    
    if qualified and close_price == low_price:
        print("\n" + "!" * 80)
        print("ERROR: Candle with NO lower wick would be qualified!")
        print("This is the bug the user reported.")
        print("!" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_signal())
