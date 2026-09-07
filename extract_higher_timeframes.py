#!/usr/bin/env python3
"""
Extract higher timeframe context (1H, 4H, 1D).

Research: Extract trend and range context from higher timeframes.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def calculate_ema(values, period):
    """Calculate EMA."""
    if len(values) < period:
        return None
    ema = values[0]
    multiplier = 2 / (period + 1)
    for value in values[1:]:
        ema = (value * multiplier) + (ema * (1 - multiplier))
    return ema


def calculate_slope(values, period=5):
    """Calculate slope (rate of change)."""
    if len(values) < period:
        return None
    return (values[-1] - values[-period]) / values[-period] * 100


def analyze_timeframe(closes, highs, lows, timeframe_name):
    """Analyze a specific timeframe."""
    if len(closes) < 50:
        return {"error": f"Not enough data for {timeframe_name}"}
    
    current_price = closes[-1]
    
    # Previous movement
    pm10 = (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) >= 11 else None
    pm20 = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else None
    
    # EMAs
    ema_21 = calculate_ema(closes, 21)
    ema_50 = calculate_ema(closes, 50)
    
    result = {
        "timeframe": timeframe_name,
        "pm10": pm10,
        "pm20": pm20,
        "direction": "UP" if pm10 and pm10 > 0 else "DOWN" if pm10 and pm10 < 0 else "SIDEWAYS"
    }
    
    if ema_21:
        result["price_above_ema_21"] = current_price > ema_21
        result["ema_21_slope"] = calculate_slope(closes, 10)
    
    if ema_50:
        result["price_above_ema_50"] = current_price > ema_50
        result["ema_50_slope"] = calculate_slope(closes, 20)
    
    # Range position
    if len(closes) >= 20:
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        result["range_position_20"] = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
    
    return result


async def analyze_higher_timeframes(fetcher, signal):
    """Analyze higher timeframes for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    
    ht_context = {
        "symbol": symbol,
        "signal_time": signal_time,
        "timeframes": {}
    }
    
    # Try 1H
    try:
        end_time = int(signal_time.timestamp() * 1000)
        start_time = int((signal_time - timedelta(days=7)).timestamp() * 1000)
        
        klines_1h = await fetcher.get_klines(
            symbol=symbol,
            interval="1h",
            limit=200,
            start_time=start_time,
            end_time=end_time
        )
        
        if klines_1h and len(klines_1h) >= 50:
            closes = [float(k['close']) for k in klines_1h]
            highs = [float(k['high']) for k in klines_1h]
            lows = [float(k['low']) for k in klines_1h]
            ht_context["timeframes"]["1H"] = analyze_timeframe(closes, highs, lows, "1H")
        else:
            ht_context["timeframes"]["1H"] = {"error": "Not enough data"}
    except Exception as e:
        ht_context["timeframes"]["1H"] = {"error": str(e)}
    
    # Try 4H
    try:
        end_time = int(signal_time.timestamp() * 1000)
        start_time = int((signal_time - timedelta(days=30)).timestamp() * 1000)
        
        klines_4h = await fetcher.get_klines(
            symbol=symbol,
            interval="4h",
            limit=200,
            start_time=start_time,
            end_time=end_time
        )
        
        if klines_4h and len(klines_4h) >= 50:
            closes = [float(k['close']) for k in klines_4h]
            highs = [float(k['high']) for k in klines_4h]
            lows = [float(k['low']) for k in klines_4h]
            ht_context["timeframes"]["4H"] = analyze_timeframe(closes, highs, lows, "4H")
        else:
            ht_context["timeframes"]["4H"] = {"error": "Not enough data"}
    except Exception as e:
        ht_context["timeframes"]["4H"] = {"error": str(e)}
    
    # Try 1D
    try:
        end_time = int(signal_time.timestamp() * 1000)
        start_time = int((signal_time - timedelta(days=180)).timestamp() * 1000)
        
        klines_1d = await fetcher.get_klines(
            symbol=symbol,
            interval="1d",
            limit=200,
            start_time=start_time,
            end_time=end_time
        )
        
        if klines_1d and len(klines_1d) >= 50:
            closes = [float(k['close']) for k in klines_1d]
            highs = [float(k['high']) for k in klines_1d]
            lows = [float(k['low']) for k in klines_1d]
            ht_context["timeframes"]["1D"] = analyze_timeframe(closes, highs, lows, "1D")
        else:
            ht_context["timeframes"]["1D"] = {"error": "Not enough data"}
    except Exception as e:
        ht_context["timeframes"]["1D"] = {"error": str(e)}
    
    return ht_context


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("HIGHER TIMEFRAME CONTEXT EXTRACTION")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load comprehensive data
    with open("large_comprehensive.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze higher timeframes
    fetcher = BingXFetcher()
    print("\nAnalyzing higher timeframes (1H, 4H, 1D)...")
    
    success_1h = 0
    success_4h = 0
    success_1d = 0
    
    for i, candidate in enumerate(candidates, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        ht = await analyze_higher_timeframes(fetcher, candidate)
        candidate["higher_timeframes"] = ht["timeframes"]
        
        if "1H" in ht["timeframes"] and "error" not in ht["timeframes"]["1H"]:
            success_1h += 1
        if "4H" in ht["timeframes"] and "error" not in ht["timeframes"]["4H"]:
            success_4h += 1
        if "1D" in ht["timeframes"] and "error" not in ht["timeframes"]["1D"]:
            success_1d += 1
    
    print(f"\nHigher timeframe analysis complete:")
    print(f"  1H: {success_1h}/{len(candidates)}")
    print(f"  4H: {success_4h}/{len(candidates)}")
    print(f"  1D: {success_1d}/{len(candidates)}")
    
    # Save results
    results = {
        "candidates": candidates,
        "summary": data["summary"]
    }
    
    with open("large_with_ht.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to large_with_ht.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
