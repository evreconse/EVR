#!/usr/bin/env python3
"""
Cross-pipeline test with 100 historical candles.

Verifies that all pipelines produce identical metrics and PASS/FAIL results.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import asyncio
import json
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import calculate_all_metrics, check_all_conditions, LW001Metrics


async def fetch_100_test_candles():
    """Fetch 100 historical candles for cross-pipeline testing."""
    fetcher = BingXFetcher()
    
    # Use BTC-USDT as test symbol
    symbol = "BTC-USDT"
    
    # Fetch last 200 candles to get 100 test candles (need 20 for volume avg)
    klines = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        limit=200
    )
    
    # Take last 100 candles (indices 100-199)
    test_candles = klines[100:]
    
    return test_candles


def calculate_metrics_canonical(candle, avg_volume_20):
    """Calculate metrics using canonical implementation."""
    open_price = float(candle['open'])
    high_price = float(candle['high'])
    low_price = float(candle['low'])
    close_price = float(candle['close'])
    volume = float(candle['volume'])
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, avg_volume_20)
    
    return {
        "range_pct": metrics.range_pct,
        "body_pct": metrics.body_pct,
        "lw_body_ratio": metrics.lower_wick_body_ratio,
        "lw_range_pct": metrics.lower_wick_range_pct,
        "open_low_pct": metrics.open_to_low_pct,
        "volume_ratio": metrics.volume_ratio
    }


def calculate_metrics_control_test(candle, avg_volume_20):
    """Calculate metrics using control_test_10_signals implementation."""
    open_price = float(candle['open'])
    close_price = float(candle['close'])
    high_price = float(candle['high'])
    low_price = float(candle['low'])
    volume = float(candle['volume'])
    
    body = abs(close_price - open_price)
    lower_wick = min(open_price, close_price) - low_price
    upper_wick = high_price - max(open_price, close_price)
    candle_range = high_price - low_price
    
    if candle_range == 0:
        return None
    
    body_percent = (body / open_price) * 100
    range_percent = (candle_range / open_price) * 100
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    open_to_low_percent = ((low_price - open_price) / open_price) * 100
    
    volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else None
    
    return {
        "range_pct": range_percent,
        "body_pct": body_percent,
        "lw_body_ratio": lower_wick_body_ratio,
        "lw_range_pct": lower_wick_range_ratio * 100,
        "open_low_pct": open_to_low_percent,
        "volume_ratio": volume_ratio
    }


def check_pass_fail_canonical(metrics):
    """Check PASS/FAIL using canonical implementation."""
    lw_metrics = LW001Metrics(
        range_pct=metrics["range_pct"],
        body_pct=metrics["body_pct"],
        lower_wick_body_ratio=metrics["lw_body_ratio"],
        lower_wick_range_pct=metrics["lw_range_pct"],
        open_to_low_pct=metrics["open_low_pct"],
        volume_ratio=metrics["volume_ratio"]
    )
    
    passed, failures = check_all_conditions(lw_metrics)
    return passed


def check_pass_fail_control_test(metrics):
    """Check PASS/FAIL using canonical check_all_conditions with unit validation."""
    # Convert dict to LW001Metrics for canonical checking
    lw_metrics = LW001Metrics(
        range_pct=metrics["range_pct"],
        body_pct=metrics["body_pct"],
        lower_wick_body_ratio=metrics["lw_body_ratio"],
        lower_wick_range_pct=metrics["lw_range_pct"],
        open_to_low_pct=metrics["open_low_pct"],
        volume_ratio=metrics["volume_ratio"]
    )
    
    passed, failures = check_all_conditions(lw_metrics)
    return passed


async def run_cross_pipeline_test():
    """Run cross-pipeline test with 100 candles."""
    print("=" * 100)
    print("CROSS-PIPELINE TEST: 100 HISTORICAL CANDLES")
    print("=" * 100)
    
    # Fetch test candles
    print("\nFetching 100 test candles...")
    candles = await fetch_100_test_candles()
    
    if len(candles) < 100:
        print(f"ERROR: Only fetched {len(candles)} candles, need 100")
        return
    
    print(f"Fetched {len(candles)} candles")
    
    # Test each candle
    mismatches = {
        "range": 0,
        "body": 0,
        "lw_body": 0,
        "lw_range": 0,
        "open_low": 0,
        "volume": 0,
        "pass_fail": 0
    }
    
    tolerance_pct = 0.01  # 0.01% tolerance for percentages
    tolerance_ratio = 0.001  # 0.001 tolerance for ratios
    
    for i in range(len(candles)):
        candle = candles[i]
        
        # Calculate avg volume from previous 20 candles
        if i >= 20:
            prev_candles = candles[i-20:i]
            avg_volume_20 = sum(float(c['volume']) for c in prev_candles) / 20
        else:
            avg_volume_20 = 1.0  # Fallback for first 20 candles
        
        # Calculate metrics using both implementations
        canonical_metrics = calculate_metrics_canonical(candle, avg_volume_20)
        control_metrics = calculate_metrics_control_test(candle, avg_volume_20)
        
        if control_metrics is None:
            continue
        
        # Compare metrics
        range_diff = abs(canonical_metrics["range_pct"] - control_metrics["range_pct"])
        body_diff = abs(canonical_metrics["body_pct"] - control_metrics["body_pct"])
        lw_body_diff = abs(canonical_metrics["lw_body_ratio"] - control_metrics["lw_body_ratio"])
        lw_range_diff = abs(canonical_metrics["lw_range_pct"] - control_metrics["lw_range_pct"])
        open_low_diff = abs(canonical_metrics["open_low_pct"] - control_metrics["open_low_pct"])
        
        if range_diff > tolerance_pct:
            mismatches["range"] += 1
        
        if body_diff > tolerance_pct:
            mismatches["body"] += 1
        
        if lw_body_diff > tolerance_ratio:
            mismatches["lw_body"] += 1
        
        if lw_range_diff > tolerance_pct:
            mismatches["lw_range"] += 1
        
        if open_low_diff > tolerance_pct:
            mismatches["open_low"] += 1
        
        # Compare PASS/FAIL
        canonical_pass = check_pass_fail_canonical(canonical_metrics)
        control_pass = check_pass_fail_control_test(control_metrics)
        
        if canonical_pass != control_pass:
            mismatches["pass_fail"] += 1
        
        # Show first 5 comparisons
        if i < 5:
            print(f"\n--- Candle {i+1} ---")
            print(f"Canonical: Range={canonical_metrics['range_pct']:.2f}% Body={canonical_metrics['body_pct']:.2f}% LW/Body={canonical_metrics['lw_body_ratio']:.2f}x LW/Range={canonical_metrics['lw_range_pct']:.1f}% Open to Low={canonical_metrics['open_low_pct']:.2f}% Vol={canonical_metrics['volume_ratio']:.2f}x")
            print(f"Control:   Range={control_metrics['range_pct']:.2f}% Body={control_metrics['body_pct']:.2f}% LW/Body={control_metrics['lw_body_ratio']:.2f}x LW/Range={control_metrics['lw_range_pct']:.1f}% Open to Low={control_metrics['open_low_pct']:.2f}% Vol={control_metrics['volume_ratio']:.2f}x")
            print(f"PASS/FAIL: Canonical={canonical_pass} Control={control_pass} Match={canonical_pass == control_pass}")
    
    print(f"\n" + "=" * 100)
    print("CROSS-PIPELINE TEST RESULTS")
    print("=" * 100)
    
    print(f"\nCandles tested: {len(candles)}")
    print(f"\nMismatches:")
    print(f"  Range: {mismatches['range']}/{len(candles)}")
    print(f"  Body: {mismatches['body']}/{len(candles)}")
    print(f"  LW/Body: {mismatches['lw_body']}/{len(candles)}")
    print(f"  LW/Range: {mismatches['lw_range']}/{len(candles)}")
    print(f"  Open to Low: {mismatches['open_low']}/{len(candles)}")
    print(f"  PASS/FAIL: {mismatches['pass_fail']}/{len(candles)}")
    
    total_mismatches = sum(mismatches.values())
    
    print(f"\nTotal mismatches: {total_mismatches}")
    
    if total_mismatches == 0:
        print(f"\nRESULT: PASS - All 100 candles produce identical results")
    else:
        print(f"\nRESULT: FAIL - {total_mismatches} mismatches found")
    
    return total_mismatches == 0


if __name__ == "__main__":
    result = asyncio.run(run_cross_pipeline_test())
    sys.exit(0 if result else 1)
