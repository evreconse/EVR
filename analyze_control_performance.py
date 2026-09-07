#!/usr/bin/env python3
"""
Detailed analysis of control sample post-signal performance.

Research: Understand why control signals perform differently from manual signals.

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


async def analyze_detailed_post_signal(fetcher, signals):
    """Analyze detailed post-signal performance for signals."""
    
    for signal in signals:
        symbol = signal["symbol"]
        signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
        signal_close = signal["close"]
        
        try:
            # Get klines after signal time (4 hours forward)
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
                signal["detailed_post_signal"] = {"error": "Not enough data"}
                continue
            
            # Find the signal candle
            signal_idx = None
            for i, k in enumerate(klines):
                if abs(int(k['time']) - signal["timestamp_ms"]) < 900000:  # Within 15 minutes
                    signal_idx = i
                    break
            
            if signal_idx is None:
                signal["detailed_post_signal"] = {"error": "Signal candle not found"}
                continue
            
            # Analyze performance candle by candle
            performance = []
            max_up = 0
            max_down = 0
            time_to_1pct = None
            time_to_2pct = None
            time_to_3pct = None
            max_adverse_move = 0
            adverse_move_before_2pct = 0
            
            for i in range(signal_idx + 1, len(klines)):
                k = klines[i]
                high = float(k['high'])
                low = float(k['low'])
                close = float(k['close'])
                
                # Calculate moves from signal close
                up_move = (high - signal_close) / signal_close * 100
                down_move = (low - signal_close) / signal_close * 100
                close_move = (close - signal_close) / signal_close * 100
                
                max_up = max(max_up, up_move)
                max_down = min(max_down, down_move)
                max_adverse_move = max(max_adverse_move, abs(down_move))
                
                # Track adverse move before reaching +2%
                if time_to_2pct is None:
                    adverse_move_before_2pct = max(adverse_move_before_2pct, abs(down_move))
                
                # Track time to targets
                if time_to_1pct is None and up_move >= 1.0:
                    time_to_1pct = i - signal_idx
                if time_to_2pct is None and up_move >= 2.0:
                    time_to_2pct = i - signal_idx
                if time_to_3pct is None and up_move >= 3.0:
                    time_to_3pct = i - signal_idx
                
                performance.append({
                    "candle": i - signal_idx,
                    "up_move": up_move,
                    "down_move": down_move,
                    "close_move": close_move,
                    "max_up_so_far": max_up,
                    "max_down_so_far": max_down
                })
            
            # Classify performance
            if max_up >= 2.0:
                if time_to_2pct <= 2:
                    performance_type = "FAST_REVERSAL"
                elif time_to_2pct <= 4:
                    performance_type = "MODERATE_REVERSAL"
                else:
                    performance_type = "SLOW_REVERSAL"
            elif max_up >= 1.0:
                performance_type = "WEAK_REVERSAL"
            else:
                performance_type = "NO_REVERSAL"
            
            signal["detailed_post_signal"] = {
                "performance_type": performance_type,
                "max_up_pct": max_up,
                "max_down_pct": max_down,
                "time_to_1pct_candles": time_to_1pct,
                "time_to_2pct_candles": time_to_2pct,
                "time_to_3pct_candles": time_to_3pct,
                "max_adverse_move_pct": max_adverse_move,
                "adverse_move_before_2pct_pct": adverse_move_before_2pct,
                "candle_performance": performance
            }
            
        except Exception as e:
            signal["detailed_post_signal"] = {"error": str(e)}


def classify_by_performance(signals):
    """Classify signals by performance type."""
    classification = {
        "FAST_REVERSAL": [],
        "MODERATE_REVERSAL": [],
        "SLOW_REVERSAL": [],
        "WEAK_REVERSAL": [],
        "NO_REVERSAL": [],
        "ERROR": []
    }
    
    for signal in signals:
        if "detailed_post_signal" not in signal:
            classification["ERROR"].append(signal)
        elif "error" in signal["detailed_post_signal"]:
            classification["ERROR"].append(signal)
        else:
            perf_type = signal["detailed_post_signal"]["performance_type"]
            classification[perf_type].append(signal)
    
    return classification


def analyze_performance_differences(classification):
    """Analyze metric differences between performance types."""
    
    metrics = [
        "body_percent",
        "range_percent",
        "lower_wick_body_ratio",
        "lower_wick_range_ratio",
        "open_to_low_percent",
        "volume_ratio"
    ]
    
    analysis = {}
    
    for perf_type, signals in classification.items():
        if not signals:
            continue
        
        type_analysis = {}
        
        for metric in metrics:
            values = [s.get(metric, 0) for s in signals if metric in s]
            if values:
                type_analysis[metric] = {
                    "count": len(values),
                    "mean": mean(values),
                    "median": median(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        analysis[perf_type] = {
            "count": len(signals),
            "metrics": type_analysis
        }
    
    return analysis


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("DETAILED POST-SIGNAL PERFORMANCE ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load control sample
    with open("manual_vs_control_analysis.json", "r") as f:
        data = json.load(f)
    
    control_signals = data["control_signals"]
    print(f"\nLoaded {len(control_signals)} control signals")
    
    # Analyze detailed post-signal performance
    fetcher = BingXFetcher()
    print("\nAnalyzing detailed post-signal performance...")
    await analyze_detailed_post_signal(fetcher, control_signals)
    
    # Classify by performance
    print("\nClassifying by performance type...")
    classification = classify_by_performance(control_signals)
    
    # Print classification summary
    print(f"\n{'=' * 100}")
    print("PERFORMANCE CLASSIFICATION")
    print(f"{'=' * 100}")
    
    for perf_type, signals in classification.items():
        print(f"\n{perf_type}: {len(signals)} signals")
        if signals:
            max_ups = [s["detailed_post_signal"]["max_up_pct"] for s in signals if "detailed_post_signal" in s and "max_up_pct" in s["detailed_post_signal"]]
            if max_ups:
                print(f"  Max Up: mean={mean(max_ups):.2f}%, median={median(max_ups):.2f}%")
    
    # Analyze metric differences
    print(f"\n{'=' * 100}")
    print("METRIC DIFFERENCES BY PERFORMANCE TYPE")
    print(f"{'=' * 100}")
    
    analysis = analyze_performance_differences(classification)
    
    for perf_type, data in analysis.items():
        print(f"\n{perf_type} ({data['count']} signals):")
        for metric, stats in data["metrics"].items():
            print(f"  {metric}: mean={stats['mean']:.4f}, median={stats['median']:.4f}")
    
    # Save results
    results = {
        "control_signals": control_signals,
        "classification": {k: len(v) for k, v in classification.items()},
        "detailed_analysis": analysis
    }
    
    with open("control_performance_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to control_performance_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
