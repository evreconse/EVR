#!/usr/bin/env python3
"""
Historical Candle Verification for LW-001.

This script fetches 5-10 historical candles and performs full canonical recalculation
with detailed step-by-step verification of all metric calculations and condition checks.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import UTC, datetime, timedelta
from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    check_all_conditions,
    LW001Metrics,
    LW001_THRESHOLDS,
    calculate_range_pct,
    calculate_body_pct,
    calculate_lower_wick_body_ratio,
    calculate_lower_wick_range_pct,
    calculate_open_to_low_pct,
    calculate_volume_ratio
)


async def fetch_test_candles(symbol: str = "BTC-USDT", count: int = 10):
    """Fetch historical candles for verification."""
    print("=" * 100)
    print(f"FETCHING {count} HISTORICAL CANDLES FOR {symbol}")
    print("=" * 100)
    
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=count * 0.25)  # 15m candles
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    candles = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        start_time=start_ms,
        end_time=end_ms,
        limit=count
    )
    
    print(f"Fetched {len(candles)} candles\n")
    return candles


def calculate_avg_volume_20(candles: list, index: int) -> float:
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    volumes = [float(candles[i]['volume']) for i in range(start_idx, index)]
    return sum(volumes) / len(volumes) if volumes else 1.0


def verify_single_candle(candle: dict, avg_volume_20: float, index: int):
    """Verify a single candle with full detailed calculation."""
    print("=" * 100)
    print(f"CANDLE {index + 1} FULL VERIFICATION")
    print("=" * 100)
    
    open_price = float(candle['open'])
    high_price = float(candle['high'])
    low_price = float(candle['low'])
    close_price = float(candle['close'])
    volume = float(candle['volume'])
    
    print(f"\nOHLCV Data:")
    print(f"  Open:   {open_price:.6f}")
    print(f"  High:   {high_price:.6f}")
    print(f"  Low:    {low_price:.6f}")
    print(f"  Close:  {close_price:.6f}")
    print(f"  Volume: {volume:.2f}")
    print(f"  Avg Vol (20): {avg_volume_20:.2f}")
    
    print(f"\n--- STEP-BY-STEP METRIC CALCULATIONS ---")
    
    # Step 1: Range calculation
    candle_range = high_price - low_price
    range_pct = calculate_range_pct(open_price, high_price, low_price)
    print(f"\n1. Range %:")
    print(f"   Formula: ((High - Low) / Open) * 100")
    print(f"   Calculation: ({high_price:.6f} - {low_price:.6f}) / {open_price:.6f} * 100")
    print(f"   Result: {candle_range:.6f} / {open_price:.6f} * 100 = {range_pct:.4f}%")
    print(f"   Threshold: {LW001_THRESHOLDS['range_pct']['value']}%")
    print(f"   Status: {'PASS' if range_pct >= LW001_THRESHOLDS['range_pct']['value'] else 'FAIL'}")
    
    # Step 2: Body calculation
    body_pct = calculate_body_pct(open_price, close_price)
    print(f"\n2. Body %:")
    print(f"   Formula: (abs(Close - Open) / Open) * 100")
    print(f"   Calculation: abs({close_price:.6f} - {open_price:.6f}) / {open_price:.6f} * 100")
    print(f"   Result: {abs(close_price - open_price):.6f} / {open_price:.6f} * 100 = {body_pct:.4f}%")
    print(f"   Threshold: {LW001_THRESHOLDS['body_pct']['value']}%")
    print(f"   Status: {'PASS' if body_pct >= LW001_THRESHOLDS['body_pct']['value'] else 'FAIL'}")
    
    # Step 3: Lower Wick calculation
    lower_wick = min(open_price, close_price) - low_price
    print(f"\n3. Lower Wick (price):")
    print(f"   Formula: min(Open, Close) - Low")
    print(f"   Calculation: min({open_price:.6f}, {close_price:.6f}) - {low_price:.6f}")
    print(f"   Result: {min(open_price, close_price):.6f} - {low_price:.6f} = {lower_wick:.6f}")
    
    # Step 4: LW/Body calculation
    lw_body_ratio = calculate_lower_wick_body_ratio(open_price, close_price, low_price)
    print(f"\n4. LW/Body Ratio:")
    print(f"   Formula: Lower Wick / abs(Close - Open)")
    print(f"   Calculation: {lower_wick:.6f} / {abs(close_price - open_price):.6f}")
    print(f"   Result: {lw_body_ratio:.4f}x")
    print(f"   Threshold: {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x")
    print(f"   Status: {'PASS' if lw_body_ratio >= LW001_THRESHOLDS['lower_wick_body_ratio']['value'] else 'FAIL'}")
    
    # Step 5: LW/Range calculation
    lw_range_pct = calculate_lower_wick_range_pct(open_price, high_price, low_price, close_price)
    print(f"\n5. LW/Range %:")
    print(f"   Formula: (Lower Wick / (High - Low)) * 100")
    print(f"   Calculation: ({lower_wick:.6f} / {candle_range:.6f}) * 100")
    print(f"   Result: {lw_range_pct:.4f}%")
    print(f"   Threshold: {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%")
    print(f"   Status: {'PASS' if lw_range_pct >= LW001_THRESHOLDS['lower_wick_range_pct']['value'] else 'FAIL'}")
    
    # Step 6: Open->Low calculation
    open_to_low_pct = calculate_open_to_low_pct(open_price, low_price)
    print(f"\n6. Open->Low %:")
    print(f"   Formula: ((Low - Open) / Open) * 100")
    print(f"   Calculation: ({low_price:.6f} - {open_price:.6f}) / {open_price:.6f} * 100")
    print(f"   Result: {open_to_low_pct:.4f}%")
    print(f"   Threshold: {LW001_THRESHOLDS['open_to_low_pct']['value']}%")
    print(f"   Status: {'PASS' if open_to_low_pct <= LW001_THRESHOLDS['open_to_low_pct']['value'] else 'FAIL'}")
    
    # Step 7: Volume Ratio calculation
    volume_ratio = calculate_volume_ratio(volume, avg_volume_20)
    print(f"\n7. Volume Ratio:")
    print(f"   Formula: Candle Volume / Average Volume (20)")
    print(f"   Calculation: {volume:.2f} / {avg_volume_20:.2f}")
    print(f"   Result: {volume_ratio:.4f}x")
    print(f"   Threshold: {LW001_THRESHOLDS['volume_ratio']['value']}x")
    print(f"   Status: {'PASS' if volume_ratio >= LW001_THRESHOLDS['volume_ratio']['value'] else 'FAIL'}")
    
    # Step 8: Canonical calculation verification
    print(f"\n--- CANONICAL CALCULATION VERIFICATION ---")
    canonical_metrics = calculate_all_metrics(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        reference_average_volume=avg_volume_20
    )
    
    print(f"\nCanonical Metrics:")
    print(f"  Range: {canonical_metrics.range_pct:.4f}% (manual: {range_pct:.4f}%) - Match: {abs(canonical_metrics.range_pct - range_pct) < 0.0001}")
    print(f"  Body: {canonical_metrics.body_pct:.4f}% (manual: {body_pct:.4f}%) - Match: {abs(canonical_metrics.body_pct - body_pct) < 0.0001}")
    print(f"  LW/Body: {canonical_metrics.lower_wick_body_ratio:.4f}x (manual: {lw_body_ratio:.4f}x) - Match: {abs(canonical_metrics.lower_wick_body_ratio - lw_body_ratio) < 0.0001}")
    print(f"  LW/Range: {canonical_metrics.lower_wick_range_pct:.4f}% (manual: {lw_range_pct:.4f}%) - Match: {abs(canonical_metrics.lower_wick_range_pct - lw_range_pct) < 0.0001}")
    print(f"  Open->Low: {canonical_metrics.open_to_low_pct:.4f}% (manual: {open_to_low_pct:.4f}%) - Match: {abs(canonical_metrics.open_to_low_pct - open_to_low_pct) < 0.0001}")
    print(f"  Volume Ratio: {canonical_metrics.volume_ratio:.4f}x (manual: {volume_ratio:.4f}x) - Match: {abs(canonical_metrics.volume_ratio - volume_ratio) < 0.0001}")
    
    # Step 9: Condition check verification
    print(f"\n--- CONDITION CHECK VERIFICATION ---")
    passed, failures = check_all_conditions(canonical_metrics)
    
    print(f"\nAND Logic Check (all 6 conditions must PASS):")
    print(f"  1. Range >= {LW001_THRESHOLDS['range_pct']['value']}%: {'PASS' if canonical_metrics.range_pct >= LW001_THRESHOLDS['range_pct']['value'] else 'FAIL'}")
    print(f"  2. Body >= {LW001_THRESHOLDS['body_pct']['value']}%: {'PASS' if canonical_metrics.body_pct >= LW001_THRESHOLDS['body_pct']['value'] else 'FAIL'}")
    print(f"  3. LW/Body >= {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x: {'PASS' if canonical_metrics.lower_wick_body_ratio >= LW001_THRESHOLDS['lower_wick_body_ratio']['value'] else 'FAIL'}")
    print(f"  4. LW/Range >= {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%: {'PASS' if canonical_metrics.lower_wick_range_pct >= LW001_THRESHOLDS['lower_wick_range_pct']['value'] else 'FAIL'}")
    print(f"  5. Open->Low <= {LW001_THRESHOLDS['open_to_low_pct']['value']}%: {'PASS' if canonical_metrics.open_to_low_pct <= LW001_THRESHOLDS['open_to_low_pct']['value'] else 'FAIL'}")
    print(f"  6. Volume Ratio >= {LW001_THRESHOLDS['volume_ratio']['value']}x: {'PASS' if canonical_metrics.volume_ratio >= LW001_THRESHOLDS['volume_ratio']['value'] else 'FAIL'}")
    
    print(f"\nFinal Result: {'PASS' if passed else 'FAIL'}")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    
    return passed


async def run_historical_verification():
    """Run full historical candle verification."""
    candles = await fetch_test_candles(symbol="BTC-USDT", count=10)
    
    if len(candles) < 5:
        print("ERROR: Need at least 5 candles for verification")
        return
    
    results = []
    
    for i in range(min(10, len(candles))):
        avg_volume_20 = calculate_avg_volume_20(candles, i)
        passed = verify_single_candle(candles[i], avg_volume_20, i)
        results.append(passed)
    
    # Summary
    print("\n" + "=" * 100)
    print("HISTORICAL CANDLE VERIFICATION SUMMARY")
    print("=" * 100)
    
    passed_count = sum(results)
    total_count = len(results)
    
    print(f"\nCandles verified: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_count - passed_count}")
    
    if passed_count == total_count:
        print("\n[PASS] All historical candle calculations verified successfully")
    else:
        print(f"\n[INFO] {total_count - passed_count} candle(s) did not meet LW-001 conditions (expected)")


if __name__ == "__main__":
    asyncio.run(run_historical_verification())
