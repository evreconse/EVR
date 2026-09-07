#!/usr/bin/env python3
"""
Analyze factors that distinguish fast reversals from slow/no reversals.

Research: Find pre-signal context and candle characteristics that correlate
with fast reversals (reaching +2% quickly without significant adverse move).

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


def calculate_range_position(closes, lookback):
    """Calculate position within range: (current - min) / (max - min)."""
    if len(closes) < lookback:
        return None
    
    recent = closes[-lookback:]
    current = closes[-1]
    min_price = min(recent)
    max_price = max(recent)
    
    if max_price == min_price:
        return 0.5
    
    return (current - min_price) / (max_price - min_price)


def calculate_previous_movement(closes, periods):
    """Calculate percentage change over given periods."""
    results = {}
    for period in periods:
        if len(closes) >= period + 1:
            change = (closes[-1] - closes[-(period + 1)]) / closes[-(period + 1)] * 100
            results[f"{period}_candles"] = change
    return results


def find_local_extremes(closes, highs, lows, lookback=10):
    """Find local minimums and maximums."""
    local_mins = []
    local_maxs = []
    
    for i in range(lookback, len(closes) - lookback):
        is_min = all(lows[i] <= lows[j] for j in range(i - lookback, i + lookback + 1))
        is_max = all(highs[i] >= highs[j] for j in range(i - lookback, i + lookback + 1))
        
        if is_min:
            local_mins.append({"index": i, "price": lows[i]})
        if is_max:
            local_maxs.append({"index": i, "price": highs[i]})
    
    return local_mins, local_maxs


def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range."""
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
    
    return mean(true_ranges[-period:])


