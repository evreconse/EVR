#!/usr/bin/env python3
"""
Test fixed fetch: Verify that removing limit parameter enables full 60-day range
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta
from collections import defaultdict


def format_timestamp_utc3(timestamp_ms):
    """Convert raw candle timestamp to UTC+3 format."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, UTC)
    dt_utc3 = dt_utc + timedelta(hours=3)
    utc3_str = dt_utc3.strftime("%d.%m.%Y %H:%M UTC+3")
    return utc3_str


def count_candles_by_month(candles):
    """Count candles by month."""
    counts = defaultdict(int)
    for candle in candles:
        timestamp = candle.get('time', candle.get('timestamp', 0))
        dt = datetime.fromtimestamp(timestamp / 1000, UTC)
        month_key = dt.strftime("%Y-%m")
        counts[month_key] += 1
    return counts


async def test_fixed_fetch(symbol: str = "SAND-USDT", days: int = 60):
    """Test fetch with fixed code (no limit parameter)."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    print("="*100)
    print(f"TEST: Fixed Fetch for {symbol}")
    print("="*100)
    print()
    print(f"Requested range:")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Duration: {days} days")
    print(f"  Expected candles: {days * 24 * 4} (at 15m interval)")
    print()
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles:
            print("ERROR: No candles returned")
            return False
        
        print(f"Actual returned:")
        first_timestamp = candles[0].get('time', candles[0].get('timestamp', 0))
        last_timestamp = candles[-1].get('time', candles[-1].get('timestamp', 0))
        
        print(f"  First candle: {format_timestamp_utc3(first_timestamp)}")
        print(f"  Last candle: {format_timestamp_utc3(last_timestamp)}")
        print(f"  Total candles: {len(candles)}")
        print()
        
        # Count by month
        monthly_counts = count_candles_by_month(candles)
        print(f"Candles by month:")
        for month in sorted(monthly_counts.keys()):
            print(f"  {month}: {monthly_counts[month]} candles")
        print()
        
        # Verify coverage
        actual_days = len(candles) / (24 * 4)
        print(f"Coverage analysis:")
        print(f"  Actual days covered: {actual_days:.2f} days")
        print(f"  Expected days: {days} days")
        
        if actual_days >= days * 0.95:  # Allow 5% margin
            print(f"  Result: PASS - Full 60-day range covered")
            return True
        else:
            print(f"  Result: FAIL - Only {actual_days:.2f} days covered")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run test on multiple symbols."""
    test_symbols = ["SAND-USDT", "FET-USDT", "TRX-USDT"]
    
    results = []
    
    for symbol in test_symbols:
        result = await test_fixed_fetch(symbol, days=60)
        results.append((symbol, result))
        print()
        print("-" * 100)
        print()
    
    print("="*100)
    print("TEST SUMMARY")
    print("="*100)
    print()
    for symbol, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol}: {status}")
    print()
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("RESULT: All tests passed - Fix verified")
    else:
        print("RESULT: Some tests failed - Fix needs review")


if __name__ == "__main__":
    asyncio.run(main())
