#!/usr/bin/env python3
"""
Re-analyze 32 manual LW-001 signals with comprehensive metrics.

Goal: Find minimum candle size filter that eliminates microscopic candles
while preserving large candles with relatively small lower wicks.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import calculate_all_metrics


# 32 manual signals with MSK times
MANUAL_SIGNALS = [
    # Format: (symbol, day, month, year, hour_msk, minute_msk)
    ("NEAR-USDT", 5, 6, 2026, 19, 0),
    ("ONDO-USDT", 4, 6, 2026, 5, 0),
    ("TAO-USDT", 4, 6, 2026, 5, 0),
    ("ENA-USDT", 4, 6, 2026, 5, 0),
    ("ENA-USDT", 5, 6, 2026, 9, 15),
    ("WLFI-USDT", 4, 6, 2026, 5, 0),
    ("DOT-USDT", 4, 6, 2026, 5, 0),
    ("UNI-USDT", 4, 6, 2026, 5, 0),
    ("ATOM-USDT", 4, 6, 2026, 5, 0),
    ("INJ-USDT", 4, 6, 2026, 5, 0),
    ("XPL-USDT", 4, 6, 2026, 5, 0),
    ("FARTCOIN-USDT", 4, 6, 2026, 5, 0),
    ("FF-USDT", 5, 6, 2026, 18, 30),
    ("ICP-USDT", 4, 6, 2026, 5, 0),
    ("SIREN-USDT", 2, 6, 2026, 16, 30),
    ("SIREN-USDT", 4, 6, 2026, 5, 0),
    ("SIREN-USDT", 7, 6, 2026, 21, 30),
    ("ARB-USDT", 4, 6, 2026, 5, 0),
    ("APT-USDT", 4, 6, 2026, 5, 0),
    ("ZRO-USDT", 4, 6, 2026, 5, 0),
    ("KITE-USDT", 4, 6, 2026, 5, 0),
    ("MON-USDT", 4, 6, 2026, 5, 0),
    ("CRV-USDT", 4, 6, 2026, 5, 0),
    ("WIF-USDT", 4, 6, 2026, 5, 0),
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


async def fetch_signal_data(
    symbol: str,
    day: int,
    month: int,
    year: int,
    hour_msk: int,
    minute_msk: int,
    fetcher: BingXFetcher,
) -> dict:
    """Fetch candle data for a signal."""
    # Create MSK time
    target_time_msk = datetime(year, month, day, hour_msk, minute_msk, tzinfo=UTC)
    
    # Convert MSK to UTC (MSK = UTC+3)
    target_time_utc = target_time_msk - timedelta(hours=3)
    
    # Calculate expected timestamp (start of M15 interval)
    expected_timestamp_ms = int(target_time_utc.timestamp() * 1000)
    
    # Fetch data around the target time (±2 hours to get previous candles)
    start_time = int((target_time_utc - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time_utc + timedelta(hours=1)).timestamp() * 1000)
    
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
    
    # Get previous candle volume
    previous_volume = 0
    if candle_index > 0:
        previous_volume = float(klines[candle_index - 1]['volume'])
    
    # Get average volume of previous 5 candles (if available)
    avg_previous_volume = 0
    if candle_index >= 5:
        volumes = [float(klines[candle_index - i]['volume']) for i in range(1, 6)]
        avg_previous_volume = statistics.mean(volumes)
    
    # Calculate all metrics using canonical formulas
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, avg_previous_volume)
    
    # Additional metrics for this specific analysis
    body = open_price - close_price
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    candle_range = high_price - low_price
    
    # Percentages
    body_percent = metrics.body_pct
    range_percent = metrics.range_pct
    lower_wick_percent = lower_wick / open_price * 100
    upper_wick_percent = upper_wick / open_price * 100
    
    # Ratios
    lower_wick_body_ratio = metrics.lower_wick_body_ratio
    lower_wick_range_ratio = metrics.lower_wick_range_pct / 100
    upper_wick_body_ratio = upper_wick / body if body > 0 else 0
    
    # Price movement percentages
    open_to_low_percent = metrics.open_to_low_pct
    open_to_close_percent = (close_price - open_price) / open_price * 100
    
    # Volume ratios
    volume_ratio_prev = volume / previous_volume if previous_volume > 0 else 0
    volume_ratio_avg = metrics.volume_ratio
    
    # Candle color
    color = get_candle_color(open_price, close_price)
    
    return {
        "symbol": symbol,
        "original_msk": target_time_msk,
        "requested_utc": target_time_utc,
        "expected_timestamp_ms": expected_timestamp_ms,
        "actual_timestamp_ms": timestamp_ms,
        "timestamp_match": timestamp_ms == expected_timestamp_ms,
        "found": True,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "color": color,
        "body": body,
        "body_percent": body_percent,
        "candle_range": candle_range,
        "range_percent": range_percent,
        "lower_wick": lower_wick,
        "lower_wick_percent": lower_wick_percent,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "upper_wick": upper_wick,
        "upper_wick_percent": upper_wick_percent,
        "upper_wick_body_ratio": upper_wick_body_ratio,
        "previous_volume": previous_volume,
        "volume_ratio_prev": volume_ratio_prev,
        "avg_previous_volume": avg_previous_volume,
        "volume_ratio_avg": volume_ratio_avg,
        "open_to_low_percent": open_to_low_percent,
        "open_to_close_percent": open_to_close_percent,
    }


def compare_filter_variants(signals):
    """Compare filter variants A-I."""
    print()
    print("=" * 140)
    print("FILTER VARIANT COMPARISON")
    print("=" * 140)
    
    # Filter only found signals
    found_signals = [s for s in signals if s["found"] and s["color"] == "RED"]
    total = len(found_signals)
    
    # Filter A: Red + LW/Body >= 2.0
    filter_a = [s for s in found_signals if s["lower_wick_body_ratio"] >= 2.0]
    
    # Filter B: Red + LW/Body >= 1.0
    filter_b = [s for s in found_signals if s["lower_wick_body_ratio"] >= 1.0]
    
    # Filter C: Red + LW/Range >= 30%
    filter_c = [s for s in found_signals if s["lower_wick_range_ratio"] >= 0.30]
    
    # Filter D: Red + LW/Range >= 30% + Volume >= 1.5x Previous
    filter_d = [s for s in found_signals if s["lower_wick_range_ratio"] >= 0.30 and s["volume_ratio_prev"] >= 1.5]
    
    # Filter E: Red + LW/Range >= 30% + Volume >= 0.5x Previous
    filter_e = [s for s in found_signals if s["lower_wick_range_ratio"] >= 0.30 and s["volume_ratio_prev"] >= 0.5]
    
    # Filter F: Red + Body % >= 0.20% + LW/Body >= 1.0
    filter_f = [s for s in found_signals if s["body_percent"] >= 0.20 and s["lower_wick_body_ratio"] >= 1.0]
    
    # Filter G: Red + Range % >= 0.5% + LW/Range >= 30%
    filter_g = [s for s in found_signals if s["range_percent"] >= 0.5 and s["lower_wick_range_ratio"] >= 0.30]
    
    # Filter H: Red + Lower Wick % >= 0.5% + Volume >= 0.5x Previous
    filter_h = [s for s in found_signals if s["lower_wick_percent"] >= 0.5 and s["volume_ratio_prev"] >= 0.5]
    
    # Filter I: Red + Body % >= 0.20% + LW/Body >= 1.0 + Volume >= 0.5x Previous
    filter_i = [s for s in found_signals if s["body_percent"] >= 0.20 and s["lower_wick_body_ratio"] >= 1.0 and s["volume_ratio_prev"] >= 0.5]
    
    print()
    print(f"{'Variant':<10} {'Description':<60} {'Coverage':<15} {'Lost':<10}")
    print("-" * 100)
    
    print(f"{'A':<10} {'Red + LW/Body >= 2.0':<60} {len(filter_a)}/{total:<10} ({len(filter_a)/total*100:.1f}%) {total-len(filter_a):<10}")
    print(f"{'B':<10} {'Red + LW/Body >= 1.0':<60} {len(filter_b)}/{total:<10} ({len(filter_b)/total*100:.1f}%) {total-len(filter_b):<10}")
    print(f"{'C':<10} {'Red + LW/Range >= 30%':<60} {len(filter_c)}/{total:<10} ({len(filter_c)/total*100:.1f}%) {total-len(filter_c):<10}")
    print(f"{'D':<10} {'Red + LW/Range >= 30% + Volume >= 1.5x':<60} {len(filter_d)}/{total:<10} ({len(filter_d)/total*100:.1f}%) {total-len(filter_d):<10}")
    print(f"{'E':<10} {'Red + LW/Range >= 30% + Volume >= 0.5x':<60} {len(filter_e)}/{total:<10} ({len(filter_e)/total*100:.1f}%) {total-len(filter_e):<10}")
    print(f"{'F':<10} {'Red + Body % >= 0.20% + LW/Body >= 1.0':<60} {len(filter_f)}/{total:<10} ({len(filter_f)/total*100:.1f}%) {total-len(filter_f):<10}")
    print(f"{'G':<10} {'Red + Range % >= 0.5% + LW/Range >= 30%':<60} {len(filter_g)}/{total:<10} ({len(filter_g)/total*100:.1f}%) {total-len(filter_g):<10}")
    print(f"{'H':<10} {'Red + LW % >= 0.5% + Volume >= 0.5x':<60} {len(filter_h)}/{total:<10} ({len(filter_h)/total*100:.1f}%) {total-len(filter_h):<10}")
    print(f"{'I':<10} {'Red + Body % >= 0.20% + LW/Body >= 1.0 + Vol >= 0.5x':<60} {len(filter_i)}/{total:<10} ({len(filter_i)/total*100:.1f}%) {total-len(filter_i):<10}")
    
    # Show lost signals for each variant
    print()
    print("LOST SIGNALS BY VARIANT:")
    print()
    
    for variant_name, filtered, description in [
        ("A", filter_a, "Red + LW/Body >= 2.0"),
        ("B", filter_b, "Red + LW/Body >= 1.0"),
        ("C", filter_c, "Red + LW/Range >= 30%"),
        ("D", filter_d, "Red + LW/Range >= 30% + Volume >= 1.5x"),
        ("E", filter_e, "Red + LW/Range >= 30% + Volume >= 0.5x"),
        ("F", filter_f, "Red + Body % >= 0.20% + LW/Body >= 1.0"),
        ("G", filter_g, "Red + Range % >= 0.5% + LW/Range >= 30%"),
        ("H", filter_h, "Red + LW % >= 0.5% + Volume >= 0.5x"),
        ("I", filter_i, "Red + Body % >= 0.20% + LW/Body >= 1.0 + Vol >= 0.5x"),
    ]:
        lost = [s for s in found_signals if s not in filtered]
        if lost:
            print(f"Variant {variant_name} ({description}):")
            for s in lost:
                print(f"  - {s['symbol']} ({format_msk_time(s['original_msk'])}): "
                      f"Body%={s['body_percent']:.4f}%, LW/Body={s['lower_wick_body_ratio']:.2f}x, "
                      f"LW/Range={s['lower_wick_range_ratio']*100:.1f}%, VolRatio={s['volume_ratio_prev']:.2f}x")
            print()
    
    return {
        "A": filter_a,
        "B": filter_b,
        "C": filter_c,
        "D": filter_d,
        "E": filter_e,
        "F": filter_f,
        "G": filter_g,
        "H": filter_h,
        "I": filter_i,
    }


def analyze_minimum_candle_size(signals):
    """Analyze minimum candle size thresholds."""
    print()
    print("=" * 140)
    print("MINIMUM CANDLE SIZE ANALYSIS")
    print("=" * 140)
    
    red_signals = [s for s in signals if s.get("found") and s.get("color") == "RED"]
    
    # Body percent distribution
    body_percents = [s["body_percent"] for s in red_signals]
    range_percents = [s["range_percent"] for s in red_signals]
    lw_percents = [s["lower_wick_percent"] for s in red_signals]
    
    print()
    print("Body Percent Distribution:")
    print(f"  Min: {min(body_percents):.4f}%")
    print(f"  Max: {max(body_percents):.4f}%")
    print(f"  Mean: {statistics.mean(body_percents):.4f}%")
    print(f"  Median: {statistics.median(body_percents):.4f}%")
    
    print()
    print("Range Percent Distribution:")
    print(f"  Min: {min(range_percents):.4f}%")
    print(f"  Max: {max(range_percents):.4f}%")
    print(f"  Mean: {statistics.mean(range_percents):.4f}%")
    print(f"  Median: {statistics.median(range_percents):.4f}%")
    
    print()
    print("Lower Wick Percent Distribution:")
    print(f"  Min: {min(lw_percents):.4f}%")
    print(f"  Max: {max(lw_percents):.4f}%")
    print(f"  Mean: {statistics.mean(lw_percents):.4f}%")
    print(f"  Median: {statistics.median(lw_percents):.4f}%")
    
    # Test different thresholds
    print()
    print("Coverage at different Body % thresholds:")
    for t in [0.10, 0.15, 0.20, 0.25, 0.30, 0.50, 0.75, 1.0]:
        count = sum(1 for bp in body_percents if bp >= t)
        print(f"  body_percent >= {t:.2f}%: {count}/{len(red_signals)} ({count/len(red_signals)*100:.1f}%)")
    
    print()
    print("Coverage at different Range % thresholds:")
    for t in [0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]:
        count = sum(1 for rp in range_percents if rp >= t)
        print(f"  range_percent >= {t:.1f}%: {count}/{len(red_signals)} ({count/len(red_signals)*100:.1f}%)")
    
    print()
    print("Coverage at different Lower Wick % thresholds:")
    for t in [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]:
        count = sum(1 for lwp in lw_percents if lwp >= t)
        print(f"  lower_wick_percent >= {t:.1f}%: {count}/{len(red_signals)} ({count/len(red_signals)*100:.1f}%)")


def print_detailed_table(signals):
    """Print detailed metrics table."""
    print()
    print("=" * 140)
    print("DETAILED METRICS TABLE")
    print("=" * 140)
    print()
    print(f"{'Symbol':<15} {'MSK':<20} {'UTC':<20} {'Color':<8} {'Body%':<10} {'Range%':<10} {'LW%':<10} {'LW/Body':<10} {'LW/Range':<10} {'VolRatio':<10}")
    print("-" * 140)
    
    for s in signals:
        if s["found"]:
            print(f"{s['symbol']:<15} {format_msk_time(s['original_msk']):<20} {format_utc_time(s['requested_utc']):<20} "
                  f"{s['color']:<8} {s['body_percent']:<10.4f} {s['range_percent']:<10.4f} {s['lower_wick_percent']:<10.4f} "
                  f"{s['lower_wick_body_ratio']:<10.2f} {s['lower_wick_range_ratio']*100:<10.1f} {s['volume_ratio_prev']:<10.2f}")
        else:
            print(f"{s['symbol']:<15} {format_msk_time(s['original_msk']):<20} {format_utc_time(s['requested_utc']):<20} "
                  f"{'ERROR':<8} {'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<10}")


async def main():
    """Main analysis."""
    print("=" * 140)
    print("RE-ANALYSIS OF 32 MANUAL LW-001 SIGNALS")
    print("=" * 140)
    print()
    
    fetcher = BingXFetcher()
    
    all_results = []
    
    for i, (symbol, day, month, year, hour_msk, minute_msk) in enumerate(MANUAL_SIGNALS, 1):
        print(f"[{i}/32] Fetching {symbol} at {day:02d}/{month:02d}/{year} {hour_msk:02d}:{minute_msk:02d} MSK...")
        
        result = await fetch_signal_data(
            symbol, day, month, year, hour_msk, minute_msk, fetcher
        )
        
        all_results.append(result)
        
        if result["found"]:
            print(f"  [{result['color']}] Body%={result['body_percent']:.4f}%, LW/Body={result['lower_wick_body_ratio']:.2f}x")
        else:
            print(f"  [ERROR] {result.get('error', 'Unknown')}")
    
    # Print detailed table
    print_detailed_table(all_results)
    
    # Compare filter variants
    filter_results = compare_filter_variants(all_results)
    
    # Analyze minimum candle size
    analyze_minimum_candle_size(all_results)
    
    # Save results
    serializable_results = []
    for r in all_results:
        r_copy = r.copy()
        r_copy["original_msk"] = format_msk_time(r["original_msk"])
        r_copy["requested_utc"] = format_utc_time(r["requested_utc"])
        serializable_results.append(r_copy)
    
    output = {
        "total_signals": len(all_results),
        "found_signals": sum(1 for r in all_results if r["found"]),
        "red_signals": sum(1 for r in all_results if r["found"] and r["color"] == "RED"),
        "results": serializable_results,
    }
    
    with open("reanalysis_manual_signals.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Results saved to reanalysis_manual_signals.json")


if __name__ == "__main__":
    asyncio.run(main())