async def analyze_pre_signal_context(fetcher, signal):
    """Analyze pre-signal context for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    
    context = {
        "symbol": symbol,
        "signal_time": signal_time,
        "pre_signal": {}
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
        
        if not klines or len(klines) < 20:
            context["pre_signal"]["error"] = "Not enough data"
            return context
        
        # Parse klines
        closes = [float(k['close']) for k in klines]
        highs = [float(k['high']) for k in klines]
        lows = [float(k['low']) for k in klines]
        volumes = [float(k['volume']) for k in klines]
        
        # Range position
        context["pre_signal"]["range_position"] = {}
        for lookback in [10, 20, 50]:
            pos = calculate_range_position(closes, lookback)
            if pos is not None:
                context["pre_signal"]["range_position"][f"{lookback}_candles"] = pos
        
        # Previous movement
        context["pre_signal"]["previous_movement"] = calculate_previous_movement(closes, [1, 2, 3, 5, 10])
        
        # Local extremes
        local_mins, local_maxs = find_local_extremes(closes, highs, lows, lookback=5)
        
        # Distance to nearest support (local minimum)
        if local_mins:
            nearest_min = min(local_mins, key=lambda x: abs(x["index"] - len(closes)))
            context["pre_signal"]["nearest_support"] = {
                "price": nearest_min["price"],
                "candles_away": len(closes) - nearest_min["index"],
                "distance_pct": (closes[-1] - nearest_min["price"]) / nearest_min["price"] * 100
            }
        
        # Consecutive red candles
        red_count = 0
        for i in range(len(closes) - 1, -1, -1):
            if closes[i] < closes[i-1] if i > 0 else False:
                red_count += 1
            else:
                break
        context["pre_signal"]["consecutive_red_candles"] = red_count
        
        # Volume analysis
        if len(volumes) >= 20:
            avg_volume_5 = mean(volumes[-5:-1]) if len(volumes) >= 5 else volumes[-2]
            avg_volume_10 = mean(volumes[-10:-1]) if len(volumes) >= 10 else volumes[-2]
            avg_volume_20 = mean(volumes[-20:-1]) if len(volumes) >= 20 else volumes[-2]
            
            context["pre_signal"]["volume_analysis"] = {
                "avg_volume_5": avg_volume_5,
                "avg_volume_10": avg_volume_10,
                "avg_volume_20": avg_volume_20,
                "current_volume": volumes[-1]
            }
        
        # ATR
        atr = calculate_atr(highs, lows, closes, 14)
        if atr and closes[-1] > 0:
            context["pre_signal"]["atr_percent"] = atr / closes[-1] * 100
        
        # Check if price is at local minimum (within 1%)
        if local_mins:
            nearest_min = min(local_mins, key=lambda x: abs(x["index"] - len(closes)))
            at_local_min = abs(closes[-1] - nearest_min["price"]) / nearest_min["price"] < 0.01
            context["pre_signal"]["at_local_minimum"] = at_local_min
        
    except Exception as e:
        context["pre_signal"]["error"] = str(e)
    
    return context


async def analyze_mae_detailed(fetcher, signal):
    """Calculate detailed Maximum Adverse Excursion before +2%."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    signal_close = signal["close"]
    
    mae_data = {
        "max_adverse_before_1pct": None,
        "max_adverse_before_2pct": None,
        "max_adverse_before_3pct": None,
        "max_adverse_overall": None,
        "time_to_1pct": None,
        "time_to_2pct": None,
        "time_to_3pct": None,
        "hit_sl_3pct": False,
        "candles_before_sl": None
    }
    
    try:
        end_time = int((signal_time + timedelta(hours=4)).timestamp() * 1000)
        start_time = int(signal_time.timestamp() * 1000)
        
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines or len(klines) < 2:
            return mae_data
        
        # Find signal candle
        signal_idx = None
        for i, k in enumerate(klines):
            if abs(int(k['time']) - signal["timestamp_ms"]) < 900000:
                signal_idx = i
                break
        
        if signal_idx is None:
            return mae_data
        
        max_adverse_1pct = 0
        max_adverse_2pct = 0
        max_adverse_3pct = 0
        max_adverse_overall = 0
        
        for i in range(signal_idx + 1, len(klines)):
            k = klines[i]
            high = float(k['high'])
            low = float(k['low'])
            
            up_move = (high - signal_close) / signal_close * 100
            down_move = (low - signal_close) / signal_close * 100
            
            max_adverse_overall = max(max_adverse_overall, abs(down_move))
            
            # Track adverse before targets
            if mae_data["time_to_1pct"] is None:
                max_adverse_1pct = max(max_adverse_1pct, abs(down_move))
            if mae_data["time_to_2pct"] is None:
                max_adverse_2pct = max(max_adverse_2pct, abs(down_move))
            if mae_data["time_to_3pct"] is None:
                max_adverse_3pct = max(max_adverse_3pct, abs(down_move))
            
            # Check if SL hit
            if down_move <= -3.0 and not mae_data["hit_sl_3pct"]:
                mae_data["hit_sl_3pct"] = True
                mae_data["candles_before_sl"] = i - signal_idx
            
            # Track time to targets
            if mae_data["time_to_1pct"] is None and up_move >= 1.0:
                mae_data["time_to_1pct"] = i - signal_idx
                mae_data["max_adverse_before_1pct"] = max_adverse_1pct
            if mae_data["time_to_2pct"] is None and up_move >= 2.0:
                mae_data["time_to_2pct"] = i - signal_idx
                mae_data["max_adverse_before_2pct"] = max_adverse_2pct
            if mae_data["time_to_3pct"] is None and up_move >= 3.0:
                mae_data["time_to_3pct"] = i - signal_idx
                mae_data["max_adverse_before_3pct"] = max_adverse_3pct
        
        mae_data["max_adverse_overall"] = max_adverse_overall
        
        # If targets not reached, record final adverse
        if mae_data["time_to_1pct"] is None:
            mae_data["max_adverse_before_1pct"] = max_adverse_1pct
        if mae_data["time_to_2pct"] is None:
            mae_data["max_adverse_before_2pct"] = max_adverse_2pct
        if mae_data["time_to_3pct"] is None:
            mae_data["max_adverse_before_3pct"] = max_adverse_3pct
        
    except Exception as e:
        mae_data["error"] = str(e)
    
    return mae_data


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("FAST REVERSAL FACTORS ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load control signals
    with open("manual_vs_control_analysis.json", "r") as f:
        data = json.load(f)
    
    control_signals = data["control_signals"]
    print(f"\nLoaded {len(control_signals)} control signals")
    
    # Analyze pre-signal context and MAE
    fetcher = BingXFetcher()
    
    print("\nAnalyzing pre-signal context...")
    for signal in control_signals:
        context = await analyze_pre_signal_context(fetcher, signal)
        signal["pre_signal_context"] = context["pre_signal"]
    
    print("\nCalculating detailed MAE...")
    for signal in control_signals:
        mae = await analyze_mae_detailed(fetcher, signal)
        signal["mae_detailed"] = mae
    
    # Re-classify based on MAE
    for signal in control_signals:
        mae = signal["mae_detailed"]
        
        if "error" in mae:
            signal["sl_risk_category"] = "ERROR"
            continue
        
        if mae["hit_sl_3pct"]:
            signal["sl_risk_category"] = "SL_HIT"
        elif mae["max_adverse_before_2pct"] and mae["max_adverse_before_2pct"] >= 2.5:
            signal["sl_risk_category"] = "HIGH_RISK"
        elif mae["max_adverse_before_2pct"] and mae["max_adverse_before_2pct"] >= 1.5:
            signal["sl_risk_category"] = "MODERATE_RISK"
        elif mae["time_to_2pct"] is not None:
            signal["sl_risk_category"] = "LOW_RISK"
        else:
            signal["sl_risk_category"] = "NO_REVERSAL"
    
    # Print classification
    print(f"\n{'=' * 100}")
    print("SL RISK CLASSIFICATION")
    print(f"{'=' * 100}")
    
    categories = {}
    for signal in control_signals:
        cat = signal["sl_risk_category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(signal)
    
    for cat, signals in categories.items():
        print(f"\n{cat}: {len(signals)} signals")
        for s in signals:
            mae = s["mae_detailed"]
            print(f"  {s['symbol']}: MAE before +2%={mae.get('max_adverse_before_2pct', 'N/A')}%, Time to +2%={mae.get('time_to_2pct', 'N/A')}")
    
    # Compare metrics by SL risk category
    print(f"\n{'=' * 100}")
    print("METRICS BY SL RISK CATEGORY")
    print(f"{'=' * 100}")
    
    metrics = ["body_percent", "range_percent", "lower_wick_body_ratio", "lower_wick_range_ratio", "open_to_low_percent", "volume_ratio"]
    
    for cat, signals in categories.items():
        if not signals or cat == "ERROR":
            continue
        
        print(f"\n{cat} ({len(signals)} signals):")
        for metric in metrics:
            values = [s.get(metric, 0) for s in signals if metric in s]
            if values:
                print(f"  {metric}: mean={mean(values):.4f}, median={median(values):.4f}")
    
    # Compare pre-signal context by category
    print(f"\n{'=' * 100}")
    print("PRE-SIGNAL CONTEXT BY SL RISK CATEGORY")
    print(f"{'=' * 100}")
    
    for cat, signals in categories.items():
        if not signals or cat == "ERROR":
            continue
        
        print(f"\n{cat} ({len(signals)} signals):")
        
        # Range position
        range_positions_10 = []
        for s in signals:
            if "pre_signal_context" in s and "range_position" in s["pre_signal_context"]:
                rp = s["pre_signal_context"]["range_position"].get("10_candles")
                if rp is not None:
                    range_positions_10.append(rp)
        
        if range_positions_10:
            print(f"  Range position (10 candles): mean={mean(range_positions_10):.4f}, median={median(range_positions_10):.4f}")
        
        # Previous movement
        prev_movements_10 = []
        for s in signals:
            if "pre_signal_context" in s and "previous_movement" in s["pre_signal_context"]:
                pm = s["pre_signal_context"]["previous_movement"].get("10_candles")
                if pm is not None:
                    prev_movements_10.append(pm)
        
        if prev_movements_10:
            print(f"  Previous movement (10 candles): mean={mean(prev_movements_10):.4f}%, median={median(prev_movements_10):.4f}%")
        
        # Consecutive red candles
        red_counts = []
        for s in signals:
            if "pre_signal_context" in s and "consecutive_red_candles" in s["pre_signal_context"]:
                red_counts.append(s["pre_signal_context"]["consecutive_red_candles"])
        
        if red_counts:
            print(f"  Consecutive red candles: mean={mean(red_counts):.1f}, median={median(red_counts):.1f}")
    
    # Save results
    results = {
        "control_signals": control_signals,
        "classification": {k: len(v) for k, v in categories.items()}
    }
    
    with open("fast_reversal_factors_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to fast_reversal_factors_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
