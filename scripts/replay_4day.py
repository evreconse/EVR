#!/usr/bin/env python3
"""
4-Day Offline Replay for LW-001 Signal Detection
"""
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.data_provider.universe_provider import get_universe_provider
from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import calculate_all_metrics

FIXED_THRESHOLDS = {
    "range_pct": 4.5,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 55.0,
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}

THRESHOLD_ORDER = [
    ("range_pct", "Range >= 4.5%"),
    ("body_pct", "Body >= 0.8%"),
    ("lw_body_ratio", "LW/Body >= 1.3x"),
    ("lw_range_pct", "LW/Range >= 55%"),
    ("open_low_pct", "Open->Low <= -2.5%"),
    ("volume_ratio", "Volume Ratio >= 1.5x"),
]

def check_red_candle(open_price, close_price):
    return close_price < open_price

def check_thresholds(metrics, thresholds):
    results = {}
    results["range_pct"] = metrics.range_pct >= thresholds["range_pct"]
    results["body_pct"] = metrics.body_pct >= thresholds["body_pct"]
    results["lw_body_ratio"] = metrics.lower_wick_body_ratio >= thresholds["lw_body_ratio"]
    results["lw_range_pct"] = metrics.lower_wick_range_pct >= thresholds["lw_range_pct"]
    results["open_low_pct"] = metrics.open_to_low_pct <= thresholds["open_low_pct"]
    results["volume_ratio"] = metrics.volume_ratio >= thresholds["volume_ratio"]
    passed = all(results.values())
    return passed, results

def calculate_avg_volume_20(candles, index):
    start_idx = max(0, index - 20)
    if start_idx >= index:
        return 1.0
    volumes = []
    for i in range(start_idx, index):
        vol = float(candles[i].get('volume', candles[i].get('vol', 0)))
        volumes.append(vol)
    if not volumes:
        return 1.0
    return sum(volumes) / len(volumes)

def format_timestamp_utc(timestamp_ms):
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, timezone.utc)
    return dt_utc.strftime("%d.%m.%Y %H:%M UTC")

