#!/usr/bin/env python3
"""
Recalculate all metrics for confirmed red candles only.

For the 6 non-red cases, use the closest red candle found during diagnosis.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# Corrected signal list with adjusted timestamps for non-red cases
# Format: (symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, note)
CORRECTED_SIGNALS = [
    # Original confirmed red candles (31)
    ("WLD-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("NEAR-USDT", 5, 6, 2026, 16, 0, 19, 0, "original"),
    ("ONDO-USDT", 4, 6, 2026, 3, 15, 6, 15, "original"),
    # TAO-USDT: Use 02:45 UTC (15 min before) - closest red candle
    ("TAO-USDT", 4, 6, 2026, 2, 45, 5, 45, "adjusted: 02:45 UTC (15 min before)"),
    ("ENA-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("ENA-USDT", 5, 6, 2026, 6, 15, 9, 15, "original"),
    ("WLFI-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("WLFI-USDT", 5, 6, 2026, 6, 15, 9, 15, "original"),
    # DOT-USDT: Use 02:45 UTC (30 min before) - closest red candle
    ("DOT-USDT", 4, 6, 2026, 2, 45, 5, 45, "adjusted: 02:45 UTC (30 min before)"),
    ("DOT-USDT", 5, 6, 2026, 6, 15, 9, 15, "original"),
    ("UNI-USDT", 4, 6, 2026, 4, 45, 7, 45, "original"),
    ("UNI-USDT", 5, 6, 2026, 6, 15, 9, 15, "original"),
    ("ATOM-USDT", 4, 6, 2026, 1, 45, 4, 45, "original"),
    ("INJ-USDT", 4, 6, 2026, 3, 45, 6, 45, "original"),
    # CRLC-USDT: Not found - skip
    ("XPL-USDT", 4, 6, 2026, 5, 0, 8, 0, "original"),
    ("FARTCOIN-USDT", 4, 6, 2026, 4, 15, 7, 15, "original"),
    ("FF-USDT", 5, 6, 2026, 17, 0, 20, 0, "original"),
    # TRUMP-USDT: Not found - skip
    ("ICP-USDT", 2, 6, 2026, 18, 0, 21, 0, "original"),
    # ICP-USDT: Use 03:15 UTC (30 min before) - closest red candle
    ("ICP-USDT", 4, 6, 2026, 3, 15, 6, 15, "adjusted: 03:15 UTC (30 min before)"),
    # DRAM-USDT: Not found - skip
    ("SIREN-USDT", 2, 6, 2026, 13, 30, 16, 30, "original"),
    ("SIREN-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("SIREN-USDT", 4, 6, 2026, 7, 15, 10, 15, "original"),
    ("SIREN-USDT", 7, 6, 2026, 19, 30, 22, 30, "original"),
    # ARB-USDT: Use 02:45 UTC (15 min before) - closest red candle
    ("ARB-USDT", 4, 6, 2026, 2, 45, 5, 45, "adjusted: 02:45 UTC (15 min before)"),
    ("APT-USDT", 4, 6, 2026, 5, 15, 8, 15, "original"),
    # ZRO-USDT: Use 03:15 UTC (15 min before) - closest red candle
    ("ZRO-USDT", 4, 6, 2026, 3, 15, 6, 15, "adjusted: 03:15 UTC (15 min before)"),
    ("KITE-USDT", 4, 6, 2026, 3, 30, 6, 30, "original"),
    # MON-USDT: Not found - skip both
    ("CRV-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    # WIF-USDT: Use 02:45 UTC (30 min before) - closest red candle
    ("WIF-USDT", 4, 6, 2026, 2, 45, 5, 45, "adjusted: 02:45 UTC (30 min before)"),
    ("PENGU-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("VIRTUAL-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("SEI-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("HOME-USDT", 4, 6, 2026, 17, 45, 20, 45, "original"),
    ("RENDER-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("PENDLE-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("POL-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
    ("OP-USDT", 4, 6, 2026, 2, 0, 5, 0, "original"),
]


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def calculate_metrics(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Calculate all metrics for a red candle."""
    # For red candle
    body = open_price - close_price
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    candle_range = high_price - low_price
    
    # Ratios
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    upper_wick_body_ratio = upper_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    body_range_ratio = body / candle_range if candle_range > 0 else 0
    
    return {
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "candle_range": candle_range,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "upper_wick_body_ratio": upper_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "body_range_ratio": body_range_ratio,
    }


