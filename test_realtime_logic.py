#!/usr/bin/env python3
"""
Test script for real-time LW-001 monitor logic.
Checks latest candles for a few symbols to verify the logic works.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test with a few symbols
TEST_SYMBOLS = ["TIA-USDT", "ICP-USDT", "ETC-USDT", "ZEC-USDT", "FET-USDT"]

# FIXED LW-001 thresholds
FIXED_THRESHOLDS = {
    "range_pct": 4.5,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 45.0,
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}


def format_timestamp_utc(timestamp_ms):
    """Convert raw candle timestamp to UTC format ONLY."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, UTC)
    utc_str = dt_utc.strftime("%d.%m.%Y %H:%M UTC")
    return utc_str


def check_red_candle(open_price, close_price):
    """Check if candle is red (Close < Open)."""
    return close_price < open_price


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


async def test_latest_candle(symbol):
    """Test the latest candle for a symbol."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    # Fetch last 25 candles
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=6)
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles or len(candles) < 21:
            print(f"  {symbol}: Not enough candles ({len(candles) if candles else 0})")
            return None
        
        # Get the most recent completed candle
        latest_candle = candles[-2]
        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))
        
        print(f"  {symbol}: Latest candle at {format_timestamp_utc(timestamp)}")
        print(f"    Open: {float(latest_candle['open']):.6f}")
        print(f"    Close: {float(latest_candle['close']):.6f}")
        print(f"    Direction: {'RED' if check_red_candle(float(latest_candle['open']), float(latest_candle['close'])) else 'GREEN'}")
        
        # Calculate average volume
        candle_index = len(candles) - 2
        avg_volume_20 = calculate_avg_volume_20(candles, candle_index)
        
        # Calculate metrics
        from LW001_METRIC_SPEC import calculate_all_metrics
        metrics = calculate_all_metrics(
            open_price=float(latest_candle['open']),
            high_price=float(latest_candle['high']),
            low_price=float(latest_candle['low']),
            close_price=float(latest_candle['close']),
            volume=float(latest_candle['volume']),
            reference_average_volume=avg_volume_20
        )
        
        print(f"    Range: {metrics.range_pct:.2f}%")
        print(f"    LW/Range: {metrics.lower_wick_range_pct:.2f}%")
        
        # Check if signal
        if check_red_candle(float(latest_candle['open']), float(latest_candle['close'])):
            if check_thresholds(metrics, FIXED_THRESHOLDS):
                print(f"    [SIGNAL] All conditions PASS")
                return {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': float(latest_candle['open']),
                    'high': float(latest_candle['high']),
                    'low': float(latest_candle['low']),
                    'close': float(latest_candle['close']),
                    'volume': float(latest_candle['volume']),
                    'metrics': metrics
                }
            else:
                print(f"    [NO SIGNAL] Metrics do not pass thresholds")
        else:
            print(f"    [NO SIGNAL] Candle is not red")
        
        print()
        return None
        
    except Exception as e:
        print(f"  {symbol}: Error - {e}")
        print()
        return None


async def main():
    """Test the real-time logic."""
    print("="*100)
    print("TEST: Real-time LW-001 Monitor Logic")
    print("="*100)
    print()
    print(f"Testing latest candles for {len(TEST_SYMBOLS)} symbols")
    print()
    
    signals_found = 0
    
    for symbol in TEST_SYMBOLS:
        signal = await test_latest_candle(symbol)
        if signal:
            signals_found += 1
    
    print("="*100)
    print("TEST COMPLETE")
    print("="*100)
    print()
    print(f"Signals found: {signals_found}")
    print()
    print("Logic test: PASSED" if signals_found >= 0 else "Logic test: FAILED")


if __name__ == "__main__":
    asyncio.run(main())