async def replay_4day():
    print("="*80)
    print("LW-001 4-DAY REPLAY")
    print("="*80)
    
    # Get universe
    provider = get_universe_provider()
    await provider.initialize()
    universe = await provider.get_universe()
    print(f"Universe: {len(universe)} symbols (current dynamic CMC 20-250 + BingX)")
    print()
    
    fetcher = BingXFetcher()
    
    # 4 days = 96 hours = 384 15m candles
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=4)
    
    print(f"Period: {start_time.strftime('%Y-%m-%d %H:%M UTC')} to {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print()
    
    # Sequential funnel counters
    funnel_counts = {k: 0 for k in FIXED_THRESHOLDS.keys()}
    funnel_counts["total_candles"] = 0
    funnel_counts["red_candles"] = 0
    
    # Independent condition counts
    independent_counts = {k: 0 for k in FIXED_THRESHOLDS.keys()}
    independent_counts["total_candles"] = 0
    independent_counts["red_candles"] = 0
    
    near_misses = []
    valid_signals = []
    
    for symbol in universe:
        try:
            candles = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                start_time=int(start_time.timestamp() * 1000),
                end_time=int(end_time.timestamp() * 1000)
            )
            
            if not candles or len(candles) < 22:
                continue
            
            # Check each completed candle (skip the last one which might be incomplete)
            for i in range(20, len(candles) - 1):
                candle = candles[i]
                funnel_counts["total_candles"] += 1
                independent_counts["total_candles"] += 1
                
                open_price = float(candle['open'])
                high_price = float(candle['high'])
                low_price = float(candle['low'])
                close_price = float(candle['close'])
                volume = float(candle['volume'])
                timestamp = candle.get('time', candle.get('timestamp', 0))
                
                if timestamp <= 0:
                    continue
                
                # Check if red candle
                is_red = check_red_candle(open_price, close_price)
                if not is_red:
                    continue
                
                funnel_counts["red_candles"] += 1
                independent_counts["red_candles"] += 1
                
                # Calculate average volume from previous 20 candles
                avg_volume_20 = calculate_avg_volume_20(candles, i)
                
                # Calculate metrics
                metrics = calculate_all_metrics(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    reference_average_volume=avg_volume_20
                )
                
                # Check thresholds
                passed, results = check_thresholds(metrics, FIXED_THRESHOLDS)
                
                # INDEPENDENT CONDITION COUNTS (each condition checked independently)
                for k, v in results.items():
                    if v:
                        independent_counts[k] += 1
                
                # SEQUENTIAL FUNNEL (each stage filters the previous)
                # Start with all red candles
                sequential_candidates = 1
                for k, label in THRESHOLD_ORDER:
                    if results[k]:
                        funnel_counts[k] += 1
                        sequential_candidates += 0
                    else:
                        sequential_candidates = 0
                        break
                
                # Track near misses (4+ conditions pass)
                pass_count = sum(1 for v in results.values() if v)
                if pass_count >= 4:
                    near_misses.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'pass_count': pass_count,
                        'metrics': metrics,
                        'results': results,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
                
                if passed:
                    valid_signals.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'metrics': metrics,
                        'results': results,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
                    
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    # Print SEQUENTIAL FUNNEL
    print("="*80)
    print("SEQUENTIAL FUNNEL (each stage filters previous)")
    print("="*80)
    prev = funnel_counts["red_candles"]
    print(f"Total candles checked:      {funnel_counts['total_candles']}")
    print(f"Red candles (Close < Open): {funnel_counts['red_candles']} (100.0%)")
    for k, label in THRESHOLD_ORDER:
        count = funnel_counts[k]
        pct = (count / prev * 100) if prev > 0 else 0
        print(f"  {label:25s}: {count:6d} ({pct:5.1f}% of prev)")
        prev = count
    print(f"ALL 6 CONDITIONS PASS:      {prev:6d} ({(prev/funnel_counts['red_candles']*100) if funnel_counts['red_candles'] > 0 else 0:5.1f}% of red)")
    print()
    
    # Print INDEPENDENT CONDITION COUNTS
    print("="*80)
    print("INDEPENDENT CONDITION COUNTS (each condition vs all red candles)")
    print("="*80)
    red = independent_counts["red_candles"]
    for k, label in THRESHOLD_ORDER:
        count = independent_counts[k]
        pct = (count / red * 100) if red > 0 else 0
        print(f"  {label:25s}: {count:6d} ({pct:5.1f}% of red)")
    print()
    
    # Print valid signals
    if valid_signals:
        print("="*80)
        print(f"VALID LW-001 SIGNALS FOUND ({len(valid_signals)})")
        print("="*80)
        for sig in valid_signals:
            m = sig['metrics']
            r = sig['results']
            print(f"\n{sig['symbol']} @ {format_timestamp_utc(sig['timestamp'])}")
            print(f"  OHLCV: O={sig['open']:.6f} H={sig['high']:.6f} L={sig['low']:.6f} C={sig['close']:.6f} V={sig['volume']:.2f}")
            print(f"  Range={m.range_pct:.2f}% Body={m.body_pct:.2f}% LW/Body={m.lower_wick_body_ratio:.2f}x LW/Range={m.lower_wick_range_pct:.2f}% Open->Low={m.open_to_low_pct:.2f}% VolRatio={m.volume_ratio:.2f}x")
            for k, label in THRESHOLD_ORDER:
                status = "PASS" if r[k] else "FAIL"
                print(f"    {label}: {status}")
    else:
        print("NO VALID LW-001 SIGNALS FOUND IN 4 DAYS")
    
    # Print near misses
    if near_misses:
        print("\n" + "="*80)
        print(f"NEAR MISSES ({len(near_misses)} candles with 4+ conditions passing)")
        print("="*80)
        # Sort by pass count descending
        near_misses.sort(key=lambda x: x['pass_count'], reverse=True)
        for nm in near_misses[:30]:
            m = nm['metrics']
            r = nm['results']
            status = " ".join([f"{k}:{'PASS' if v else 'FAIL'}" for k, v in r.items()])
            print(f"{nm['symbol']} @ {format_timestamp_utc(nm['timestamp'])} [{nm['pass_count']}/6] {status}")
            print(f"  O={nm['open']:.6f} H={nm['high']:.6f} L={nm['low']:.6f} C={nm['close']:.6f} V={nm['volume']:.2f}")
            print(f"  Range={m.range_pct:.2f}% Body={m.body_pct:.2f}% LW/Body={m.lower_wick_body_ratio:.2f}x LW/Range={m.lower_wick_range_pct:.2f}% Open->Low={m.open_to_low_pct:.2f}% VolRatio={m.volume_ratio:.2f}x")
    
    print("\n" + "="*80)
    print("REPLAY COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(replay_4day())