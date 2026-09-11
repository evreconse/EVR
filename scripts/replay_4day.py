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
    print(f"Universe: {len(universe)} symbols")
    print()
    
    fetcher = BingXFetcher()
    
    # 4 days = 96 hours = 384 15m candles
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=4)
    
    print(f"Period: {start_time.strftime('%Y-%m-%d %H:%M UTC')} to {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print()
    
    total_candles_checked = 0
    total_red_candles = 0
    total_passed = 0
    condition_passes = {k: 0 for k in FIXED_THRESHOLDS.keys()}
    near_misses = []
    valid_signals = []
    
    for symbol in universe[:50]:  # Limit to first 50 for speed
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
                total_candles_checked += 1
                
                open_price = float(candle['open'])
                high_price = float(candle['high'])
                low_price = float(candle['low'])
                close_price = float(candle['close'])
                volume = float(candle['volume'])
                timestamp = candle.get('time', candle.get('timestamp', 0))
                
                if timestamp <= 0:
                    continue
                
                # Check if red candle
                if not check_red_candle(open_price, close_price):
                    continue
                
                total_red_candles += 1
                
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
                
                # Track condition passes
                for k, v in results.items():
                    if v:
                        condition_passes[k] += 1
                
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
                    total_passed += 1
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
    
    # Print funnel
    print("="*80)
    print("FUNNEL ANALYSIS")
    print("="*80)
    print(f"Total candles checked:      {total_candles_checked}")
    print(f"Red candles:                {total_red_candles}")
    for k, v in condition_passes.items():
        print(f"  {k:20s} >= threshold: {v}")
    print(f"ALL 6 CONDITIONS PASS:      {total_passed}")
    print()
    
    # Print valid signals
    if valid_signals:
        print("="*80)
        print("VALID LW-001 SIGNALS FOUND")
        print("="*80)
        for sig in valid_signals:
            m = sig['metrics']
            print(f"\n{sig['symbol']} @ {format_timestamp_utc(sig['timestamp'])}")
            print(f"  O={sig['open']:.6f} H={sig['high']:.6f} L={sig['low']:.6f} C={sig['close']:.6f} V={sig['volume']:.2f}")
            print(f"  Range={m.range_pct:.2f}% Body={m.body_pct:.2f}% LW/Body={m.lower_wick_body_ratio:.2f}x LW/Range={m.lower_wick_range_pct:.2f}% Open->Low={m.open_to_low_pct:.2f}% VolRatio={m.volume_ratio:.2f}x")
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