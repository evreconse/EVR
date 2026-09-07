#!/usr/bin/env python3
"""
Diagnose 6 non-red signals by checking neighboring candles.

For each signal that shows green/neutral, check nearby M15 candles
to find the correct red candle that matches the user's manual signal.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# 6 signals that need diagnosis
DIAGNOSIS_SIGNALS = [
    ("TAO-USDT", 4, 6, 2026, 6, 0, 3, 0),
    ("DOT-USDT", 4, 6, 2026, 6, 15, 3, 15),
    ("ICP-USDT", 4, 6, 2026, 6, 45, 3, 45),
    ("ARB-USDT", 4, 6, 2026, 6, 0, 3, 0),
    ("ZRO-USDT", 4, 6, 2026, 6, 30, 3, 30),
    ("WIF-USDT", 4, 6, 2026, 6, 15, 3, 15),
]


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


async def diagnose_signal(
    symbol: str,
    day: int,
    month: int,
    year: int,
    hour_utc: int,
    minute_utc: int,
    hour_msk: int,
    minute_msk: int,
    fetcher: BingXFetcher,
) -> dict:
    """
    Diagnose a signal by checking neighboring candles.
    """
    target_time_utc = datetime(year, month, day, hour_utc, minute_utc, tzinfo=UTC)
    target_time_msk = datetime(year, month, day, hour_msk, minute_msk, tzinfo=UTC)
    
    # Fetch data around the target time (±4 hours)
    start_time = int((target_time_utc - timedelta(hours=4)).timestamp() * 1000)
    end_time = int((target_time_utc + timedelta(hours=4)).timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        return {
            "symbol": symbol,
            "error": f"API error: {e}",
            "found": False,
        }
    
    # Find all red candles in the vicinity
    red_candles = []
    
    for kline in klines:
        open_price = float(kline['open'])
        close_price = float(kline['close'])
        
        if close_price < open_price:  # Red candle
            timestamp_ms = int(kline['time'])
            candle_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            time_diff_minutes = abs((candle_time - target_time_utc).total_seconds() / 60)
            
            red_candles.append({
                "timestamp_ms": timestamp_ms,
                "candle_time_utc": candle_time,
                "candle_time_msk": candle_time + timedelta(hours=3),
                "time_diff_minutes": time_diff_minutes,
                "open": open_price,
                "high": float(kline['high']),
                "low": float(kline['low']),
                "close": close_price,
                "volume": float(kline['volume']),
            })
    
    # Sort by time difference
    red_candles.sort(key=lambda x: x["time_diff_minutes"])
    
    return {
        "symbol": symbol,
        "target_time_utc": target_time_utc,
        "target_time_msk": target_time_msk,
        "target_timestamp_ms": int(target_time_utc.timestamp() * 1000),
        "red_candles_nearby": red_candles[:10],  # Top 10 closest red candles
        "total_red_candles": len(red_candles),
    }


async def main():
    """Diagnose all 6 non-red signals."""
    print("=" * 120)
    print("DIAGNOSIS OF 6 NON-RED SIGNALS")
    print("=" * 120)
    print()
    print("Checking neighboring M15 candles to find the correct red candle.")
    print()
    
    fetcher = BingXFetcher()
    
    for symbol, day, month, year, hour_msk, minute_msk, hour_utc, minute_utc in DIAGNOSIS_SIGNALS:
        print(f"Diagnosing {symbol} at {day:02d}/{month:02d}/{year} {hour_utc:02d}:{minute_utc:02d} UTC ({hour_msk:02d}:{minute_msk:02d} MSK)...")
        
        result = await diagnose_signal(
            symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, fetcher
        )
        
        if result.get("error"):
            print(f"  ERROR: {result['error']}")
            continue
        
        print(f"  Target timestamp: {result['target_timestamp_ms']} ms")
        print(f"  Total red candles in ±4 hours: {result['total_red_candles']}")
        print()
        
        if result["red_candles_nearby"]:
            print(f"  Closest red candles:")
            print(f"  {'Diff (min)':<12} {'UTC Time':<20} {'MSK Time':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10}")
            print("  " + "-" * 110)
            
            for candle in result["red_candles_nearby"]:
                diff = candle["time_diff_minutes"]
                utc_time = format_utc_time(candle["candle_time_utc"])
                msk_time = format_msk_time(candle["candle_time_msk"])
                print(f"  {diff:<12.0f} {utc_time:<20} {msk_time:<20} "
                      f"{candle['open']:<10.6f} {candle['high']:<10.6f} {candle['low']:<10.6f} {candle['close']:<10.6f}")
            
            # Check if there's a red candle within ±15 minutes
            very_close = [c for c in result["red_candles_nearby"] if c["time_diff_minutes"] <= 15]
            if very_close:
                print(f"\n  [!] Found red candle(s) within ±15 minutes:")
                for candle in very_close:
                    print(f"      {format_utc_time(candle['candle_time_utc'])} ({candle['time_diff_minutes']:.0f} min diff)")
        else:
            print(f"  No red candles found in ±4 hours")
        
        print()
        print("=" * 120)
        print()


if __name__ == "__main__":
    asyncio.run(main())
