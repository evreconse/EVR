#!/usr/bin/env python3
"""
Critical Audit: Debug Historical Data Fetching for LW-001

This script investigates why only 5 signals were found over 60 days,
all on the same day (22.08.2026), and why SAND-USDT appears to be incorrect.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta
from collections import defaultdict

# Test symbols (5 different coins from Top-21-250)
TEST_SYMBOLS = ["SAND-USDT", "FET-USDT", "TRX-USDT", "ZEC-USDT", "ICP-USDT"]

# MODERATE_1 thresholds
MODERATE1_THRESHOLDS = {
    "range_pct": 4.0,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 55.0,
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}


def format_timestamp_utc3(timestamp_ms):
    """Convert raw candle timestamp to UTC+3 format."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, UTC)
    dt_utc3 = dt_utc + timedelta(hours=3)
    utc3_str = dt_utc3.strftime("%d.%m.%Y %H:%M UTC+3")
    return utc3_str


def format_timestamp_utc(timestamp_ms):
    """Convert raw candle timestamp to UTC format."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, UTC)
    utc_str = dt_utc.strftime("%d.%m.%Y %H:%M UTC")
    return utc_str


def count_candles_by_month(candles):
    """Count candles by month."""
    counts = defaultdict(int)
    for candle in candles:
        timestamp = candle.get('time', candle.get('timestamp', 0))
        dt = datetime.fromtimestamp(timestamp / 1000, UTC)
        month_key = dt.strftime("%Y-%m")
        counts[month_key] += 1
    return counts


async def fetch_historical_candles_detailed(symbol: str, days: int = 60):
    """Fetch historical candles with detailed logging."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    print(f"\n{'='*100}")
    print(f"Symbol: {symbol}")
    print(f"{'='*100}")
    print(f"Requested range:")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (timestamp: {int(start_time.timestamp() * 1000)})")
    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (timestamp: {int(end_time.timestamp() * 1000)})")
    print(f"  Duration: {days} days")
    print()
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles:
            print("ERROR: No candles returned")
            return []
        
        print(f"Actual returned range:")
        first_timestamp = candles[0].get('time', candles[0].get('timestamp', 0))
        last_timestamp = candles[-1].get('time', candles[-1].get('timestamp', 0))
        
        print(f"  First candle: {format_timestamp_utc(first_timestamp)} ({format_timestamp_utc3(first_timestamp)})")
        print(f"  Last candle: {format_timestamp_utc(last_timestamp)} ({format_timestamp_utc3(last_timestamp)})")
        print(f"  Total candles: {len(candles)}")
        print()
        
        # Count by month
        monthly_counts = count_candles_by_month(candles)
        print(f"Candles by month:")
        for month in sorted(monthly_counts.keys()):
            print(f"  {month}: {monthly_counts[month]} candles")
        print()
        
        return candles
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []


def calculate_avg_volume_20(candles, index):
    """Calculate average volume of previous 20 candles."""
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


def check_thresholds(metrics, thresholds):
    """Check if metrics pass all thresholds."""
    return (
        metrics.range_pct >= thresholds["range_pct"] and
        metrics.body_pct >= thresholds["body_pct"] and
        metrics.lower_wick_body_ratio >= thresholds["lw_body_ratio"] and
        metrics.lower_wick_range_pct >= thresholds["lw_range_pct"] and
        metrics.open_to_low_pct <= thresholds["open_low_pct"] and
        metrics.volume_ratio >= thresholds["volume_ratio"]
    )


def analyze_candle_details(candle, symbol):
    """Analyze a single candle in detail."""
    timestamp = candle.get('time', candle.get('timestamp', 0))
    open_price = float(candle.get('open', 0))
    high_price = float(candle.get('high', 0))
    low_price = float(candle.get('low', 0))
    close_price = float(candle.get('close', 0))
    volume = float(candle.get('volume', candle.get('vol', 0)))
    
    print(f"\n{'='*100}")
    print(f"DETAILED CANDLE ANALYSIS: {symbol}")
    print(f"{'='*100}")
    print(f"Raw exchange timestamp: {timestamp}")
    print(f"Raw timestamp unit: milliseconds since Unix epoch")
    print(f"UTC datetime: {format_timestamp_utc(timestamp)}")
    print(f"UTC+3 datetime: {format_timestamp_utc3(timestamp)}")
    print()
    print(f"OHLCV:")
    print(f"  Open: {open_price:.6f}")
    print(f"  High: {high_price:.6f}")
    print(f"  Low: {low_price:.6f}")
    print(f"  Close: {close_price:.6f}")
    print(f"  Volume: {volume:.2f}")
    print()
    print(f"Candle direction:")
    if close_price > open_price:
        print(f"  GREEN (Close > Open)")
        print(f"  Body: {close_price - open_price:.6f} (+{abs(close_price - open_price)/open_price*100:.2f}%)")
    elif close_price < open_price:
        print(f"  RED (Close < Open)")
        print(f"  Body: {close_price - open_price:.6f} ({abs(close_price - open_price)/open_price*100:.2f}%)")
    else:
        print(f"  DOJI (Close == Open)")
    print()
    print(f"Lower Wick:")
    lower_wick = min(open_price, close_price) - low_price
    print(f"  Size: {lower_wick:.6f}")
    print(f"  % of Open: {lower_wick/open_price*100:.2f}%")
    print()


