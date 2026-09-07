#!/usr/bin/env python3
"""
Verify all 42 manual signals with detailed diagnostics.

CRITICAL: All 42 original signals were RED candles.
If BingX shows green/neutral, diagnose the timestamp/candle matching error first.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# 42 manual signals with MSK and UTC times
MANUAL_SIGNALS = [
    # Format: (symbol, day, month, year, hour_msk, minute_msk, hour_utc, minute_utc)
    ("WLD-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("NEAR-USDT", 5, 6, 2026, 19, 0, 16, 0),
    ("ONDO-USDT", 4, 6, 2026, 6, 15, 3, 15),
    ("TAO-USDT", 4, 6, 2026, 6, 0, 3, 0),
    ("ENA-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("ENA-USDT", 5, 6, 2026, 9, 15, 6, 15),
    ("WLFI-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("WLFI-USDT", 5, 6, 2026, 9, 15, 6, 15),
    ("DOT-USDT", 4, 6, 2026, 6, 15, 3, 15),
    ("DOT-USDT", 5, 6, 2026, 9, 15, 6, 15),
    ("UNI-USDT", 4, 6, 2026, 7, 45, 4, 45),
    ("UNI-USDT", 5, 6, 2026, 9, 15, 6, 15),
    ("ATOM-USDT", 4, 6, 2026, 4, 45, 1, 45),
    ("INJ-USDT", 4, 6, 2026, 6, 45, 3, 45),
    ("CRLC-USDT", 6, 6, 2026, 8, 0, 5, 0),
    ("XPL-USDT", 4, 6, 2026, 8, 0, 5, 0),
    ("FARTCOIN-USDT", 4, 6, 2026, 7, 15, 4, 15),
    ("FF-USDT", 5, 6, 2026, 20, 0, 17, 0),
    ("TRUMP-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("ICP-USDT", 2, 6, 2026, 21, 0, 18, 0),
    ("ICP-USDT", 4, 6, 2026, 6, 45, 3, 45),
    ("DRAM-USDT", 6, 6, 2026, 6, 45, 3, 45),
    ("SIREN-USDT", 2, 6, 2026, 16, 30, 13, 30),
    ("SIREN-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("SIREN-USDT", 4, 6, 2026, 10, 15, 7, 15),
    ("SIREN-USDT", 7, 6, 2026, 22, 30, 19, 30),
    ("ARB-USDT", 4, 6, 2026, 6, 0, 3, 0),
    ("APT-USDT", 4, 6, 2026, 8, 15, 5, 15),
    ("ZRO-USDT", 4, 6, 2026, 6, 30, 3, 30),
    ("KITE-USDT", 4, 6, 2026, 6, 30, 3, 30),
    ("MON-USDT", 4, 6, 2026, 6, 45, 3, 45),
    ("MON-USDT", 5, 6, 2026, 9, 15, 6, 15),
    ("CRV-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("WIF-USDT", 4, 6, 2026, 6, 15, 3, 15),
    ("PENGU-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("VIRTUAL-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("SEI-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("HOME-USDT", 4, 6, 2026, 20, 45, 17, 45),
    ("RENDER-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("PENDLE-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("POL-USDT", 4, 6, 2026, 5, 0, 2, 0),
    ("OP-USDT", 4, 6, 2026, 5, 0, 2, 0),
]


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


async def verify_signal_with_diagnostics(
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
    Verify a single manual signal with detailed diagnostics.
    """
    # Create target datetime
    target_time_utc = datetime(year, month, day, hour_utc, minute_utc, tzinfo=UTC)
    target_time_msk = datetime(year, month, day, hour_msk, minute_msk, tzinfo=UTC)
    
    # Calculate expected timestamp (start of M15 interval)
    expected_timestamp_ms = int(target_time_utc.timestamp() * 1000)
    
    # Verify M15 alignment
    minutes = target_time_utc.minute
    is_m15_aligned = minutes % 15 == 0
    
    # Fetch data around the target time (±4 hours for diagnostics)
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
            "target_time_utc": target_time_utc,
            "target_time_msk": target_time_msk,
            "expected_timestamp_ms": expected_timestamp_ms,
            "error": f"API error: {e}",
            "found": False,
            "is_m15_aligned": is_m15_aligned,
        }
    
    # Find exact candle by timestamp
    target_kline = None
    candle_index = -1
    
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_time == expected_timestamp_ms:
            target_kline = kline
            candle_index = i
            break
    
    # If exact match not found, find nearest candles for diagnostics
    nearest_before = None
    nearest_after = None
    
    if not target_kline:
        for i, kline in enumerate(klines):
            kline_time = int(kline['time'])
            if kline_time < expected_timestamp_ms:
                nearest_before = (i, kline)
            elif kline_time > expected_timestamp_ms and nearest_after is None:
                nearest_after = (i, kline)
    
    if target_kline:
        # Parse OHLC
        open_price = float(target_kline['open'])
        high_price = float(target_kline['high'])
        low_price = float(target_kline['low'])
        close_price = float(target_kline['close'])
        volume = float(target_kline['volume'])
        timestamp_ms = int(target_kline['time'])
        
        # Check if red
        is_red = close_price < open_price
        is_neutral = close_price == open_price
        is_green = close_price > open_price
        
        return {
            "symbol": symbol,
            "target_time_utc": target_time_utc,
            "target_time_msk": target_time_msk,
            "expected_timestamp_ms": expected_timestamp_ms,
            "actual_timestamp_ms": timestamp_ms,
            "timestamp_match": timestamp_ms == expected_timestamp_ms,
            "is_m15_aligned": is_m15_aligned,
            "found": True,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
            "is_red": is_red,
            "is_neutral": is_neutral,
            "is_green": is_green,
            "needs_diagnosis": not is_red,
        }
    else:
        return {
            "symbol": symbol,
            "target_time_utc": target_time_utc,
            "target_time_msk": target_time_msk,
            "expected_timestamp_ms": expected_timestamp_ms,
            "found": False,
            "is_m15_aligned": is_m15_aligned,
            "nearest_before_time": int(nearest_before[1]['time']) if nearest_before else None,
            "nearest_after_time": int(nearest_after[1]['time']) if nearest_after else None,
            "error": "Candle not found at exact timestamp",
        }


