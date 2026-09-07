#!/usr/bin/env python3
"""
Simple unit tests for LW-001 qualification formula.

Tests the exact qualification formula:
qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
"""

from dataclasses import dataclass


@dataclass
class TestCase:
    """Test case for LW-001 qualification."""
    name: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    expected_qualified: bool
    description: str


def calculate_lw001_qualification(open_price, high_price, low_price, close_price, threshold=2.0):
    """
    Calculate LW-001 qualification using the exact formula.
    
    Formula: qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
    """
    # Condition 1: Red candle (Close < Open)
    is_red = close_price < open_price
    
    if is_red:
        # For red candle
        body = open_price - close_price
        lower_wick = close_price - low_price
    else:
        # For green candle (not used in qualification but calculated for completeness)
        body = close_price - open_price
        lower_wick = open_price - low_price
    
    # Upper wick (informational only, NOT used in qualification)
    upper_wick = high_price - max(open_price, close_price)
    
    # Calculate ratio
    if body > 0:
        ratio = lower_wick / body
    else:
        ratio = 0.0
    
    # Qualification: red candle AND lower_wick/body >= threshold
    qualified = is_red and ratio >= threshold
    
    return {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified
    }


def run_test(test_case: TestCase):
    """Run a single test case."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case.name}")
    print(f"Description: {test_case.description}")
    print(f"{'='*80}")
    
    # Calculate using LW-001 formula
    result = calculate_lw001_qualification(
        test_case.open_price,
        test_case.high_price,
        test_case.low_price,
        test_case.close_price,
        threshold=2.0
    )
    
    print(f"\nOHLC Data:")
    print(f"  Open: {test_case.open_price}")
    print(f"  High: {test_case.high_price}")
    print(f"  Low: {test_case.low_price}")
    print(f"  Close: {test_case.close_price}")
    
    print(f"\nLW-001 Calculation:")
    print(f"  Red Candle (Close < Open): {result['is_red']}")
    print(f"  Body (Open - Close for red): {result['body']}")
    print(f"  Lower Wick (Close - Low for red): {result['lower_wick']}")
    print(f"  Upper Wick (informational only): {result['upper_wick']}")
    print(f"  Lower Wick / Body: {result['ratio']:.2f}x")
    print(f"  Expected Qualified: {test_case.expected_qualified}")
    print(f"  Calculated Qualified: {result['qualified']}")
    
    # Verify
    test_passed = (result['qualified'] == test_case.expected_qualified)
    
    print(f"\nTest Result: {'PASS' if test_passed else 'FAIL'}")
    
    if not test_passed:
        print(f"  ERROR: Expected {test_case.expected_qualified}, got {result['qualified']}")
    
    return test_passed


def main():
    """Run all unit tests."""
    print("="*80)
    print("LW-001 QUALIFICATION FORMULA UNIT TESTS")
    print("="*80)
    print("\nTesting formula: qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)")
    print("\nUpper wick is NOT used in qualification - it's informational only.")
    
    # Test cases
    test_cases = [
        TestCase(
            name="Test 1 - Should PASS (basic hammer)",
            open_price=100.0,
            high_price=101.0,
            low_price=97.0,
            close_price=99.0,
            expected_qualified=True,
            description="Red candle with lower wick exactly 2x body"
        ),
        TestCase(
            name="Test 2 - Should FAIL (insufficient lower wick)",
            open_price=100.0,
            high_price=101.0,
            low_price=98.0,
            close_price=99.0,
            expected_qualified=False,
            description="Red candle with lower wick only 1x body"
        ),
        TestCase(
            name="Test 3 - Should PASS (huge upper wick ignored)",
            open_price=100.0,
            high_price=150.0,
            low_price=97.0,
            close_price=99.0,
            expected_qualified=True,
            description="Red candle with huge upper wick - should PASS because upper wick is ignored"
        ),
        TestCase(
            name="Test 4 - Should FAIL (green candle)",
            open_price=99.0,
            high_price=101.0,
            low_price=97.0,
            close_price=100.0,
            expected_qualified=False,
            description="Green candle - should FAIL regardless of lower wick"
        ),
        TestCase(
            name="Test 5 - Should PASS (strong hammer)",
            open_price=100.0,
            high_price=102.0,
            low_price=92.0,
            close_price=98.0,
            expected_qualified=True,
            description="Red candle with lower wick 3x body"
        ),
        TestCase(
            name="Test 6 - Should FAIL (doji - no body)",
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
            expected_qualified=False,
            description="Doji with no body - should FAIL"
        ),
    ]
    
    results = []
    for test_case in test_cases:
        passed = run_test(test_case)
        results.append((test_case.name, passed))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] ALL TESTS PASSED")
        print("\nFormula verified: qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)")

        print("\nKey confirmations:")
        print("  [OK] Upper wick does NOT affect qualification")
        print("  [OK] Only red candles (Close < Open) are considered")
        print("  [OK] Only lower wick / body ratio matters")
        print("  [OK] Threshold is exactly 2.0")
    else:
        print(f"\n[FAIL] {total - passed} TEST(S) FAILED")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
