#!/usr/bin/env python3
"""
Calculate post-signal performance and extract required features for validation.

Research: Calculate TP +3% / SL -3% performance and extract PM10, PM20, range position, EMA21 slope, HTF directions.

DO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.
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


def calculate_slope(values, period=5):
    """Calculate slope (rate of change)."""
    if len(values) < period:
        return None
    return (values[-1] - values[-period]) / values[-period] * 100


def classify_signal(performance):
    """Classify signal based on performance."""
    if performance["hit_tp_before_sl"]:
        if performance["time_to_3pct_candles"] and performance["time_to_3pct_candles"] <= 10:
            return "VERY_FAST"
        elif performance["time_to_3pct_candles"] and performance["time_to_3pct_candles"] <= 30:
            return "FAST"
        else:
            return "SLOW"
    elif performance["hit_sl_before_tp"]:
        return "SL_HIT"
    else:
        return "NO_REVERSAL"


async def calculate_signal_performance(fetcher, signal):
    """Calculate post-signal performance for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    signal_close = signal["close"]
    
    # Get klines after signal (up to 100 candles = 25 hours)
    start_time = int(signal_time.timestamp() * 1000)
    end_time = int((signal_time + timedelta(hours=25)).timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines:
            return {
                "error": "No post-signal klines",
                "hit_tp_before_sl": False,
                "hit_sl_before_tp": False,
                "time_to_2pct_candles": None,
                "time_to_3pct_candles": None,
                "max_adverse_before_2pct": None,
                "max_adverse_before_3pct": None
            }
        
        tp_3pct = signal_close * 1.03
        sl_3pct = signal_close * 0.97
        
        hit_tp_before_sl = False
        hit_sl_before_tp = False
        time_to_2pct = None
        time_to_3pct = None
        max_adverse_before_2pct = None
        max_adverse_before_3pct = None
        
        tp_2pct = signal_close * 1.02
        
        max_drawdown = 0
        
        for i, kline in enumerate(klines, 1):
            high = float(kline['high'])
            low = float(kline['low'])
            
            # Track max drawdown
            drawdown = (signal_close - low) / signal_close * 100
            max_drawdown = max(max_drawdown, drawdown)
            
            # Check TP
            if not hit_tp_before_sl and not hit_sl_before_tp:
                if high >= tp_2pct and time_to_2pct is None:
                    time_to_2pct = i
                    max_adverse_before_2pct = max_drawdown
                
                if high >= tp_3pct:
                    hit_tp_before_sl = True
                    time_to_3pct = i
                    max_adverse_before_3pct = max_drawdown
                    break
            
            # Check SL
            if low <= sl_3pct:
                hit_sl_before_tp = True
                if time_to_2pct is None:
                    max_adverse_before_2pct = max_drawdown
                if time_to_3pct is None:
                    max_adverse_before_3pct = max_drawdown
                break
        
        return {
            "hit_tp_before_sl": hit_tp_before_sl,
            "hit_sl_before_tp": hit_sl_before_tp,
            "time_to_2pct_candles": time_to_2pct,
            "time_to_3pct_candles": time_to_3pct,
            "max_adverse_before_2pct": max_adverse_before_2pct,
            "max_adverse_before_3pct": max_adverse_before_3pct
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "hit_tp_before_sl": False,
            "hit_sl_before_tp": False,
            "time_to_2pct_candles": None,
            "time_to_3pct_candles": None,
            "max_adverse_before_2pct": None,
            "max_adverse_before_3pct": None
        }


async def extract_features(fetcher, signal):
    """Extract pre-signal features for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    
    features = {}
    
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
        
        if not klines or len(klines) < 30:
            features["error"] = "Not enough 15m data"
            return features
        
        # Parse klines
        closes = [float(k['close']) for k in klines]
        highs = [float(k['high']) for k in klines]
        lows = [float(k['low']) for k in klines]
        
        # Previous movement
        pm10 = (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) >= 11 else None
        pm20 = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else None
        short_term_direction = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else None
        
        features["previous_movement_10"] = pm10
        features["previous_movement_20"] = pm20
        features["short_term_direction"] = short_term_direction
        
        # Range position
        if len(closes) >= 20:
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            range_position = (closes[-1] - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
            features["range_position_20"] = range_position
        
        # EMA21 slope
        ema_21 = calculate_ema(closes, 21)
        if ema_21:
            features["ema_21_slope"] = calculate_slope(closes, 10)
            features["price_above_ema_21"] = closes[-1] > ema_21
        
        # Higher timeframes
        # 1H
        try:
            klines_1h = await fetcher.get_klines(
                symbol=symbol,
                interval="1h",
                limit=100,
                start_time=int((signal_time - timedelta(days=7)).timestamp() * 1000),
                end_time=end_time
            )
            
            if klines_1h and len(klines_1h) >= 20:
                closes_1h = [float(k['close']) for k in klines_1h]
                pm10_1h = (closes_1h[-1] - closes_1h[-11]) / closes_1h[-11] * 100 if len(closes_1h) >= 11 else None
                features["1h_pm10"] = pm10_1h
                features["1h_direction"] = "UP" if pm10_1h and pm10_1h > 0 else "DOWN" if pm10_1h and pm10_1h < 0 else "SIDEWAYS"
        except:
            pass
        
        # 4H
        try:
            klines_4h = await fetcher.get_klines(
                symbol=symbol,
                interval="4h",
                limit=100,
                start_time=int((signal_time - timedelta(days=30)).timestamp() * 1000),
                end_time=end_time
            )
            
            if klines_4h and len(klines_4h) >= 20:
                closes_4h = [float(k['close']) for k in klines_4h]
                pm10_4h = (closes_4h[-1] - closes_4h[-11]) / closes_4h[-11] * 100 if len(closes_4h) >= 11 else None
                features["4h_pm10"] = pm10_4h
                features["4h_direction"] = "UP" if pm10_4h and pm10_4h > 0 else "DOWN" if pm10_4h and pm10_4h < 0 else "SIDEWAYS"
        except:
            pass
        
        # 1D
        try:
            klines_1d = await fetcher.get_klines(
                symbol=symbol,
                interval="1d",
                limit=100,
                start_time=int((signal_time - timedelta(days=180)).timestamp() * 1000),
                end_time=end_time
            )
            
            if klines_1d and len(klines_1d) >= 20:
                closes_1d = [float(k['close']) for k in klines_1d]
                pm10_1d = (closes_1d[-1] - closes_1d[-11]) / closes_1d[-11] * 100 if len(closes_1d) >= 11 else None
                features["1d_pm10"] = pm10_1d
                features["1d_direction"] = "UP" if pm10_1d and pm10_1d > 0 else "DOWN" if pm10_1d and pm10_1d < 0 else "SIDEWAYS"
        except:
            pass
        
    except Exception as e:
        features["error"] = str(e)
    
    return features


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("CALCULATING VALIDATION PERFORMANCE AND EXTRACTING FEATURES")
    print("=" * 100)
    print("\nDO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load validation sample
    with open("validation_sample.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    fetcher = BingXFetcher()
    
    # Calculate performance and extract features
    print("\nCalculating performance and extracting features...")
    
    success_count = 0
    error_count = 0
    
    for i, candidate in enumerate(candidates, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        # Calculate performance
        perf = await calculate_signal_performance(fetcher, candidate)
        candidate["performance"] = perf
        
        # Extract features
        features = await extract_features(fetcher, candidate)
        candidate["features"] = features
        
        # Classify
        if "error" not in perf:
            candidate["category"] = classify_signal(perf)
            success_count += 1
        else:
            candidate["category"] = "ERROR"
            error_count += 1
    
    print(f"\nPerformance calculation complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    
    # Save results
    results = {
        "candidates": candidates,
        "summary": data["summary"]
    }
    
    with open("validation_with_performance.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to validation_with_performance.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
