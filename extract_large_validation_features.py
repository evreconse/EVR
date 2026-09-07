#!/usr/bin/env python3
"""
Extract deep features for large validation sample.

Research: Extract all deep features for 122 candidates.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
from statistics import mean, median
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


def calculate_sma(values, period):
    """Calculate SMA."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calculate_atr(highs, lows, closes, period=14):
    """Calculate ATR."""
    if len(highs) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)
    
    return sum(true_ranges[-period:]) / period


def calculate_slope(values, period=5):
    """Calculate slope (rate of change)."""
    if len(values) < period:
        return None
    return (values[-1] - values[-period]) / values[-period] * 100


def analyze_short_term_trend(closes):
    """Analyze short-term trend direction."""
    trends = {}
    
    for period in [1, 3, 5, 10, 20]:
        if len(closes) >= period + 1:
            change = (closes[-1] - closes[-(period + 1)]) / closes[-(period + 1)] * 100
            trends[f"{period}_candles"] = change
    
    # Trend direction
    if len(closes) >= 6:
        recent_change = (closes[-1] - closes[-6]) / closes[-6] * 100
        if recent_change > 0.5:
            trends["short_term_direction"] = "UP"
        elif recent_change < -0.5:
            trends["short_term_direction"] = "DOWN"
        else:
            trends["short_term_direction"] = "SIDEWAYS"
    
    return trends


def analyze_ema_sma(closes, highs, lows):
    """Analyze EMA/SMA position and slope."""
    indicators = {}
    
    if len(closes) < 20:
        return indicators
    
    current_price = closes[-1]
    
    # EMAs
    ema_9 = calculate_ema(closes, 9)
    ema_21 = calculate_ema(closes, 21)
    
    # SMAs
    sma_9 = calculate_sma(closes, 9)
    sma_21 = calculate_sma(closes, 21)
    
    if ema_9:
        indicators["price_above_ema_9"] = current_price > ema_9
        indicators["price_ema_9_distance"] = (current_price - ema_9) / ema_9 * 100
        indicators["ema_9_slope"] = calculate_slope(closes, 5)
    
    if ema_21:
        indicators["price_above_ema_21"] = current_price > ema_21
        indicators["price_ema_21_distance"] = (current_price - ema_21) / ema_21 * 100
        indicators["ema_21_slope"] = calculate_slope(closes, 10)
    
    if sma_9:
        indicators["price_above_sma_9"] = current_price > sma_9
        indicators["price_sma_9_distance"] = (current_price - sma_9) / sma_9 * 100
    
    if sma_21:
        indicators["price_above_sma_21"] = current_price > sma_21
        indicators["price_sma_21_distance"] = (current_price - sma_21) / sma_21 * 100
    
    # EMA alignment
    if ema_9 and ema_21:
        indicators["ema_alignment"] = (ema_9 > ema_21)
    
    return indicators


def analyze_distance_to_extremes(closes, highs, lows):
    """Analyze distance to recent high/low."""
    extremes = {}
    
    if len(closes) < 20:
        return extremes
    
    current_price = closes[-1]
    
    # Recent high/low
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    
    extremes["distance_to_high_20"] = (recent_high - current_price) / recent_high * 100
    extremes["distance_to_low_20"] = (current_price - recent_low) / recent_low * 100
    
    # Position within range
    extremes["range_position_20"] = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
    
    # 50 candle lookback
    if len(closes) >= 50:
        recent_high_50 = max(highs[-50:])
        recent_low_50 = min(lows[-50:])
        extremes["distance_to_high_50"] = (recent_high_50 - current_price) / recent_high_50 * 100
        extremes["distance_to_low_50"] = (current_price - recent_low_50) / recent_low_50 * 100
        extremes["range_position_50"] = (current_price - recent_low_50) / (recent_high_50 - recent_low_50) if recent_high_50 != recent_low_50 else 0.5
    
    return extremes


async def analyze_deep_features(fetcher, signal):
    """Analyze deep pre-signal features for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    
    features = {
        "symbol": symbol,
        "signal_time": signal_time,
        "features": {}
    }
    
    try:
        # Get 15m klines before signal (50 candles back)
        end_time = int(signal_time.timestamp() * 1000)
        start_time = int((signal_time - timedelta(hours=13)).timestamp() * 1000)
        
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines or len(klines) < 25:
            features["features"]["error"] = "Not enough data"
            return features
        
        # Parse klines
        closes = [float(k['close']) for k in klines]
        highs = [float(k['high']) for k in klines]
        lows = [float(k['low']) for k in klines]
        volumes = [float(k['volume']) for k in klines]
        
        # Short-term trend
        features["features"]["short_term_trend"] = analyze_short_term_trend(closes)
        
        # EMA/SMA
        features["features"]["ema_sma"] = analyze_ema_sma(closes, highs, lows)
        
        # Distance to extremes
        features["features"]["distance_to_extremes"] = analyze_distance_to_extremes(closes, highs, lows)
        
        # ATR
        atr = calculate_atr(highs, lows, closes, period=14)
        if atr:
            features["features"]["atr"] = atr
            features["features"]["atr_percent"] = atr / closes[-1] * 100
        
        # Current range vs ATR
        if len(highs) >= 2:
            current_range = (highs[-1] - lows[-1]) / lows[-1] * 100
            features["features"]["current_range_percent"] = current_range
            if atr:
                features["features"]["range_atr_ratio"] = current_range / (atr / closes[-1] * 100)
        
    except Exception as e:
        features["features"]["error"] = str(e)
    
    return features


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("LARGE VALIDATION SAMPLE DEEP FEATURES EXTRACTION")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load candidates with performance
    with open("large_validation_performance.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze deep features
    fetcher = BingXFetcher()
    print("\nAnalyzing deep features...")
    
    success_count = 0
    error_count = 0
    
    for i, candidate in enumerate(candidates, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        features = await analyze_deep_features(fetcher, candidate)
        candidate["deep_features"] = features["features"]
        
        if "error" in features["features"]:
            error_count += 1
        else:
            success_count += 1
    
    print(f"\nDeep features analysis complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    
    # Save results
    results = {
        "candidates": candidates,
        "summary": data["summary"]
    }
    
    with open("large_validation_complete.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to large_validation_complete.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
