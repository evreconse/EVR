#!/usr/bin/env python3
"""
Analyze 42 manual LW-001 signals to find common patterns.

This is a RESEARCH task - DO NOT modify existing LW-001 strategy,
production, backtest, PASS_CHECK, Telegram, or any existing formulas.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from collections import defaultdict
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


# 42 manual signals with MSK and UTC times
# BingX requires symbols to end with -USDT or -USDC
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


def analyze_candle_geometry(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """
    Analyze candle geometry without assuming LW-001 conditions.
    
    Returns:
        Dict with all geometry metrics.
    """
    is_red = close_price < open_price
    is_green = close_price > open_price
    
    if is_red:
        body = open_price - close_price
        lower_wick = close_price - low_price
        upper_wick = high_price - open_price
    else:
        body = close_price - open_price
        lower_wick = open_price - low_price
        upper_wick = high_price - close_price
    
    total_range = high_price - low_price
    
    # Calculate ratios
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    upper_wick_body_ratio = upper_wick / body if body > 0 else 0
    body_range_ratio = body / total_range if total_range > 0 else 0
    lower_wick_range_ratio = lower_wick / total_range if total_range > 0 else 0
    upper_wick_range_ratio = upper_wick / total_range if total_range > 0 else 0
    
    return {
        "is_red": is_red,
        "is_green": is_green,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "total_range": total_range,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "upper_wick_body_ratio": upper_wick_body_ratio,
        "body_range_ratio": body_range_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "upper_wick_range_ratio": upper_wick_range_ratio,
    }


def analyze_volume_metrics(current_volume: float, klines: list, candle_index: int) -> dict:
    """
    Analyze volume metrics for a candle.
    
    Returns:
        Dict with volume metrics.
    """
    # Previous candle volume
    if candle_index > 0:
        previous_volume = float(klines[candle_index - 1]['volume'])
        volume_ratio_previous = current_volume / previous_volume if previous_volume > 0 else 0
    else:
        previous_volume = 0
        volume_ratio_previous = 0
    
    # Previous 15 candles
    start_idx_15 = max(0, candle_index - 15)
    previous_15_volumes = [float(klines[i]['volume']) for i in range(start_idx_15, candle_index)]
    max_previous_15 = max(previous_15_volumes) if previous_15_volumes else 0
    volume_ratio_max_15 = current_volume / max_previous_15 if max_previous_15 > 0 else 0
    
    # Previous 48 candles
    start_idx_48 = max(0, candle_index - 48)
    previous_48_volumes = [float(klines[i]['volume']) for i in range(start_idx_48, candle_index)]
    max_previous_48 = max(previous_48_volumes) if previous_48_volumes else 0
    volume_ratio_max_48 = current_volume / max_previous_48 if max_previous_48 > 0 else 0
    
    return {
        "current_volume": current_volume,
        "previous_candle_volume": previous_volume,
        "volume_ratio_previous": volume_ratio_previous,
        "max_previous_15": max_previous_15,
        "volume_ratio_max_15": volume_ratio_max_15,
        "max_previous_48": max_previous_48,
        "volume_ratio_max_48": volume_ratio_max_48,
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
    fetcher: BingXFetcher,
) -> dict:
    """
    Fetch and analyze a single manual signal.
    
    Returns:
        Dict with all analysis data or None if candle not found.
    """
    # Create target datetime
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
            "target_time_utc": target_time_utc,
            "target_time_msk": target_time_msk,
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
            "target_time_utc": target_time_utc,
            "target_time_msk": target_time_msk,
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
    
    # Analyze geometry
    geometry = analyze_candle_geometry(open_price, high_price, low_price, close_price)
    
    # Analyze volume
    volume_metrics = analyze_volume_metrics(volume, klines, candle_index)
    
    return {
        "symbol": symbol,
        "target_time_utc": target_time_utc,
        "target_time_msk": target_time_msk,
        "timestamp_ms": timestamp_ms,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "found": True,
        "geometry": geometry,
        "volume_metrics": volume_metrics,
    }


async def main():
    """Analyze all 42 manual signals."""
    print("=" * 100)
    print("ANALYZING 42 MANUAL LW-001 SIGNALS - RESEARCH TASK")
    print("=" * 100)
    print()
    
    fetcher = BingXFetcher()
    
    # Fetch all signals
    all_signals = []
    not_found = []
    
    for i, (symbol, day, month, year, hour_msk, minute_msk, hour_utc, minute_utc) in enumerate(MANUAL_SIGNALS, 1):
        print(f"[{i}/42] Fetching {symbol} at {day:02d}/{month:02d}/{year} {hour_utc:02d}:{minute_utc:02d} UTC...")
        
        signal_data = await fetch_and_analyze_signal(
            symbol, day, month, year, hour_utc, minute_utc, hour_msk, minute_msk, fetcher
        )
        
        if signal_data["found"]:
            all_signals.append(signal_data)
            print(f"  [OK] Found: O={signal_data['open']:.6f} H={signal_data['high']:.6f} L={signal_data['low']:.6f} C={signal_data['close']:.6f}")
        else:
            not_found.append(signal_data)
            print(f"  [X] NOT FOUND: {signal_data.get('error', 'Unknown error')}")
    
    print()
    print("=" * 100)
    print(f"SUMMARY: Found {len(all_signals)}/{len(MANUAL_SIGNALS)} signals")
    print("=" * 100)
    
    if not_found:
        print("\nNOT FOUND SIGNALS:")
        for nf in not_found:
            print(f"  - {nf['symbol']} at {format_utc_time(nf['target_time_utc'])}: {nf.get('error', 'Unknown')}")
    
    # Save results to file for further analysis
    import json
    
    # Convert datetime objects to strings for JSON serialization
    serializable_signals = []
    for sig in all_signals:
        sig_copy = sig.copy()
        sig_copy["target_time_utc"] = format_utc_time(sig["target_time_utc"])
        sig_copy["target_time_msk"] = format_msk_time(sig["target_time_msk"])
        serializable_signals.append(sig_copy)
    
    serializable_not_found = []
    for nf in not_found:
        nf_copy = nf.copy()
        nf_copy["target_time_utc"] = format_utc_time(nf["target_time_utc"])
        nf_copy["target_time_msk"] = format_msk_time(nf["target_time_msk"])
        serializable_not_found.append(nf_copy)
    
    output = {
        "found_signals": serializable_signals,
        "not_found_signals": serializable_not_found,
        "total_found": len(all_signals),
        "total_not_found": len(not_found),
    }
    
    with open("manual_signals_analysis.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to manual_signals_analysis.json")
    
    # Print table
    print("\n" + "=" * 100)
    print("PART 1 - TABLE OF ALL FOUND SIGNALS")
    print("=" * 100)
    print(f"{'Symbol':<15} {'MSK':<20} {'UTC':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Volume':<15}")
    print("-" * 100)
    
    for sig in all_signals:
        print(f"{sig['symbol']:<15} {format_msk_time(sig['target_time_msk']):<20} {format_utc_time(sig['target_time_utc']):<20} "
              f"{sig['open']:<10.6f} {sig['high']:<10.6f} {sig['low']:<10.6f} {sig['close']:<10.6f} {sig['volume']:>15,.0f}")
    
    # Print geometry analysis
    print("\n" + "=" * 100)
    print("PART 2 - GEOMETRY ANALYSIS")
    print("=" * 100)
    print(f"{'Symbol':<15} {'Color':<8} {'Body':<12} {'Lower Wick':<12} {'Upper Wick':<12} {'LW/Body':<10} {'UW/Body':<10}")
    print("-" * 100)
    
    for sig in all_signals:
        geo = sig["geometry"]
        color = "RED" if geo["is_red"] else "GREEN"
        print(f"{sig['symbol']:<15} {color:<8} {geo['body']:<12.6f} {geo['lower_wick']:<12.6f} {geo['upper_wick']:<12.6f} "
              f"{geo['lower_wick_body_ratio']:<10.2f} {geo['upper_wick_body_ratio']:<10.2f}")
    
    # Print volume analysis
    print("\n" + "=" * 100)
    print("PART 3 - VOLUME ANALYSIS")
    print("=" * 100)
    print(f"{'Symbol':<15} {'Current Vol':<15} {'Prev Vol':<15} {'Cur/Prev':<10} {'Cur/Max15':<10} {'Cur/Max48':<10}")
    print("-" * 100)
    
    for sig in all_signals:
        vol = sig["volume_metrics"]
        print(f"{sig['symbol']:<15} {vol['current_volume']:>15,.0f} {vol['previous_candle_volume']:>15,.0f} "
              f"{vol['volume_ratio_previous']:<10.2f} {vol['volume_ratio_max_15']:<10.2f} {vol['volume_ratio_max_48']:<10.2f}")
    
    # Pattern analysis
    print("\n" + "=" * 100)
    print("PART 4 - PATTERN ANALYSIS")
    print("=" * 100)
    
    if len(all_signals) == 0:
        print("\nNo signals found - cannot perform pattern analysis.")
        return
    
    red_count = sum(1 for sig in all_signals if sig["geometry"]["is_red"])
    green_count = sum(1 for sig in all_signals if sig["geometry"]["is_green"])
    
    print(f"\nCOLOR DISTRIBUTION:")
    print(f"  Red candles: {red_count}/{len(all_signals)} ({red_count/len(all_signals)*100:.1f}%)")
    print(f"  Green candles: {green_count}/{len(all_signals)} ({green_count/len(all_signals)*100:.1f}%)")
    
    # Lower Wick / Body ratio distribution
    lw_body_ratios = [sig["geometry"]["lower_wick_body_ratio"] for sig in all_signals]
    lw_body_avg = sum(lw_body_ratios) / len(lw_body_ratios)
    lw_body_min = min(lw_body_ratios)
    lw_body_max = max(lw_body_ratios)
    
    print(f"\nLOWER WICK / BODY RATIO:")
    print(f"  Average: {lw_body_avg:.2f}x")
    print(f"  Min: {lw_body_min:.2f}x")
    print(f"  Max: {lw_body_max:.2f}x")
    
    # Count how many have LW/Body >= 2.0 (current LW-001 condition)
    lw_body_ge_2 = sum(1 for r in lw_body_ratios if r >= 2.0)
    print(f"  >= 2.0x: {lw_body_ge_2}/{len(all_signals)} ({lw_body_ge_2/len(all_signals)*100:.1f}%)")
    
    # Upper Wick / Body ratio distribution
    uw_body_ratios = [sig["geometry"]["upper_wick_body_ratio"] for sig in all_signals]
    uw_body_avg = sum(uw_body_ratios) / len(uw_body_ratios)
    uw_body_min = min(uw_body_ratios)
    uw_body_max = max(uw_body_ratios)
    
    print(f"\nUPPER WICK / BODY RATIO:")
    print(f"  Average: {uw_body_avg:.2f}x")
    print(f"  Min: {uw_body_min:.2f}x")
    print(f"  Max: {uw_body_max:.2f}x")
    
    # Volume ratio distribution
    vol_prev_ratios = [sig["volume_metrics"]["volume_ratio_previous"] for sig in all_signals if sig["volume_metrics"]["previous_candle_volume"] > 0]
    if vol_prev_ratios:
        vol_prev_avg = sum(vol_prev_ratios) / len(vol_prev_ratios)
        vol_prev_min = min(vol_prev_ratios)
        vol_prev_max = max(vol_prev_ratios)
        
        print(f"\nVOLUME RATIO (Current / Previous):")
        print(f"  Average: {vol_prev_avg:.2f}x")
        print(f"  Min: {vol_prev_min:.2f}x")
        print(f"  Max: {vol_prev_max:.2f}x")
        
        vol_prev_ge_1_5 = sum(1 for r in vol_prev_ratios if r >= 1.5)
        print(f"  >= 1.5x: {vol_prev_ge_1_5}/{len(vol_prev_ratios)} ({vol_prev_ge_1_5/len(vol_prev_ratios)*100:.1f}%)")
    
    vol_15_ratios = [sig["volume_metrics"]["volume_ratio_max_15"] for sig in all_signals if sig["volume_metrics"]["max_previous_15"] > 0]
    if vol_15_ratios:
        vol_15_avg = sum(vol_15_ratios) / len(vol_15_ratios)
        print(f"\nVOLUME RATIO (Current / Max Previous 15):")
        print(f"  Average: {vol_15_avg:.2f}x")
    
    vol_48_ratios = [sig["volume_metrics"]["volume_ratio_max_48"] for sig in all_signals if sig["volume_metrics"]["max_previous_48"] > 0]
    if vol_48_ratios:
        vol_48_avg = sum(vol_48_ratios) / len(vol_48_ratios)
        print(f"\nVOLUME RATIO (Current / Max Previous 48):")
        print(f"  Average: {vol_48_avg:.2f}x")
    
    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