async def main():
    """Main audit function."""
    print("="*100)
    print("CRITICAL AUDIT: LW-001 HISTORICAL DATA FETCHING")
    print("="*100)
    print()
    print("Testing 5 symbols for full 60-day range")
    print()
    
    # Test each symbol
    for symbol in TEST_SYMBOLS:
        candles = await fetch_historical_candles_detailed(symbol, days=60)
        
        if not candles:
            continue
        
        # Analyze funnel for this symbol
        print(f"Funnel analysis for {symbol}:")
        funnel = {
            'total': len(candles),
            'pass_range': 0,
            'pass_body': 0,
            'pass_lw_body': 0,
            'pass_lw_range': 0,
            'pass_open_low': 0,
            'pass_volume': 0,
            'pass_all': 0
        }
        
        signals = []
        
        for j in range(len(candles)):
            try:
                from LW001_METRIC_SPEC import calculate_all_metrics
                
                open_price = float(candles[j].get('open', 0))
                high_price = float(candles[j].get('high', 0))
                low_price = float(candles[j].get('low', 0))
                close_price = float(candles[j].get('close', 0))
                volume = float(candles[j].get('volume', candles[j].get('vol', 0)))
                timestamp = candles[j].get('time', candles[j].get('timestamp', 0))
                
                if open_price <= 0:
                    continue
                
                avg_volume_20 = calculate_avg_volume_20(candles, j)
                
                metrics = calculate_all_metrics(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    reference_average_volume=avg_volume_20
                )
                
                if metrics.range_pct >= MODERATE1_THRESHOLDS['range_pct']:
                    funnel['pass_range'] += 1
                if metrics.body_pct >= MODERATE1_THRESHOLDS['body_pct']:
                    funnel['pass_body'] += 1
                if metrics.lower_wick_body_ratio >= MODERATE1_THRESHOLDS['lw_body_ratio']:
                    funnel['pass_lw_body'] += 1
                if metrics.lower_wick_range_pct >= MODERATE1_THRESHOLDS['lw_range_pct']:
                    funnel['pass_lw_range'] += 1
                if metrics.open_to_low_pct <= MODERATE1_THRESHOLDS['open_low_pct']:
                    funnel['pass_open_low'] += 1
                if metrics.volume_ratio >= MODERATE1_THRESHOLDS['volume_ratio']:
                    funnel['pass_volume'] += 1
                
                if check_thresholds(metrics, MODERATE1_THRESHOLDS):
                    funnel['pass_all'] += 1
                    signals.append({
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'metrics': metrics
                    })
            except Exception as e:
                continue
        
        print(f"  Total candles: {funnel['total']}")
        print(f"  Pass Range >= 4.0%: {funnel['pass_range']} ({funnel['pass_range']/funnel['total']*100:.2f}%)")
        print(f"  Pass Body >= 0.8%: {funnel['pass_body']} ({funnel['pass_body']/funnel['total']*100:.2f}%)")
        print(f"  Pass LW/Body >= 1.3x: {funnel['pass_lw_body']} ({funnel['pass_lw_body']/funnel['total']*100:.2f}%)")
        print(f"  Pass LW/Range >= 55%: {funnel['pass_lw_range']} ({funnel['pass_lw_range']/funnel['total']*100:.2f}%)")
        print(f"  Pass Open->Low <= -2.5%: {funnel['pass_open_low']} ({funnel['pass_open_low']/funnel['total']*100:.2f}%)")
        print(f"  Pass Volume Ratio >= 1.5x: {funnel['pass_volume']} ({funnel['pass_volume']/funnel['total']*100:.2f}%)")
        print(f"  Pass ALL 6 conditions: {funnel['pass_all']} ({funnel['pass_all']/funnel['total']*100:.4f}%)")
        print()
        
        # Show signal dates
        if signals:
            print(f"Signals found ({len(signals)}):")
            for sig in signals:
                print(f"  {format_timestamp_utc(sig['timestamp'])} ({format_timestamp_utc3(sig['timestamp'])})")
            
            # Detailed analysis of first signal
            if signals:
                first_sig = signals[0]
                first_candle = None
                for candle in candles:
                    if candle.get('time', candle.get('timestamp', 0)) == first_sig['timestamp']:
                        first_candle = candle
                        break
                if first_candle:
                    analyze_candle_details(first_candle, symbol)
        else:
            print("No signals found")
        
        print()
    
    print("="*100)
    print("AUDIT COMPLETE")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(main())
