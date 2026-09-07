#!/usr/bin/env python3
"""
Analyze pre-signal context for 30 manual signals.

Research: Why manual signals reversed immediately vs some automatic candidates continued falling.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def calculate_ema(prices, period):
    """Calculate EMA for given period."""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def calculate_sma(prices, period):
    """Calculate SMA for given period."""
    if len(prices) < period:
        return None
    
    return sum(prices[-period:]) / period


def calculate_atr(highs, lows, period=14):
    """Calculate ATR for given period."""
    if len(highs) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]) if i > 0 else 0,
            abs(lows[i] - closes[i-1]) if i > 0 else 0
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return None
    
    return sum(true_ranges[-period:]) / period


async def analyze_signal_context(symbol, signal_time, fetcher):
    """Analyze context before a signal for multiple timeframes."""
    
    # Get historical data for different timeframes
    timeframes = ["15m", "1h", "4h", "1d"]
    
    context = {
        "symbol": symbol,
        "signal_time": signal_time,
        "timeframes": {}
    }
    
    for tf in timeframes:
        # Calculate limit based on timeframe
        if tf == "15m":
            limit = 1000
        elif tf == "1h":
            limit = 1000
        elif tf == "4h":
            limit = 500
        else:  # 1d
            limit = 365
        
        try:
            # Get recent klines (most recent data available)
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval=tf,
                limit=limit
            )
            
            if not klines or len(klines) < 20:
                context["timeframes"][tf] = {"error": "Not enough data"}
                continue
            
            # Parse klines
            closes = [float(k['close']) for k in klines]
            highs = [float(k['high']) for k in klines]
            lows = [float(k['low']) for k in klines]
            opens = [float(k['open']) for k in klines]
            volumes = [float(k['volume']) for k in klines]
            timestamps = [int(k['time']) for k in klines]
            
            # Find the candle that contains or is closest to signal time
            signal_candle_idx = None
            min_diff = float('inf')
            
            for i, ts in enumerate(timestamps):
                candle_time = datetime.fromtimestamp(ts / 1000, tz=UTC)
                diff = abs((candle_time - signal_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    signal_candle_idx = i
            
            if signal_candle_idx is None or signal_candle_idx >= len(klines):
                context["timeframes"][tf] = {"error": "Could not find signal candle"}
                continue
            
            # Analyze context
            tf_context = {
                "signal_candle_idx": signal_candle_idx,
                "signal_close": closes[signal_candle_idx],
                "signal_high": highs[signal_candle_idx],
                "signal_low": lows[signal_candle_idx],
                "signal_open": opens[signal_candle_idx],
            }
            
            # 1. Range position %
            range_high = max(highs[:signal_candle_idx+1])
            range_low = min(lows[:signal_candle_idx+1])
            if range_high != range_low:
                range_position = (closes[signal_candle_idx] - range_low) / (range_high - range_low)
            else:
                range_position = 0.5
            tf_context["range_position_pct"] = range_position * 100
            tf_context["range_high"] = range_high
            tf_context["range_low"] = range_low
            
            # 2. Previous downward movement
            if signal_candle_idx >= 1:
                prev_1_change = (closes[signal_candle_idx] - closes[signal_candle_idx-1]) / closes[signal_candle_idx-1] * 100
                tf_context["prev_1_candle_change_pct"] = prev_1_change
            else:
                tf_context["prev_1_candle_change_pct"] = 0
            
            if signal_candle_idx >= 3:
                prev_3_change = (closes[signal_candle_idx] - closes[signal_candle_idx-3]) / closes[signal_candle_idx-3] * 100
                tf_context["prev_3_candles_change_pct"] = prev_3_change
            else:
                tf_context["prev_3_candles_change_pct"] = 0
            
            if signal_candle_idx >= 5:
                prev_5_change = (closes[signal_candle_idx] - closes[signal_candle_idx-5]) / closes[signal_candle_idx-5] * 100
                tf_context["prev_5_candles_change_pct"] = prev_5_change
            else:
                tf_context["prev_5_candles_change_pct"] = 0
            
            if signal_candle_idx >= 10:
                prev_10_change = (closes[signal_candle_idx] - closes[signal_candle_idx-10]) / closes[signal_candle_idx-10] * 100
                tf_context["prev_10_candles_change_pct"] = prev_10_change
            else:
                tf_context["prev_10_candles_change_pct"] = 0
            
            # 3. Local minimum analysis
            if signal_candle_idx >= 5:
                recent_lows = lows[signal_candle_idx-5:signal_candle_idx+1]
                local_min = min(recent_lows)
                local_min_idx = recent_lows.index(local_min) + signal_candle_idx - 5
                
                # Check if signal is at or near local minimum
                is_at_local_min = abs(lows[signal_candle_idx] - local_min) / local_min < 0.01
                tf_context["is_at_local_min"] = is_at_local_min
                tf_context["local_min"] = local_min
                tf_context["local_min_distance_pct"] = (lows[signal_candle_idx] - local_min) / local_min * 100
            else:
                tf_context["is_at_local_min"] = False
                tf_context["local_min"] = None
                tf_context["local_min_distance_pct"] = None
            
            # 4. Previous swing low (look back 20 candles)
            if signal_candle_idx >= 20:
                swing_low = min(lows[signal_candle_idx-20:signal_candle_idx])
                swing_low_idx = lows[signal_candle_idx-20:signal_candle_idx].index(swing_low) + signal_candle_idx - 20
                
                # Check if signal broke swing low
                broke_swing_low = lows[signal_candle_idx] < swing_low
                tf_context["broke_previous_swing_low"] = broke_swing_low
                tf_context["previous_swing_low"] = swing_low
                tf_context["swing_low_break_pct"] = (swing_low - lows[signal_candle_idx]) / swing_low * 100 if broke_swing_low else 0
                
                # Check if closed back above
                closed_above = closes[signal_candle_idx] > swing_low
                tf_context["closed_above_swing_low"] = closed_above
            else:
                tf_context["broke_previous_swing_low"] = False
                tf_context["previous_swing_low"] = None
                tf_context["swing_low_break_pct"] = 0
                tf_context["closed_above_swing_low"] = False
            
            # 5. Trend structure (Lower High / Lower Low)
            if signal_candle_idx >= 10:
                recent_highs = highs[signal_candle_idx-10:signal_candle_idx+1]
                recent_lows = lows[signal_candle_idx-10:signal_candle_idx+1]
                
                # Count consecutive red candles
                red_count = 0
                for i in range(signal_candle_idx, max(0, signal_candle_idx-10), -1):
                    if closes[i] < opens[i]:
                        red_count += 1
                    else:
                        break
                
                tf_context["consecutive_red_candles"] = red_count
                
                # Check for lower highs pattern
                highs_descending = all(recent_highs[i] >= recent_highs[i+1] for i in range(len(recent_highs)-1))
                tf_context["descending_highs"] = highs_descending
                
                # Check for lower lows pattern
                lows_descending = all(recent_lows[i] >= recent_lows[i+1] for i in range(len(recent_lows)-1))
                tf_context["descending_lows"] = lows_descending
            else:
                tf_context["consecutive_red_candles"] = 0
                tf_context["descending_highs"] = False
                tf_context["descending_lows"] = False
            
            # 6. Volatility (ATR, range expansion)
            if len(highs) >= 15:
                atr = calculate_atr(highs, lows, 14)
                tf_context["atr_14"] = atr
                
                # Current range vs average range
                current_range = highs[signal_candle_idx] - lows[signal_candle_idx]
                avg_range = sum(highs[signal_candle_idx-10:signal_candle_idx] - lows[signal_candle_idx-10:signal_candle_idx]) / 10
                if avg_range > 0:
                    range_expansion = current_range / avg_range
                else:
                    range_expansion = 1
                tf_context["range_expansion_ratio"] = range_expansion
            else:
                tf_context["atr_14"] = None
                tf_context["range_expansion_ratio"] = None
            
            # 7. EMA/SMA position
            if len(closes) >= 20:
                ema_20 = calculate_ema(closes[:signal_candle_idx+1], 20)
                sma_20 = calculate_sma(closes[:signal_candle_idx+1], 20)
                tf_context["ema_20"] = ema_20
                tf_context["sma_20"] = sma_20
                tf_context["price_vs_ema_20_pct"] = (closes[signal_candle_idx] - ema_20) / ema_20 * 100 if ema_20 else None
            else:
                tf_context["ema_20"] = None
                tf_context["sma_20"] = None
                tf_context["price_vs_ema_20_pct"] = None
            
            if len(closes) >= 50:
                ema_50 = calculate_ema(closes[:signal_candle_idx+1], 50)
                sma_50 = calculate_sma(closes[:signal_candle_idx+1], 50)
                tf_context["ema_50"] = ema_50
                tf_context["sma_50"] = sma_50
                tf_context["price_vs_ema_50_pct"] = (closes[signal_candle_idx] - ema_50) / ema_50 * 100 if ema_50 else None
            else:
                tf_context["ema_50"] = None
                tf_context["sma_50"] = None
                tf_context["price_vs_ema_50_pct"] = None
            
            if len(closes) >= 200:
                ema_200 = calculate_ema(closes[:signal_candle_idx+1], 200)
                sma_200 = calculate_sma(closes[:signal_candle_idx+1], 200)
                tf_context["ema_200"] = ema_200
                tf_context["sma_200"] = sma_200
                tf_context["price_vs_ema_200_pct"] = (closes[signal_candle_idx] - ema_200) / ema_200 * 100 if ema_200 else None
            else:
                tf_context["ema_200"] = None
                tf_context["sma_200"] = None
                tf_context["price_vs_ema_200_pct"] = None
            
            context["timeframes"][tf] = tf_context
            
        except Exception as e:
            context["timeframes"][tf] = {"error": str(e)}
    
    return context


async def main():
    """Main function to analyze pre-signal context."""
    print("=" * 100)
    print("PRE-SIGNAL CONTEXT ANALYSIS - 30 MANUAL SIGNALS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load 30 manual signals (excluding FF-USDT)
    with open("minimum_candle_size_research.json", "r") as f:
        data = json.load(f)
    
    signals = data["signals"]
    
    # Exclude FF-USDT
    signals = [s for s in signals if s["symbol"] != "FF-USDT"]
    
    print(f"\nLoaded {len(signals)} signals (excluding FF-USDT)")
    
    fetcher = BingXFetcher()
    
    all_contexts = []
    
    for i, signal in enumerate(signals, 1):
        symbol = signal["symbol"]
        signal_time = datetime.fromtimestamp(signal["actual_timestamp_ms"] / 1000, tz=UTC)
        
        print(f"\n[{i}/{len(signals)}] Analyzing {symbol} at {signal_time}")
        
        try:
            context = await analyze_signal_context(symbol, signal_time, fetcher)
            all_contexts.append(context)
            print(f"  Completed analysis for {symbol}")
        except Exception as e:
            print(f"  Error analyzing {symbol}: {e}")
            all_contexts.append({
                "symbol": symbol,
                "signal_time": signal_time,
                "error": str(e)
            })
    
    # Save results
    with open("pre_signal_context_analysis.json", "w") as f:
        json.dump(all_contexts, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print(f"Analysis complete. Results saved to pre_signal_context_analysis.json")
    print(f"{'=' * 100}")


# Global closes for ATR calculation
closes = []


if __name__ == "__main__":
    asyncio.run(main())
