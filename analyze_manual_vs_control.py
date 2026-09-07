#!/usr/bin/env python3
"""
Analyze 30 manual signals vs control sample of recent signals.

Research: Find patterns that distinguish manual signals (fast reversals) 
from ordinary candles meeting the same conditions.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
from statistics import mean, median, stdev
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def analyze_candle_geometry(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Analyze candle geometry."""
    is_red = close_price < open_price
    body = abs(close_price - open_price)
    upper_wick = high_price - max(open_price, close_price)
    lower_wick = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    return {
        "is_red": is_red,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "total_range": total_range,
        "lower_wick_body_ratio": lower_wick / body if body > 0 else 0,
        "lower_wick_range_ratio": lower_wick / total_range if total_range > 0 else 0,
        "body_percent": body / open_price * 100,
        "range_percent": total_range / open_price * 100,
        "open_to_low_percent": (low_price - open_price) / open_price * 100,
    }


async def find_control_sample(fetcher, limit=50):
    """Load experimental candidates as control sample."""
    
    # Load the experimental candidates we already found
    try:
        with open("experimental_candidates_formula3.json", "r") as f:
            experimental_data = json.load(f)
        
        control_sample = []
        for cand in experimental_data:
            control_sample.append({
                "symbol": cand["symbol"],
                "timestamp_ms": int(datetime.strptime(cand["event_time"], "%d.%m.%Y %H:%M UTC").replace(tzinfo=UTC).timestamp() * 1000),
                "open": cand["open"],
                "high": cand["high"],
                "low": cand["low"],
                "close": cand["close"],
                "volume": cand.get("volume", 0),
                "volume_ratio": cand["volume_ratio"],
                "body_percent": cand["formula_details"]["body_percent"],
                "range_percent": cand["formula_details"]["range_percent"],
                "lower_wick_body_ratio": cand["lower_wick_body_ratio"],
                "lower_wick_range_ratio": cand["lower_wick_range_ratio"],
                "open_to_low_percent": cand["formula_details"]["open_to_low_percent"],
                "is_manual": False
            })
        
        print(f"Loaded {len(control_sample)} experimental candidates as control sample")
        return control_sample
        
    except FileNotFoundError:
        print("experimental_candidates_formula3.json not found, searching for new candidates...")
        
        # Fallback: search for recent candidates
        universe = [
            "WLD-USDT", "ONDO-USDT", "TAO-USDT", "ENA-USDT", "WLFI-USDT",
            "INJ-USDT", "XPL-USDT", "FARTCOIN-USDT", "ICP-USDT", "SIREN-USDT",
            "ARB-USDT", "APT-USDT", "ZRO-USDT", "KITE-USDT", "CRV-USDT",
            "WIF-USDT", "PENGU-USDT", "VIRTUAL-USDT", "SEI-USDT", "HOME-USDT",
            "RENDER-USDT", "PENDLE-USDT", "POL-USDT", "OP-USDT", "SUI-USDT",
            "ORDI-USDT", "TIA-USDT", "JTO-USDT", "ALT-USDT", "MEW-USDT",
            "ONE-USDT", "LUNC-USDT", "10000SATS-USDT", "1000BONK-USDT",
            "ARPA-USDT", "BLUR-USDT", "CAKE-USDT", "CELO-USDT",
            "COMP-USDT", "DASH-USDT", "ENS-USDT", "FET-USDT", "FIL-USDT",
            "GALA-USDT", "GLM-USDT", "GRT-USDT", "IMX-USDT",
            "IOTA-USDT", "KAVA-USDT", "LDO-USDT", "MANA-USDT",
            "MASK-USDT", "MINA-USDT", "NMR-USDT",
            "PEOPLE-USDT", "QNT-USDT", "ROSE-USDT", "RUNE-USDT",
            "SAND-USDT", "SNX-USDT", "STG-USDT", "STORJ-USDT", "SUSHI-USDT",
            "THETA-USDT", "TLM-USDT", "WOO-USDT", "YFI-USDT",
            "ZEC-USDT", "ZEN-USDT",
        ]
        
        print(f"Universe size: {len(universe)} coins")
        
        def check_conditions(open_price, high_price, low_price, close_price, current_volume, previous_volume):
            geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
            
            open_to_low_percent = (low_price - open_price) / open_price * 100
            vol_ratio = current_volume / previous_volume if previous_volume > 0 else 0
            lw_range_ratio = geo["lower_wick_range_ratio"]
            lw_body_ratio = geo["lower_wick_body_ratio"]
            range_percent = geo["range_percent"]
            body_percent = geo["body_percent"]
            
            return (
                geo["is_red"] and
                open_to_low_percent <= -2.5 and
                vol_ratio >= 0.75 and
                lw_range_ratio >= 0.40 and
                lw_body_ratio >= 0.75 and
                range_percent >= 2.5 and
                body_percent >= 0.30
            )
        
        control_sample = []
        
        end_time = int(datetime.now(UTC).timestamp() * 1000)
        start_time = int((datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000)
        
        for symbol in universe:
            if len(control_sample) >= limit:
                break
            
            try:
                klines = await fetcher.get_klines(
                    symbol=symbol, 
                    interval="15m", 
                    limit=2000,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not klines or len(klines) < 20:
                    continue
                
                for i in range(len(klines) - 2, max(0, len(klines) - 100), -1):
                    k = klines[i]
                    open_price = float(k['open'])
                    high_price = float(k['high'])
                    low_price = float(k['low'])
                    close_price = float(k['close'])
                    current_volume = float(k['volume'])
                    
                    if i > 0:
                        previous_volume = float(klines[i-1]['volume'])
                    else:
                        previous_volume = 0
                    
                    if check_conditions(open_price, high_price, low_price, close_price, current_volume, previous_volume):
                        geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
                        
                        control_sample.append({
                            "symbol": symbol,
                            "timestamp_ms": int(k['time']),
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": current_volume,
                            "previous_volume": previous_volume,
                            "volume_ratio": current_volume / previous_volume if previous_volume > 0 else 0,
                            "body_percent": geo["body_percent"],
                            "range_percent": geo["range_percent"],
                            "lower_wick_body_ratio": geo["lower_wick_body_ratio"],
                            "lower_wick_range_ratio": geo["lower_wick_range_ratio"],
                            "open_to_low_percent": geo["open_to_low_percent"],
                            "is_manual": False
                        })
                        
                        if len(control_sample) >= limit:
                            break
                
                if len(control_sample) >= limit:
                    break
                    
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        return control_sample


async def analyze_post_signal_performance(fetcher, signals):
    """Analyze post-signal performance for recent signals."""
    
    for signal in signals:
        symbol = signal["symbol"]
        signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
        signal_close = signal["close"]
        
        try:
            # Get klines after signal time
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
                signal["post_signal"] = {"error": "Not enough data"}
                continue
            
            # Find the signal candle
            signal_idx = None
            for i, k in enumerate(klines):
                if abs(int(k['time']) - signal["timestamp_ms"]) < 900000:  # Within 15 minutes
                    signal_idx = i
                    break
            
            if signal_idx is None:
                signal["post_signal"] = {"error": "Signal candle not found"}
                continue
            
            # Analyze performance
            max_up = 0
            max_down = 0
            time_to_1pct = None
            time_to_2pct = None
            time_to_3pct = None
            max_adverse_move = 0
            
            for i in range(signal_idx + 1, len(klines)):
                k = klines[i]
                high = float(k['high'])
                low = float(k['low'])
                
                # Calculate moves from signal close
                up_move = (high - signal_close) / signal_close * 100
                down_move = (low - signal_close) / signal_close * 100
                
                max_up = max(max_up, up_move)
                max_down = min(max_down, down_move)
                max_adverse_move = max(max_adverse_move, abs(down_move))
                
                # Track time to targets
                if time_to_1pct is None and up_move >= 1.0:
                    time_to_1pct = i - signal_idx
                if time_to_2pct is None and up_move >= 2.0:
                    time_to_2pct = i - signal_idx
                if time_to_3pct is None and up_move >= 3.0:
                    time_to_3pct = i - signal_idx
            
            signal["post_signal"] = {
                "max_up_pct": max_up,
                "max_down_pct": max_down,
                "time_to_1pct_candles": time_to_1pct,
                "time_to_2pct_candles": time_to_2pct,
                "time_to_3pct_candles": time_to_3pct,
                "max_adverse_move_pct": max_adverse_move
            }
            
        except Exception as e:
            signal["post_signal"] = {"error": str(e)}


def compare_groups(manual_signals, control_signals):
    """Compare manual signals vs control sample."""
    
    comparison = {
        "manual_count": len(manual_signals),
        "control_count": len(control_signals),
        "metrics": {}
    }
    
    metrics = [
        "body_percent",
        "range_percent", 
        "lower_wick_body_ratio",
        "lower_wick_range_ratio",
        "open_to_low_percent",
        "volume_ratio"
    ]
    
    for metric in metrics:
        manual_values = [s.get(metric, 0) for s in manual_signals if metric in s]
        control_values = [s.get(metric, 0) for s in control_signals if metric in s]
        
        if manual_values and control_values:
            comparison["metrics"][metric] = {
                "manual": {
                    "count": len(manual_values),
                    "mean": mean(manual_values),
                    "median": median(manual_values),
                    "min": min(manual_values),
                    "max": max(manual_values),
                    "stdev": stdev(manual_values) if len(manual_values) > 1 else 0
                },
                "control": {
                    "count": len(control_values),
                    "mean": mean(control_values),
                    "median": median(control_values),
                    "min": min(control_values),
                    "max": max(control_values),
                    "stdev": stdev(control_values) if len(control_values) > 1 else 0
                },
                "difference": {
                    "mean_diff": mean(manual_values) - mean(control_values),
                    "median_diff": median(manual_values) - median(control_values)
                }
            }
    
    return comparison


async def main():
    """Main analysis function."""
    print("=" * 100)
    print("MANUAL SIGNALS VS CONTROL SAMPLE ANALYSIS")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Load manual signals (excluding FF-USDT)
    with open("minimum_candle_size_research.json", "r") as f:
        data = json.load(f)
    
    manual_signals = [s for s in data["signals"] if s["symbol"] != "FF-USDT"]
    
    # Normalize manual signals format
    for s in manual_signals:
        s["volume_ratio"] = s["volume_ratio_prev"]
        s["timestamp_ms"] = s["actual_timestamp_ms"]
    
    print(f"\nLoaded {len(manual_signals)} manual signals (excluding FF-USDT)")
    
    # Find control sample
    fetcher = BingXFetcher()
    print("\nFinding control sample of recent signals...")
    control_signals = await find_control_sample(fetcher, limit=50)
    print(f"Found {len(control_signals)} control signals")
    
    # Analyze post-signal performance for control signals
    print("\nAnalyzing post-signal performance for control signals...")
    await analyze_post_signal_performance(fetcher, control_signals)
    
    # Compare groups
    print("\nComparing manual vs control signals...")
    comparison = compare_groups(manual_signals, control_signals)
    
    # Save results
    results = {
        "manual_signals": manual_signals,
        "control_signals": control_signals,
        "comparison": comparison
    }
    
    with open("manual_vs_control_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'=' * 100}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 100}")
    
    for metric, data in comparison["metrics"].items():
        print(f"\n{metric}:")
        print(f"  Manual:   mean={data['manual']['mean']:.4f}, median={data['manual']['median']:.4f}")
        print(f"  Control:  mean={data['control']['mean']:.4f}, median={data['control']['median']:.4f}")
        print(f"  Diff:     mean={data['difference']['mean_diff']:.4f}, median={data['difference']['median_diff']:.4f}")
    
    # Post-signal performance summary
    print(f"\n{'=' * 100}")
    print("POST-SIGNAL PERFORMANCE (CONTROL SAMPLE)")
    print(f"{'=' * 100}")
    
    perf_data = [s["post_signal"] for s in control_signals if "post_signal" in s and "error" not in s["post_signal"]]
    
    if perf_data:
        max_ups = [p["max_up_pct"] for p in perf_data]
        max_downs = [p["max_down_pct"] for p in perf_data]
        adverse_moves = [p["max_adverse_move_pct"] for p in perf_data]
        
        print(f"\nMax Up:   mean={mean(max_ups):.2f}%, median={median(max_ups):.2f}%")
        print(f"Max Down: mean={mean(max_downs):.2f}%, median={median(max_downs):.2f}%")
        print(f"Max Adverse: mean={mean(adverse_moves):.2f}%, median={median(adverse_moves):.2f}%")
        
        time_to_2pct = [p["time_to_2pct_candles"] for p in perf_data if p["time_to_2pct_candles"] is not None]
        if time_to_2pct:
            print(f"Time to +2%: mean={mean(time_to_2pct):.1f} candles, median={median(time_to_2pct):.1f} candles")
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to manual_vs_control_analysis.json")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
