#!/usr/bin/env python3
"""
Unit tests for LW-001 canonical metric specification.

Tests each metric calculation independently.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import sys
sys.path.insert(0, ".")

from LW001_METRIC_SPEC import (
    calculate_range_pct,
    calculate_body_pct,
    calculate_lower_wick,
    calculate_lower_wick_body_ratio,
    calculate_lower_wick_range_pct,
    calculate_open_to_low_pct,
    calculate_volume_ratio,
    calculate_all_metrics,
    validate_metric_units,
    LW001_THRESHOLDS,
    check_all_conditions
)


def test_range_pct():
    """Test Range percentage calculation."""
    print("=" * 100)
    print("TEST: Range Percentage")
    print("=" * 100)
    
    # Test 1: Standard case
    open_price = 100.0
    high_price = 106.0
    low_price = 94.0
    expected = 12.0  # (106 - 94) / 100 * 100 = 12%
    
    result = calculate_range_pct(open_price, high_price, low_price)
    print(f"\nTest 1: Open={open_price}, High={high_price}, Low={low_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Different values
    open_price = 50.0
    high_price = 53.0
    low_price = 47.0
    expected = 12.0  # (53 - 47) / 50 * 100 = 12%
    
    result = calculate_range_pct(open_price, high_price, low_price)
    print(f"\nTest 2: Open={open_price}, High={high_price}, Low={low_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_body_pct():
    """Test Body percentage calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: Body Percentage")
    print("=" * 100)
    
    # Test 1: Green candle
    open_price = 100.0
    close_price = 102.0
    expected = 2.0  # abs(102 - 100) / 100 * 100 = 2%
    
    result = calculate_body_pct(open_price, close_price)
    print(f"\nTest 1 (Green): Open={open_price}, Close={close_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Red candle
    open_price = 100.0
    close_price = 98.0
    expected = 2.0  # abs(98 - 100) / 100 * 100 = 2%
    
    result = calculate_body_pct(open_price, close_price)
    print(f"\nTest 2 (Red): Open={open_price}, Close={close_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_lower_wick():
    """Test Lower Wick calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: Lower Wick")
    print("=" * 100)
    
    # Test 1: Green candle
    open_price = 100.0
    close_price = 102.0
    low_price = 94.0
    expected = 6.0  # min(100, 102) - 94 = 100 - 94 = 6
    
    result = calculate_lower_wick(open_price, close_price, low_price)
    print(f"\nTest 1 (Green): Open={open_price}, Close={close_price}, Low={low_price}")
    print(f"  Expected: {expected}")
    print(f"  Result: {result:.2f}")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Red candle
    open_price = 100.0
    close_price = 98.0
    low_price = 94.0
    expected = 4.0  # min(100, 98) - 94 = 98 - 94 = 4
    
    result = calculate_lower_wick(open_price, close_price, low_price)
    print(f"\nTest 2 (Red): Open={open_price}, Close={close_price}, Low={low_price}")
    print(f"  Expected: {expected}")
    print(f"  Result: {result:.2f}")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_lower_wick_body_ratio():
    """Test LW/Body ratio calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: LW/Body Ratio")
    print("=" * 100)
    
    # Test 1: Standard case
    open_price = 100.0
    close_price = 102.0
    low_price = 94.0
    # LW = 6, Body = 2, Ratio = 3
    expected = 3.0
    
    result = calculate_lower_wick_body_ratio(open_price, close_price, low_price)
    print(f"\nTest 1: Open={open_price}, Close={close_price}, Low={low_price}")
    print(f"  Expected: {expected}x")
    print(f"  Result: {result:.2f}x")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Different ratio
    open_price = 100.0
    close_price = 101.0
    low_price = 95.0
    # LW = 5, Body = 1, Ratio = 5
    expected = 5.0
    
    result = calculate_lower_wick_body_ratio(open_price, close_price, low_price)
    print(f"\nTest 2: Open={open_price}, Close={close_price}, Low={low_price}")
    print(f"  Expected: {expected}x")
    print(f"  Result: {result:.2f}x")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_lower_wick_range_pct():
    """Test LW/Range percentage calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: LW/Range Percentage")
    print("=" * 100)
    
    # Test 1: Standard case
    open_price = 100.0
    high_price = 106.0
    low_price = 94.0
    close_price = 102.0
    # LW = 6, Range = 12, LW/Range = 50%
    expected = 50.0
    
    result = calculate_lower_wick_range_pct(open_price, high_price, low_price, close_price)
    print(f"\nTest 1: Open={open_price}, High={high_price}, Low={low_price}, Close={close_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.1f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.1 else 'FAIL'}")
    
    # Test 2: Different values
    open_price = 100.0
    high_price = 110.0
    low_price = 90.0
    close_price = 95.0
    # LW = 5, Range = 20, LW/Range = 25%
    expected = 25.0
    
    result = calculate_lower_wick_range_pct(open_price, high_price, low_price, close_price)
    print(f"\nTest 2: Open={open_price}, High={high_price}, Low={low_price}, Close={close_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.1f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.1 else 'FAIL'}")


def test_open_to_low_pct():
    """Test Open to Low percentage calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: Open to Low Percentage")
    print("=" * 100)
    
    # Test 1: Standard case
    open_price = 100.0
    low_price = 95.0
    expected = -5.0  # (95 - 100) / 100 * 100 = -5%
    
    result = calculate_open_to_low_pct(open_price, low_price)
    print(f"\nTest 1: Open={open_price}, Low={low_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Larger drop
    open_price = 100.0
    low_price = 94.0
    expected = -6.0  # (94 - 100) / 100 * 100 = -6%
    
    result = calculate_open_to_low_pct(open_price, low_price)
    print(f"\nTest 2: Open={open_price}, Low={low_price}")
    print(f"  Expected: {expected}%")
    print(f"  Result: {result:.2f}%")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_volume_ratio():
    """Test Volume Ratio calculation."""
    print(f"\n{'=' * 100}")
    print("TEST: Volume Ratio")
    print("=" * 100)
    
    # Test 1: Standard case
    candle_volume = 1000.0
    reference_avg = 500.0
    expected = 2.0  # 1000 / 500 = 2
    
    result = calculate_volume_ratio(candle_volume, reference_avg)
    print(f"\nTest 1: Candle Volume={candle_volume}, Avg Volume={reference_avg}")
    print(f"  Expected: {expected}x")
    print(f"  Result: {result:.2f}x")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")
    
    # Test 2: Higher ratio
    candle_volume = 1500.0
    reference_avg = 500.0
    expected = 3.0  # 1500 / 500 = 3
    
    result = calculate_volume_ratio(candle_volume, reference_avg)
    print(f"\nTest 2: Candle Volume={candle_volume}, Avg Volume={reference_avg}")
    print(f"  Expected: {expected}x")
    print(f"  Result: {result:.2f}x")
    print(f"  Status: {'PASS' if abs(result - expected) < 0.01 else 'FAIL'}")


def test_unit_validation():
    """Test unit validation."""
    print(f"\n{'=' * 100}")
    print("TEST: Unit Validation")
    print("=" * 100)
    
    # Test 1: Matching units
    print(f"\nTest 1: Matching units (%)")
    try:
        result = validate_metric_units(6.5, "%", 6.0, "%")
        print(f"  Status: PASS - Units match")
    except ValueError as e:
        print(f"  Status: FAIL - {e}")
    
    # Test 2: Mismatched units
    print(f"\nTest 2: Mismatched units (%) vs (x)")
    try:
        result = validate_metric_units(0.63, "x", 63.0, "%")
        print(f"  Status: FAIL - Should have raised ValueError")
    except ValueError as e:
        print(f"  Status: PASS - Correctly raised ValueError: {e}")
    
    # Test 3: Matching ratio units
    print(f"\nTest 3: Matching units (x)")
    try:
        result = validate_metric_units(2.5, "x", 2.5, "x")
        print(f"  Status: PASS - Units match")
    except ValueError as e:
        print(f"  Status: FAIL - {e}")


def test_all_metrics():
    """Test calculate_all_metrics function."""
    print(f"\n{'=' * 100}")
    print("TEST: Calculate All Metrics")
    print("=" * 100)
    
    open_price = 100.0
    high_price = 106.0
    low_price = 94.0
    close_price = 102.0
    volume = 1000.0
    reference_avg = 500.0
    
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, reference_avg)
    
    print(f"\nInput: O={open_price}, H={high_price}, L={low_price}, C={close_price}, V={volume}, Avg={reference_avg}")
    print(f"\nResults:")
    print(f"  Range: {metrics.range_pct:.2f}%")
    print(f"  Body: {metrics.body_pct:.2f}%")
    print(f"  LW/Body: {metrics.lower_wick_body_ratio:.2f}x")
    print(f"  LW/Range: {metrics.lower_wick_range_pct:.1f}%")
    print(f"  Open to Low: {metrics.open_to_low_pct:.2f}%")
    print(f"  Volume Ratio: {metrics.volume_ratio:.2f}x")
    
    # Verify expected values
    expected_range = 12.0  # (106-94)/100*100
    expected_body = 2.0  # abs(102-100)/100*100
    expected_lw_body = 3.0  # 6/2
    expected_lw_range = 50.0  # 6/12*100
    expected_open_low = -6.0  # (94-100)/100*100
    expected_vol_ratio = 2.0  # 1000/500
    
    print(f"\nVerification:")
    print(f"  Range: {metrics.range_pct:.2f}% vs {expected_range}% - {'PASS' if abs(metrics.range_pct - expected_range) < 0.01 else 'FAIL'}")
    print(f"  Body: {metrics.body_pct:.2f}% vs {expected_body}% - {'PASS' if abs(metrics.body_pct - expected_body) < 0.01 else 'FAIL'}")
    print(f"  LW/Body: {metrics.lower_wick_body_ratio:.2f}x vs {expected_lw_body}x - {'PASS' if abs(metrics.lower_wick_body_ratio - expected_lw_body) < 0.01 else 'FAIL'}")
    print(f"  LW/Range: {metrics.lower_wick_range_pct:.1f}% vs {expected_lw_range}% - {'PASS' if abs(metrics.lower_wick_range_pct - expected_lw_range) < 0.1 else 'FAIL'}")
    print(f"  Open to Low: {metrics.open_to_low_pct:.2f}% vs {expected_open_low}% - {'PASS' if abs(metrics.open_to_low_pct - expected_open_low) < 0.01 else 'FAIL'}")
    print(f"  Volume Ratio: {metrics.volume_ratio:.2f}x vs {expected_vol_ratio}x - {'PASS' if abs(metrics.volume_ratio - expected_vol_ratio) < 0.01 else 'FAIL'}")


def main():
    """Run all unit tests."""
    print("=" * 100)
    print("LW-001 CANONICAL METRIC SPECIFICATION - UNIT TESTS")
    print("=" * 100)
    
    test_range_pct()
    test_body_pct()
    test_lower_wick()
    test_lower_wick_body_ratio()
    test_lower_wick_range_pct()
    test_open_to_low_pct()
    test_volume_ratio()
    test_unit_validation()
    test_all_metrics()
    
    print(f"\n{'=' * 100}")
    print("UNIT TESTS COMPLETE")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
