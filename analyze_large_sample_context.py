#!/usr/bin/env python3
"""
Analyze pre-signal context for large sample of candidates.

Research: Analyze range position, previous movement, local levels for 100 candidates.

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


def find_local_extremes(closes, highs, lows, lookback=5):
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
            if i > 0 and closes[i] < closes[i-1]:
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
        
        # Check if price is at local minimum (within 1%)
        if local_mins:
            nearest_min = min(local_mins, key=lambda x: abs(x["index"] - len(closes)))
            at_local_min = abs(closes[-1] - nearest_min["price"]) / nearest_min["price"] < 0.01
            context["pre_signal"]["at_local_minimum"] = at_local_min
        
    except Exception as e:
        context["pre_signal"]["error"] = str(e)
    
    return context


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("LARGE SAMPLE PRE-SIGNAL CONTEXT ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load candidates
    with open("large_sample_performance_analysis.json", "r") as f:
        data = json.load(f)
    
    candidates = data["candidates"]
    print(f"\nLoaded {len(candidates)} candidates")
    
    # Analyze pre-signal context
    fetcher = BingXFetcher()
    print("\nAnalyzing pre-signal context...")
    
    for i, candidate in enumerate(candidates, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(candidates)}")
        
        context = await analyze_pre_signal_context(fetcher, candidate)
        candidate["pre_signal_context"] = context["pre_signal"]
    
    # Group by category
    categories = {}
    for candidate in candidates:
        cat = candidate["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(candidate)
    
    # Compare pre-signal context by category
    print(f"\n{'=' * 100}")
    print("PRE-SIGNAL CONTEXT BY CATEGORY")
    print(f"{'=' * 100}")
    
    for cat, signals in sorted(categories.items()):
        if not signals:
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
        
        # At local minimum
        at_local_mins = []
        for s in signals:
            if "pre_signal_context" in s and "at_local_minimum" in s["pre_signal_context"]:
                at_local_mins.append(s["pre_signal_context"]["at_local_minimum"])
        
        if at_local_mins:
            pct_at_min = sum(at_local_mins) / len(at_local_mins) * 100
            print(f"  At local minimum: {pct_at_min:.1f}%")
    
    # Focus on FAST vs SL_HIT comparison
    print(f"\n{'=' * 100}")
    print("FAST vs SL_HIT PRE-SIGNAL CONTEXT COMPARISON")
    print(f"{'=' * 100}")
    
    fast_signals = categories.get("VERY_FAST", []) + categories.get("FAST", [])
    sl_hit_signals = categories.get("SL_HIT", [])
    
    print(f"\nFAST/VERY_FAST ({len(fast_signals)} signals) vs SL_HIT ({len(sl_hit_signals)} signals)")
    
    # Range position comparison
    fast_rp = []
    sl_rp = []
    for s in fast_signals:
        if "pre_signal_context" in s and "range_position" in s["pre_signal_context"]:
            rp = s["pre_signal_context"]["range_position"].get("10_candles")
            if rp is not None:
                fast_rp.append(rp)
    for s in sl_hit_signals:
        if "pre_signal_context" in s and "range_position" in s["pre_signal_context"]:
            rp = s["pre_signal_context"]["range_position"].get("10_candles")
            if rp is not None:
                sl_rp.append(rp)
    
    if fast_rp and sl_rp:
        print(f"\nRange position (10 candles):")
        print(f"  FAST: mean={mean(fast_rp):.4f}, median={median(fast_rp):.4f}")
        print(f"  SL_HIT: mean={mean(sl_rp):.4f}, median={median(sl_rp):.4f}")
    
    # Previous movement comparison
    fast_pm = []
    sl_pm = []
    for s in fast_signals:
        if "pre_signal_context" in s and "previous_movement" in s["pre_signal_context"]:
            pm = s["pre_signal_context"]["previous_movement"].get("10_candles")
            if pm is not None:
                fast_pm.append(pm)
    for s in sl_hit_signals:
        if "pre_signal_context" in s and "previous_movement" in s["pre_signal_context"]:
            pm = s["pre_signal_context"]["previous_movement"].get("10_candles")
            if pm is not None:
                sl_pm.append(pm)
    
    if fast_pm and sl_pm:
        print(f"\nPrevious movement (10 candles):")
        print(f"  FAST: mean={mean(fast_pm):.4f}%, median={median(fast_pm):.4f}%")
        print(f"  SL_HIT: mean={mean(sl_pm):.4f}%, median={median(sl_pm):.4f}%")
    
    # Save results
    results = {
        "candidates": candidates,
        "classification": {k: len(v) for k, v in categories.items()}
    }
    
    with open("large_sample_context_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to large_sample_context_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
