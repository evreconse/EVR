#!/usr/bin/env python3
"""
Extract comprehensive features for deep context research.

Research: Extract all available features including PM5/20/30, EMA 9/50/100, range positions, etc.

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


def analyze_previous_movement(closes):
    """Analyze previous price movement for multiple periods."""
    movements = {}
    
    for period in [5, 10, 20, 30]:
        if len(closes) >= period + 1:
            change = (closes[-1] - closes[-(period + 1)]) / closes[-(period + 1)] * 100
            movements[f"{period}_candles"] = change
    
    # Green/red candle counts
    green_count = 0
    red_count = 0
    for i in range(1, min(31, len(closes))):
        if closes[i] > closes[i-1]:
            green_count += 1
        elif closes[i] < closes[i-1]:
            red_count += 1
    
    movements["green_count_30"] = green_count
    movements["red_count_30"] = red_count
    movements["green_red_ratio_30"] = green_count / red_count if red_count > 0 else None
    
    # Max up/down before signal
    if len(closes) >= 30:
        max_up = max((closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, min(31, len(closes))))
        max_down = min((closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, min(31, len(closes))))
        movements["max_up_30"] = max_up
        movements["max_down_30"] = max_down
    
    # Growth/detection before signal
    if len(closes) >= 10:
        growth_10 = (closes[-1] - closes[-10]) / closes[-10] * 100
        movements["growth_10"] = growth_10
        movements["was_growth_10"] = growth_10 > 0
    
    return movements


def analyze_ema_structure(closes, highs, lows):
    """Analyze EMA structure with multiple EMAs."""
    indicators = {}
    
    if len(closes) < 100:
        return indicators
    
    current_price = closes[-1]
    
    # EMAs
    ema_9 = calculate_ema(closes, 9)
    ema_21 = calculate_ema(closes, 21)
    ema_50 = calculate_ema(closes, 50)
    ema_100 = calculate_ema(closes, 100)
    
    if ema_9:
        indicators["price_above_ema_9"] = current_price > ema_9
        indicators["price_ema_9_distance"] = (current_price - ema_9) / ema_9 * 100
        indicators["ema_9_slope"] = calculate_slope(closes, 5)
    
    if ema_21:
        indicators["price_above_ema_21"] = current_price > ema_21
        indicators["price_ema_21_distance"] = (current_price - ema_21) / ema_21 * 100
        indicators["ema_21_slope"] = calculate_slope(closes, 10)
    
    if ema_50:
        indicators["price_above_ema_50"] = current_price > ema_50
        indicators["price_ema_50_distance"] = (current_price - ema_50) / ema_50 * 100
        indicators["ema_50_slope"] = calculate_slope(closes, 20)
    
    if ema_100:
        indicators["price_above_ema_100"] = current_price > ema_100
        indicators["price_ema_100_distance"] = (current_price - ema_100) / ema_100 * 100
        indicators["ema_100_slope"] = calculate_slope(closes, 30)
    
    # EMA alignment
    if ema_9 and ema_21:
        indicators["ema_9_21_alignment"] = (ema_9 > ema_21)
    if ema_21 and ema_50:
        indicators["ema_21_50_alignment"] = (ema_21 > ema_50)
    if ema_50 and ema_100:
        indicators["ema_50_100_alignment"] = (ema_50 > ema_100)
    
    # Higher high / higher low sequences
    if len(highs) >= 20:
        higher_highs = 0
        higher_lows = 0
        for i in range(1, 20):
            if highs[-i] > highs[-i-1]:
                higher_highs += 1
            if lows[-i] > lows[-i-1]:
                higher_lows += 1
        indicators["higher_highs_20"] = higher_highs
        indicators["higher_lows_20"] = higher_lows
    
    return indicators


def analyze_range_positions(closes, highs, lows):
    """Analyze range positions for multiple windows."""
    positions = {}
    
    if len(closes) < 100:
        return positions
    
    current_price = closes[-1]
    
    for window in [10, 20, 50, 100]:
        if len(closes) >= window:
            recent_high = max(highs[-window:])
            recent_low = min(lows[-window:])
            
            positions[f"distance_to_high_{window}"] = (recent_high - current_price) / recent_high * 100
            positions[f"distance_to_low_{window}"] = (current_price - recent_low) / recent_low * 100
            positions[f"range_position_{window}"] = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
            
            # Breakout detection
            if window >= 20:
                prev_high = max(highs[-window:-10])
                prev_low = min(lows[-window:-10])
                positions[f"recent_high_breakout_{window}"] = recent_high > prev_high
                positions[f"recent_low_breakout_{window}"] = recent_low < prev_low
    
    return positions


def analyze_volatility(closes, highs, lows, volumes):
    """Analyze volatility metrics."""
    volatility = {}
    
    if len(closes) < 50:
        return volatility
    
    # Current range
    current_range = (highs[-1] - lows[-1]) / lows[-1] * 100
    volatility["current_range_percent"] = current_range
    
    # Average range
    ranges = [(highs[i] - lows[i]) / lows[i] * 100 for i in range(-20, 0)]
    volatility["avg_range_20"] = mean(ranges)
    
    # ATR
    atr = calculate_atr(highs, lows, closes, period=14)
    if atr:
        volatility["atr"] = atr
        volatility["atr_percent"] = atr / closes[-1] * 100
    
    # Range expansion/contraction
    if len(ranges) >= 10:
        volatility["range_expansion"] = ranges[-1] > mean(ranges[-10:-1])
        volatility["range_contraction"] = ranges[-1] < mean(ranges[-10:-1])
    
    # Volatility regime
    if volatility.get("avg_range_20"):
        volatility["volatility_regime"] = "HIGH" if current_range > volatility["avg_range_20"] * 1.5 else "NORMAL"
    
    return volatility


def analyze_volume(volumes):
    """Analyze volume metrics."""
    volume_metrics = {}
    
    if len(volumes) < 20:
        return volume_metrics
    
    current_volume = volumes[-1]
    avg_volume = mean(volumes[-20:])
    
    volume_metrics["volume_relative_avg"] = current_volume / avg_volume if avg_volume > 0 else None
    volume_metrics["volume_growth_5"] = (volumes[-1] - volumes[-6]) / volumes[-6] * 100 if len(volumes) >= 6 else None
    volume_metrics["volume_decline_5"] = (volumes[-1] - volumes[-6]) / volumes[-6] * 100 if len(volumes) >= 6 else None
    
    return volume_metrics


async def analyze_comprehensive_features(fetcher, signal):
    """Analyze comprehensive pre-signal features for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    
    features = {
        "symbol": symbol,
        "signal_time": signal_time,
        "features": {}
    }
    
    try:
        # Get 15m klines before signal (100 candles back)
        end_time = int(signal_time.timestamp() * 1000)
        start_time = int((signal_time - timedelta(hours=25)).timestamp() * 1000)
        
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=200,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines or len(klines) < 50:
            features["features"]["error"] = "Not enough data"
            return features
        
        # Parse klines
        closes = [float(k['close']) for k in klines]
        highs = [float(k['high']) for k in klines]
        lows = [float(k['low']) for k in klines]
        volumes = [float(k['volume']) for k in klines]
        
        # Previous movement
        features["features"]["previous_movement"] = analyze_previous_movement(closes)
        
        # EMA structure
        features["features"]["ema_structure"] = analyze_ema_structure(closes, highs, lows)
        
        # Range positions
        features["features"]["range_positions"] = analyze_range_positions(closes, highs, lows)
        
        # Volatility
        features["features"]["volatility"] = analyze_volatility(closes, highs, lows, volumes)
        
        # Volume
        features["features"]["volume"] = analyze_volume(volumes)
        
    except Exception as e:
        features["features"]["error"] = str(e)
    
    return features


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("COMPREHENSIVE FEATURES EXTRACTION")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load candidates
    with open("large_diverse_sample.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze comprehensive features
    fetcher = BingXFetcher()
    print("\nAnalyzing comprehensive features...")
    
    success_count = 0
    error_count = 0
    
    for i, candidate in enumerate(candidates, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        features = await analyze_comprehensive_features(fetcher, candidate)
        candidate["comprehensive_features"] = features["features"]
        
        if "error" in features["features"]:
            error_count += 1
        else:
            success_count += 1
    
    print(f"\nComprehensive features analysis complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    
    # Save results
    results = {
        "candidates": candidates,
        "summary": data["summary"]
    }
    
    with open("large_comprehensive.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to large_comprehensive.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
