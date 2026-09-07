#!/usr/bin/env python3
"""
Verify all 42 manual signals with EXACT original timestamps.
NO adjustments, NO shifting to nearest red candles.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# 42 manual signals with ORIGINAL MSK times (no changes)
MANUAL_SIGNALS = [
    # Format: (symbol, day, month, year, hour_msk, minute_msk)
    ("WLD-USDT", 4, 6, 2026, 5, 0),
    ("NEAR-USDT", 5, 6, 2026, 19, 0),
    ("ONDO-USDT", 4, 6, 2026, 6, 15),
    ("TAO-USDT", 4, 6, 2026, 6, 0),
    ("ENA-USDT", 4, 6, 2026, 5, 0),
    ("ENA-USDT", 5, 6, 2026, 9, 15),
    ("WLFI-USDT", 4, 6, 2026, 5, 0),
    ("WLFI-USDT", 5, 6, 2026, 9, 15),
    ("DOT-USDT", 4, 6, 2026, 6, 15),
    ("DOT-USDT", 5, 6, 2026, 9, 15),
    ("UNI-USDT", 4, 6, 2026, 7, 45),
    ("UNI-USDT", 5, 6, 2026, 9, 15),
    ("ATOM-USDT", 4, 6, 2026, 4, 45),
    ("INJ-USDT", 4, 6, 2026, 6, 45),
    ("CRLC-USDT", 6, 6, 2026, 8, 0),
    ("XPL-USDT", 4, 6, 2026, 8, 0),
    ("FARTCOIN-USDT", 4, 6, 2026, 7, 15),
    ("FF-USDT", 5, 6, 2026, 20, 0),
    ("TRUMP-USDT", 4, 6, 2026, 5, 0),
    ("ICP-USDT", 2, 6, 2026, 21, 0),
    ("ICP-USDT", 4, 6, 2026, 6, 45),
    ("DRAM-USDT", 6, 6, 2026, 6, 45),
    ("SIREN-USDT", 2, 6, 2026, 16, 30),
    ("SIREN-USDT", 4, 6, 2026, 5, 0),
    ("SIREN-USDT", 4, 6, 2026, 10, 15),
    ("SIREN-USDT", 7, 6, 2026, 22, 30),
    ("ARB-USDT", 4, 6, 2026, 6, 0),
    ("APT-USDT", 4, 6, 2026, 8, 15),
    ("ZRO-USDT", 4, 6, 2026, 6, 30),
    ("KITE-USDT", 4, 6, 2026, 6, 30),
    ("MON-USDT", 4, 6, 2026, 6, 45),
    ("MON-USDT", 5, 6, 2026, 9, 15),
    ("CRV-USDT", 4, 6, 2026, 5, 0),
    ("WIF-USDT", 4, 6, 2026, 6, 15),
    ("PENGU-USDT", 4, 6, 2026, 5, 0),
    ("VIRTUAL-USDT", 4, 6, 2026, 5, 0),
    ("SEI-USDT", 4, 6, 2026, 5, 0),
    ("HOME-USDT", 4, 6, 2026, 20, 45),
    ("RENDER-USDT", 4, 6, 2026, 5, 0),
    ("PENDLE-USDT", 4, 6, 2026, 5, 0),
    ("POL-USDT", 4, 6, 2026, 5, 0),
    ("OP-USDT", 4, 6, 2026, 5, 0),
]


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def get_candle_color(open_price: float, close_price: float) -> str:
    """Get candle color."""
    if close_price < open_price:
        return "RED"
    elif close_price > open_price:
        return "GREEN"
    else:
        return "NEUTRAL"


async def verify_signal_exact(
    symbol: str,
    day: int,
    month: int,
    year: int,
    hour_msk: int,
    minute_msk: int,
    fetcher: BingXFetcher,
) -> dict:
    """
    Verify a single signal with EXACT original timestamp.
    NO adjustments.
    """
    # Create original MSK time
    target_time_msk = datetime(year, month, day, hour_msk, minute_msk, tzinfo=UTC)
    
    # Convert MSK to UTC (MSK = UTC+3)
    target_time_utc = target_time_msk - timedelta(hours=3)
    
    # Calculate expected timestamp (start of M15 interval)
    expected_timestamp_ms = int(target_time_utc.timestamp() * 1000)
    
    # Verify M15 alignment
    minutes = target_time_utc.minute
    is_m15_aligned = minutes % 15 == 0
    
    # Fetch data around the target time (±2 hours to get previous/next candles)
    start_time = int((target_time_utc - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time_utc + timedelta(hours=2)).timestamp() * 1000)
    
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
            "original_msk": target_time_msk,
            "requested_utc": target_time_utc,
            "expected_timestamp_ms": expected_timestamp_ms,
            "is_m15_aligned": is_m15_aligned,
            "status": "UNVERIFIED",
            "error": f"API error: {e}",
            "found": False,
        }
    
    # Find exact candle by timestamp
    target_kline = None
    candle_index = -1
    
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        if kline_time == expected_timestamp_ms:
            target_kline = kline
            candle_index = i
            break
    
    if not target_kline:
        return {
            "symbol": symbol,
            "original_msk": target_time_msk,
            "requested_utc": target_time_utc,
            "expected_timestamp_ms": expected_timestamp_ms,
            "is_m15_aligned": is_m15_aligned,
            "status": "UNVERIFIED",
            "error": "Candle not found at exact timestamp",
            "found": False,
        }
    
    # Parse OHLC
    open_price = float(target_kline['open'])
    high_price = float(target_kline['high'])
    low_price = float(target_kline['low'])
    close_price = float(target_kline['close'])
    volume = float(target_kline['volume'])
    timestamp_ms = int(target_kline['time'])
    
    # Check candle color
    color = get_candle_color(open_price, close_price)
    
    # Determine status
    if color == "RED":
        status = "VERIFIED"
    else:
        status = "DATA MISMATCH"
    
    # Get previous and next candles for mismatched cases
    previous_candle = None
    next_candle = None
    
    if status == "DATA MISMATCH":
        if candle_index > 0:
            prev_kline = klines[candle_index - 1]
            previous_candle = {
                "timestamp_ms": int(prev_kline['time']),
                "datetime_utc": datetime.fromtimestamp(int(prev_kline['time']) / 1000, tz=UTC),
                "open": float(prev_kline['open']),
                "high": float(prev_kline['high']),
                "low": float(prev_kline['low']),
                "close": float(prev_kline['close']),
                "color": get_candle_color(float(prev_kline['open']), float(prev_kline['close'])),
            }
        
        if candle_index < len(klines) - 1:
            next_kline = klines[candle_index + 1]
            next_candle = {
                "timestamp_ms": int(next_kline['time']),
                "datetime_utc": datetime.fromtimestamp(int(next_kline['time']) / 1000, tz=UTC),
                "open": float(next_kline['open']),
                "high": float(next_kline['high']),
                "low": float(next_kline['low']),
                "close": float(next_kline['close']),
                "color": get_candle_color(float(next_kline['open']), float(next_kline['close'])),
            }
    
    return {
        "symbol": symbol,
        "original_msk": target_time_msk,
        "requested_utc": target_time_utc,
        "expected_timestamp_ms": expected_timestamp_ms,
        "actual_timestamp_ms": timestamp_ms,
        "timestamp_match": timestamp_ms == expected_timestamp_ms,
        "is_m15_aligned": is_m15_aligned,
        "status": status,
        "found": True,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "color": color,
        "previous_candle": previous_candle,
        "next_candle": next_candle,
    }


async def main():
    """Verify all 42 signals with exact original timestamps."""
    print("=" * 140)
    print("VERIFICATION OF 42 MANUAL SIGNALS WITH EXACT ORIGINAL TIMESTAMPS")
    print("=" * 140)
    print()
    print("NO adjustments, NO shifting to nearest red candles.")
    print("Using EXACT original MSK times converted to UTC for API requests.")
    print()
    
    fetcher = BingXFetcher()
    
    all_results = []
    
    for i, (symbol, day, month, year, hour_msk, minute_msk) in enumerate(MANUAL_SIGNALS, 1):
        print(f"[{i}/42] Verifying {symbol} at {day:02d}/{month:02d}/{year} {hour_msk:02d}:{minute_msk:02d} MSK...")
        
        result = await verify_signal_exact(
            symbol, day, month, year, hour_msk, minute_msk, fetcher
        )
        
        all_results.append(result)
        
        if result["found"]:
            print(f"  [{result['status']}] {result['color']}: O={result['open']:.6f} H={result['high']:.6f} L={result['low']:.6f} C={result['close']:.6f}")
        else:
            print(f"  [{result['status']}] {result.get('error', 'Unknown')}")
    
    print()
    print("=" * 140)
    print("SUMMARY TABLE")
    print("=" * 140)
    print()
    
    # Print table
    print(f"{'#':<3} {'Symbol':<15} {'Original MSK':<20} {'Requested UTC':<20} {'Exact M15 found':<15} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Color':<8} {'Status':<12}")
    print("-" * 140)
    
    for i, result in enumerate(all_results, 1):
        original_msk = format_msk_time(result["original_msk"])
        requested_utc = format_utc_time(result["requested_utc"])
        exact_found = "YES" if result["found"] else "NO"
        
        if result["found"]:
            print(f"{i:<3} {result['symbol']:<15} {original_msk:<20} {requested_utc:<20} {exact_found:<15} "
                  f"{result['open']:<10.6f} {result['high']:<10.6f} {result['low']:<10.6f} {result['close']:<10.6f} "
                  f"{result['color']:<8} {result['status']:<12}")
        else:
            print(f"{i:<3} {result['symbol']:<15} {original_msk:<20} {requested_utc:<20} {exact_found:<15} "
                  f"{'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<8} {result['status']:<12}")
    
    print()
    print("=" * 140)
    print("STATUS BREAKDOWN")
    print("=" * 140)
    
    verified = sum(1 for r in all_results if r["status"] == "VERIFIED")
    unverified = sum(1 for r in all_results if r["status"] == "UNVERIFIED")
    mismatch = sum(1 for r in all_results if r["status"] == "DATA MISMATCH")
    
    print(f"VERIFIED (red candle at exact timestamp): {verified}")
    print(f"UNVERIFIED (candle not found or API error): {unverified}")
    print(f"DATA MISMATCH (non-red candle at exact timestamp): {mismatch}")
    print(f"Total: {len(all_results)}")
    
    # Detailed info for DATA MISMATCH cases
    if mismatch > 0:
        print()
        print("=" * 140)
        print("DETAILED INFO FOR DATA MISMATCH CASES")
        print("=" * 140)
        
        for result in all_results:
            if result["status"] == "DATA MISMATCH":
                print()
                print(f"Symbol: {result['symbol']}")
                print(f"  Original MSK: {format_msk_time(result['original_msk'])}")
                print(f"  Requested UTC: {format_utc_time(result['requested_utc'])}")
                print(f"  Expected timestamp: {result['expected_timestamp_ms']} ms")
                print(f"  Actual timestamp: {result['actual_timestamp_ms']} ms")
                print(f"  Timestamp match: {result['timestamp_match']}")
                print(f"  M15 aligned: {result['is_m15_aligned']}")
                print()
                print(f"  REQUESTED CANDLE (at exact timestamp):")
                print(f"    Timestamp: {result['actual_timestamp_ms']} ms")
                print(f"    UTC: {format_utc_time(result['requested_utc'])}")
                print(f"    OHLC: O={result['open']:.6f} H={result['high']:.6f} L={result['low']:.6f} C={result['close']:.6f}")
                print(f"    Color: {result['color']}")
                
                if result["previous_candle"]:
                    print()
                    print(f"  PREVIOUS M15 CANDLE:")
                    print(f"    Timestamp: {result['previous_candle']['timestamp_ms']} ms")
                    print(f"    UTC: {format_utc_time(result['previous_candle']['datetime_utc'])}")
                    print(f"    OHLC: O={result['previous_candle']['open']:.6f} H={result['previous_candle']['high']:.6f} "
                          f"L={result['previous_candle']['low']:.6f} C={result['previous_candle']['close']:.6f}")
                    print(f"    Color: {result['previous_candle']['color']}")
                
                if result["next_candle"]:
                    print()
                    print(f"  NEXT M15 CANDLE:")
                    print(f"    Timestamp: {result['next_candle']['timestamp_ms']} ms")
                    print(f"    UTC: {format_utc_time(result['next_candle']['datetime_utc'])}")
                    print(f"    OHLC: O={result['next_candle']['open']:.6f} H={result['next_candle']['high']:.6f} "
                          f"L={result['next_candle']['low']:.6f} C={result['next_candle']['close']:.6f}")
                    print(f"    Color: {result['next_candle']['color']}")
                
                print()
                print("-" * 140)
    
    # Save results
    import json
    
    serializable_results = []
    for r in all_results:
        r_copy = r.copy()
        r_copy["original_msk"] = format_msk_time(r["original_msk"])
        r_copy["requested_utc"] = format_utc_time(r["requested_utc"])
        
        if r.get("previous_candle"):
            r_copy["previous_candle"]["datetime_utc"] = format_utc_time(r["previous_candle"]["datetime_utc"])
        if r.get("next_candle"):
            r_copy["next_candle"]["datetime_utc"] = format_utc_time(r["next_candle"]["datetime_utc"])
        
        serializable_results.append(r_copy)
    
    output = {
        "verified": verified,
        "unverified": unverified,
        "data_mismatch": mismatch,
        "results": serializable_results,
    }
    
    with open("original_timestamps_verification.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to original_timestamps_verification.json")


if __name__ == "__main__":
    asyncio.run(main())