async def main():
    """Verify all 42 manual signals with diagnostics."""
    print("=" * 120)
    print("VERIFICATION OF 42 MANUAL LW-001 SIGNALS WITH DETAILED DIAGNOSTICS")
    print("=" * 120)
    print()
    print("CRITICAL: All 42 original signals were RED candles.")
    print("If BingX shows green/neutral, diagnose the timestamp/candle matching error first.")
    print()
    
    fetcher = BingXFetcher()
    
    # Verify all signals
    all_results = []
    not_found = []
    needs_diagnosis = []
    confirmed_red = []
    
    for i, (symbol, day, month, year, hour_msk, minute_msk, hour_utc, minute_utc) in enumerate(MANUAL_SIGNALS, 1):
        print(f"[{i}/42] Verifying {symbol} at {day:02d}/{month:02d}/{year} {hour_utc:02d}:{minute_utc:02d} UTC...")
        
        result = await verify_signal_with_diagnostics(
            symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, fetcher
        )
        
        all_results.append(result)
        
        if result["found"]:
            if result["is_red"]:
                confirmed_red.append(result)
                print(f"  [OK] RED candle confirmed: O={result['open']:.6f} H={result['high']:.6f} L={result['low']:.6f} C={result['close']:.6f}")
            else:
                needs_diagnosis.append(result)
                color = "NEUTRAL" if result["is_neutral"] else "GREEN"
                print(f"  [!] DIAGNOSIS NEEDED: {color} candle found (expected RED)")
                print(f"      O={result['open']:.6f} H={result['high']:.6f} L={result['low']:.6f} C={result['close']:.6f}")
                print(f"      Timestamp match: {result['timestamp_match']}")
                print(f"      M15 aligned: {result['is_m15_aligned']}")
        else:
            not_found.append(result)
            print(f"  [X] NOT FOUND: {result.get('error', 'Unknown')}")
            if result.get('nearest_before_time'):
                print(f"      Nearest before: {result['nearest_before_time']} ms")
            if result.get('nearest_after_time'):
                print(f"      Nearest after: {result['nearest_after_time']} ms")
    
    print()
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)
    print(f"Total signals: {len(MANUAL_SIGNALS)}")
    print(f"Confirmed RED: {len(confirmed_red)}")
    print(f"Needs diagnosis (not RED): {len(needs_diagnosis)}")
    print(f"Not found: {len(not_found)}")
    
    # Detailed diagnosis for non-red candles
    if needs_diagnosis:
        print()
        print("=" * 120)
        print("DETAILED DIAGNOSIS FOR NON-RED CANDLES")
        print("=" * 120)
        
        for result in needs_diagnosis:
            print(f"\nSymbol: {result['symbol']}")
            print(f"  Target MSK: {format_msk_time(result['target_time_msk'])}")
            print(f"  Target UTC: {format_utc_time(result['target_time_utc'])}")
            print(f"  Expected timestamp: {result['expected_timestamp_ms']} ms")
            print(f"  Actual timestamp: {result['actual_timestamp_ms']} ms")
            print(f"  Timestamp match: {result['timestamp_match']}")
            print(f"  M15 aligned: {result['is_m15_aligned']}")
            print(f"  OHLC: O={result['open']:.6f} H={result['high']:.6f} L={result['low']:.6f} C={result['close']:.6f}")
            print(f"  Color: {'NEUTRAL' if result['is_neutral'] else 'GREEN'}")
            print(f"  Body: {abs(result['open'] - result['close']):.6f}")
    
    # Save results
    import json
    
    serializable_results = []
    for r in all_results:
        r_copy = r.copy()
        if "target_time_utc" in r_copy:
            r_copy["target_time_utc"] = format_utc_time(r["target_time_utc"])
        if "target_time_msk" in r_copy:
            r_copy["target_time_msk"] = format_msk_time(r["target_time_msk"])
        serializable_results.append(r_copy)
    
    output = {
        "confirmed_red": len(confirmed_red),
        "needs_diagnosis": len(needs_diagnosis),
        "not_found": len(not_found),
        "results": serializable_results,
    }
    
    with open("manual_signals_verification.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to manual_signals_verification.json")


if __name__ == "__main__":
    asyncio.run(main())
