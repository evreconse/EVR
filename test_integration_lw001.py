#!/usr/bin/env python3
"""
Integration test for LW-001 with synthetic passing candle.

Tests that a candle designed to pass all conditions actually passes.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import sys
sys.path.insert(0, ".")

from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    check_all_conditions,
    LW001_THRESHOLDS
)


def test_synthetic_passing_candle():
    """Test with a synthetic candle designed to pass all conditions."""
    print("=" * 100)
    print("INTEGRATION TEST: Synthetic Passing Candle")
    print("=" * 100)
    
    # Design a candle that passes all 6 conditions:
    # Range >= 6%, Body >= 1.9%, LW/Body >= 2.5x, LW/Range >= 63%, Open→Low <= -5%, Volume Ratio >= 2.6x
    
    open_price = 100.0
    close_price = 102.0  # Body = 2% (>= 1.9% ✓)
    high_price = 104.0
    low_price = 91.0  # Range = 13% (>= 6% ✓), Open→Low = -9% (<= -5% ✓)
    volume = 1000.0
    reference_avg = 300.0  # Volume Ratio = 3.33x (>= 2.6x ✓)
    
    # Calculate expected values:
    # LW = min(100, 102) - 91 = 9
    # LW/Body = 9/2 = 4.5x (>= 2.5x ✓)
    # LW/Range = 9/13 = 69.2% (>= 63% ✓)
    
    print(f"\nSynthetic Candle OHLCV:")
    print(f"  Open: {open_price}")
    print(f"  High: {high_price}")
    print(f"  Low: {low_price}")
    print(f"  Close: {close_price}")
    print(f"  Volume: {volume}")
    print(f"  Avg Volume (20): {reference_avg}")
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    
    print(f"\nCalculated Metrics:")
    print(f"  Range: {metrics.range_pct:.2f}%")
    print(f"  Body: {metrics.body_pct:.2f}%")
    print(f"  LW/Body: {metrics.lower_wick_body_ratio:.2f}x")
    print(f"  LW/Range: {metrics.lower_wick_range_pct:.1f}%")
    print(f"  Open to Low: {metrics.open_to_low_pct:.2f}%")
    print(f"  Volume Ratio: {metrics.volume_ratio:.2f}x")
    
    print(f"\nThresholds:")
    print(f"  Range >= {LW001_THRESHOLDS['range_pct']['value']}%")
    print(f"  Body >= {LW001_THRESHOLDS['body_pct']['value']}%")
    print(f"  LW/Body >= {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x")
    print(f"  LW/Range >= {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%")
    print(f"  Open to Low <= {LW001_THRESHOLDS['open_to_low_pct']['value']}%")
    print(f"  Volume Ratio >= {LW001_THRESHOLDS['volume_ratio']['value']}x")
    
    print(f"\nCondition Checks:")
    print(f"  Range: {metrics.range_pct:.2f}% >= {LW001_THRESHOLDS['range_pct']['value']}%: {'PASS' if metrics.range_pct >= LW001_THRESHOLDS['range_pct']['value'] else 'FAIL'}")
    print(f"  Body: {metrics.body_pct:.2f}% >= {LW001_THRESHOLDS['body_pct']['value']}%: {'PASS' if metrics.body_pct >= LW001_THRESHOLDS['body_pct']['value'] else 'FAIL'}")
    print(f"  LW/Body: {metrics.lower_wick_body_ratio:.2f}x >= {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x: {'PASS' if metrics.lower_wick_body_ratio >= LW001_THRESHOLDS['lower_wick_body_ratio']['value'] else 'FAIL'}")
    print(f"  LW/Range: {metrics.lower_wick_range_pct:.1f}% >= {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%: {'PASS' if metrics.lower_wick_range_pct >= LW001_THRESHOLDS['lower_wick_range_pct']['value'] else 'FAIL'}")
    print(f"  Open to Low: {metrics.open_to_low_pct:.2f}% <= {LW001_THRESHOLDS['open_to_low_pct']['value']}%: {'PASS' if metrics.open_to_low_pct <= LW001_THRESHOLDS['open_to_low_pct']['value'] else 'FAIL'}")
    print(f"  Volume Ratio: {metrics.volume_ratio:.2f}x >= {LW001_THRESHOLDS['volume_ratio']['value']}x: {'PASS' if metrics.volume_ratio >= LW001_THRESHOLDS['volume_ratio']['value'] else 'FAIL'}")
    
    passed, failures = check_all_conditions(metrics)
    
    print(f"\nFinal Result:")
    print(f"  Overall: {'PASS' if passed else 'FAIL'}")
    if failures:
        print(f"  Failures: {failures}")
    else:
        print(f"  All 6 conditions passed!")
    
    return passed


def test_synthetic_failing_candles():
    """Test candles that fail each condition (may fail multiple due to interdependence)."""
    print(f"\n{'=' * 100}")
    print("INTEGRATION TEST: Synthetic Failing Candles (Negative Tests)")
    print("=" * 100)
    print("Note: Due to metric interdependence, some tests may fail on multiple conditions.")
    print("The key is that ALL tests should result in FAIL (not PASS).")
    
    reference_avg = 300.0
    
    # Test 1: Range FAIL
    print(f"\nTest 1: Range FAIL (primary)")
    open_price = 100.0
    close_price = 102.0
    high_price = 104.0  # Range = 4% (FAIL)
    low_price = 100.0
    volume = 1000.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  Range: {metrics.range_pct:.2f}% (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")
    
    # Test 2: Body FAIL
    print(f"\nTest 2: Body FAIL (primary)")
    open_price = 100.0
    close_price = 100.5  # Body = 0.5% (FAIL)
    high_price = 106.0
    low_price = 91.0
    volume = 1000.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  Body: {metrics.body_pct:.2f}% (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")
    
    # Test 3: LW/Body FAIL
    print(f"\nTest 3: LW/Body FAIL (primary)")
    open_price = 100.0
    close_price = 102.0
    high_price = 106.0
    low_price = 97.0  # LW = 3, LW/Body = 1.5x (FAIL)
    volume = 1000.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  LW/Body: {metrics.lower_wick_body_ratio:.2f}x (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")
    
    # Test 4: LW/Range FAIL
    print(f"\nTest 4: LW/Range FAIL (primary)")
    open_price = 100.0
    close_price = 102.0
    high_price = 110.0  # Range = 10%
    low_price = 96.0  # LW = 4, LW/Range = 40% (FAIL)
    volume = 1000.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  LW/Range: {metrics.lower_wick_range_pct:.1f}% (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")
    
    # Test 5: Open→Low FAIL
    print(f"\nTest 5: Open to Low FAIL (primary)")
    open_price = 100.0
    close_price = 102.0
    high_price = 106.0
    low_price = 96.0  # Open→Low = -4% (FAIL)
    volume = 1000.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  Open to Low: {metrics.open_to_low_pct:.2f}% (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")
    
    # Test 6: Volume Ratio FAIL
    print(f"\nTest 6: Volume Ratio FAIL (primary)")
    open_price = 100.0
    close_price = 102.0
    high_price = 106.0
    low_price = 94.0
    volume = 500.0  # Volume Ratio = 1.67x (FAIL)
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    passed, failures = check_all_conditions(metrics)
    print(f"  Volume Ratio: {metrics.volume_ratio:.2f}x (expected FAIL)")
    print(f"  Overall: {'FAIL' if not passed else 'UNEXPECTED PASS'}")


def main():
    """Run all integration tests."""
    print("=" * 100)
    print("LW-001 INTEGRATION TESTS")
    print("=" * 100)
    
    # Test passing candle
    passing = test_synthetic_passing_candle()
    
    # Test failing candles
    test_synthetic_failing_candles()
    
    print(f"\n{'=' * 100}")
    print("INTEGRATION TESTS COMPLETE")
    print(f"{'=' * 100}")
    
    if passing:
        print(f"\nRESULT: PASSING CANDLE TEST PASSED")
        print(f"The pipeline correctly identifies a valid signal.")
    else:
        print(f"\nRESULT: PASSING CANDLE TEST FAILED")
        print(f"The pipeline is broken - a valid candle was rejected.")


if __name__ == "__main__":
    main()