async def fetch_and_analyze_signal(
    symbol: str,
    day: int,
    month: int,
    year: int,
    hour_utc: int,
    minute_utc: int,
    hour_msk: int,
    minute_msk: int,
    note: str,
    fetcher: BingXFetcher,
) -> dict:
    """Fetch and analyze a single corrected signal."""
    target_time_utc = datetime(year, month, day, hour_utc, minute_utc, tzinfo=UTC)
    target_time_msk = datetime(year, month, day, hour_msk, minute_msk, tzinfo=UTC)
    
    # Fetch data around the target time (±2 hours)
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
            "error": f"API error: {e}",
            "found": False,
        }
    
    # Find exact candle by timestamp
    target_kline = None
    candle_index = -1
    
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == target_time_utc:
            target_kline = kline
            candle_index = i
            break
    
    if not target_kline:
        return {
            "symbol": symbol,
            "error": "Candle not found at corrected timestamp",
            "found": False,
        }
    
    # Parse OHLC
    open_price = float(target_kline['open'])
    high_price = float(target_kline['high'])
    low_price = float(target_kline['low'])
    close_price = float(target_kline['close'])
    volume = float(target_kline['volume'])
    timestamp_ms = int(target_kline['time'])
    
    # Check if red
    is_red = close_price < open_price
    
    if not is_red:
        return {
            "symbol": symbol,
            "error": "Corrected candle is still not red",
            "found": False,
        }
    
    # Calculate metrics
    metrics = calculate_metrics(open_price, high_price, low_price, close_price)
    
    # Get previous candle volume
    if candle_index > 0:
        previous_volume = float(klines[candle_index - 1]['volume'])
        volume_ratio = volume / previous_volume if previous_volume > 0 else 0
    else:
        previous_volume = 0
        volume_ratio = 0
    
    return {
        "symbol": symbol,
        "target_time_utc": target_time_utc,
        "target_time_msk": target_time_msk,
        "timestamp_ms": timestamp_ms,
        "note": note,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "previous_volume": previous_volume,
        "volume_ratio": volume_ratio,
        "is_red": True,
        "found": True,
        **metrics,
    }


async def main():
    """Recalculate metrics for all corrected signals."""
    print("=" * 120)
    print("RECALCULATING METRICS FOR CORRECTED RED CANDLES")
    print("=" * 120)
    print()
    
    fetcher = BingXFetcher()
    
    all_signals = []
    not_found = []
    
    for i, (symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, note) in enumerate(CORRECTED_SIGNALS, 1):
        print(f"[{i}/{len(CORRECTED_SIGNALS)}] Fetching {symbol} at {day:02d}/{month:02d}/{year} {hour_utc:02d}:{minute_utc:02d} UTC ({note})...")
        
        signal_data = await fetch_and_analyze_signal(
            symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, note, fetcher
        )
        
        if signal_data["found"]:
            all_signals.append(signal_data)
            print(f"  [OK] RED: O={signal_data['open']:.6f} H={signal_data['high']:.6f} L={signal_data['low']:.6f} C={signal_data['close']:.6f}")
            print(f"       Body={signal_data['body']:.6f} LW={signal_data['lower_wick']:.6f} UW={signal_data['upper_wick']:.6f}")
            print(f"       LW/Body={signal_data['lower_wick_body_ratio']:.2f}x LW/Range={signal_data['lower_wick_range_ratio']:.2f} VolRatio={signal_data['volume_ratio']:.2f}x")
        else:
            not_found.append(signal_data)
            print(f"  [X] {signal_data.get('error', 'Unknown')}")
    
    print()
    print("=" * 120)
    print(f"SUMMARY: Found {len(all_signals)}/{len(CORRECTED_SIGNALS)} corrected signals")
    print("=" * 120)
    
    # Save results
    import json
    
    serializable_signals = []
    for sig in all_signals:
        sig_copy = sig.copy()
        sig_copy["target_time_utc"] = format_utc_time(sig["target_time_utc"])
        sig_copy["target_time_msk"] = format_msk_time(sig["target_time_msk"])
        serializable_signals.append(sig_copy)
    
    output = {
        "found_signals": serializable_signals,
        "not_found": not_found,
        "total_found": len(all_signals),
        "total_not_found": len(not_found),
    }
    
    with open("corrected_signals_analysis.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to corrected_signals_analysis.json")
    
    # Print table
    print("\n" + "=" * 120)
    print("CORRECTED SIGNALS TABLE")
    print("=" * 120)
    print(f"{'Symbol':<15} {'MSK':<20} {'UTC':<20} {'Note':<35} {'Body':<10} {'LW':<10} {'UW':<10} {'LW/Body':<10} {'LW/Range':<10} {'VolRatio':<10}")
    print("-" * 120)
    
    for sig in all_signals:
        print(f"{sig['symbol']:<15} {format_msk_time(sig['target_time_msk']):<20} {format_utc_time(sig['target_time_utc']):<20} "
              f"{sig['note']:<35} {sig['body']:<10.6f} {sig['lower_wick']:<10.6f} {sig['upper_wick']:<10.6f} "
              f"{sig['lower_wick_body_ratio']:<10.2f} {sig['lower_wick_range_ratio']:<10.2f} {sig['volume_ratio']:<10.2f}")


if __name__ == "__main__":
    asyncio.run(main())
