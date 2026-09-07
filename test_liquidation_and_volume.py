#!/usr/bin/env python3
"""
Test liquidation data fetch and new volume filter with known signals.

Test 1-3 known historical signals:
- ONE-USDT at 2026-08-12 01:15 UTC
- LUNC-USDT at 2026-08-12 11:00 UTC
- SUI-USDT at 2026-08-07 14:45 UTC
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher
from src.exchange.coinglass_fetcher import CoinGlassFetcher


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


async def test_signal(symbol: str, target_time_utc: datetime):
    """Test a single signal for volume filter and liquidation data."""
    print("=" * 80)
    print(f"TESTING: {symbol}")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    coinglass = CoinGlassFetcher()
    
    # Fetch BingX data around the target time
    start_time = int((target_time_utc - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time_utc + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    # Find the target candle
    target_kline = None
    previous_kline = None
    
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == target_time_utc:
            target_kline = kline
            if i > 0:
                previous_kline = klines[i - 1]
            break
    
    if not target_kline:
        print(f"ERROR: Target candle not found at {target_time_utc}")
        return
    
    # Parse target candle
    current_volume = float(target_kline['volume'])
    timestamp_ms = int(target_kline['time'])
    
    # Parse previous candle
    if previous_kline:
        previous_candle_volume = float(previous_kline['volume'])
        previous_time_ms = int(previous_kline['time'])
        previous_datetime = datetime.fromtimestamp(previous_time_ms / 1000, tz=UTC)
    else:
        print(f"WARNING: No previous candle found")
        previous_candle_volume = 0
        previous_datetime = None
    
    # Calculate volume ratio
    volume_ratio = current_volume / previous_candle_volume if previous_candle_volume > 0 else 0.0
    volume_qualified = volume_ratio >= 1.5
    
    print(f"\nBINGX DATA:")
    print(f"  Symbol: {symbol}")
    print(f"  Target Time UTC: {target_time_utc}")
    print(f"  Target Time MSK: {format_msk_time(target_time_utc)}")
    print(f"  Timestamp (ms): {timestamp_ms}")
    print(f"\n  Current Volume: {current_volume:,.0f}")
    print(f"  Previous Candle Time UTC: {previous_datetime}")
    print(f"  Previous Candle Volume: {previous_candle_volume:,.0f}")
    print(f"  Volume Ratio: {volume_ratio:.2f}x")
    print(f"  Volume Qualified (>= 1.5x): {volume_qualified}")
    
    # Fetch CoinGlass liquidation data
    print(f"\nCOINGLASS DATA:")
    try:
        liquidation_data = await coinglass.get_liquidation_for_candle(symbol, timestamp_ms)
        
        if liquidation_data:
            print(f"  Long Liquidation USD: ${liquidation_data['long_liquidation_usd']:,.0f}")
            print(f"  Short Liquidation USD: ${liquidation_data['short_liquidation_usd']:,.0f}")
            print(f"  Total Liquidation USD: ${liquidation_data['long_liquidation_usd'] + liquidation_data['short_liquidation_usd']:,.0f}")
            print(f"  Timestamp Match: {liquidation_data['timestamp'] == timestamp_ms}")
        else:
            print(f"  No liquidation data found for this candle")
            print(f"  Trying to fetch history around this time...")
            
            # Try to fetch history to see what's available
            history = await coinglass.get_liquidation_history(
                symbol=symbol,
                start_time=timestamp_ms - (60 * 60 * 1000),  # 1 hour before
                end_time=timestamp_ms + (60 * 60 * 1000),  # 1 hour after
                limit=20,
            )
            
            print(f"  Found {len(history)} liquidation records in the 2-hour window")
            if history:
                print(f"\n  Nearest records:")
                for record in history[:5]:
                    rec_time = record.get("time")
                    rec_datetime = datetime.fromtimestamp(rec_time / 1000, tz=UTC)
                    time_diff = abs(rec_time - timestamp_ms) / 1000 / 60  # minutes
                    print(f"    {rec_datetime} ({time_diff:.0f} min diff): Long=${record.get('longLiquidation', 0):,.0f}, Short=${record.get('shortLiquidation', 0):,.0f}")
    
    except Exception as e:
        print(f"  ERROR fetching liquidation data: {e}")
    
    print()


async def main():
    """Test 3 known signals."""
    print("=" * 80)
    print("TESTING LIQUIDATION DATA AND NEW VOLUME FILTER")
    print("=" * 80)
    print()
    
    # Test signals from the recent batch
    test_signals = [
        ("ONE-USDT", datetime(2026, 8, 12, 1, 15, tzinfo=UTC)),
        ("LUNC-USDT", datetime(2026, 8, 12, 11, 0, tzinfo=UTC)),
        ("SUI-USDT", datetime(2026, 8, 7, 14, 45, tzinfo=UTC)),
    ]
    
    for symbol, target_time in test_signals:
        await test_signal(symbol, target_time)
    
    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
