#!/usr/bin/env python3
"""
Unit Tests for LW-001 Strategy Logic Verification

Tests A-F to verify the correct implementation of LW-001 qualification logic.

User's specification:
- Body = Open - Close (for red candles)
- Lower Wick = Close - Low (for red candles)
- Upper Wick = High - Open (for red candles, informational only)
- Qualification = (Close < Open) AND (Lower Wick >= 2 * Body)
- Upper Wick does NOT participate in qualification
- High does NOT participate in qualification
"""

def check_lw001(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """
    Check if candle meets LW-001 conditions.
    
    User's specification:
    - Red candle: Close < Open
    - Body = Open - Close
    - Lower Wick = Close - Low
    - Upper Wick = High - Open (informational only)
    - Qualification = (Close < Open) AND (Lower Wick >= 2 * Body)
    """
    # Condition 1: Red candle (Close < Open)
    is_red = close_price < open_price
    
    if not is_red:
        return {
            "qualified": False,
            "reason": "Not a red candle",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    # Calculate body (Open - Close for red candles)
    body = open_price - close_price
    
    if body <= 0:
        return {
            "qualified": False,
            "reason": "Zero or negative body",
            "is_red": is_red,
            "body": body,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    # Calculate lower wick (Close - Low for red candles)
    lower_wick = close_price - low_price
    
    # Calculate upper wick (informational only: High - Open for red candles)
    upper_wick = high_price - open_price
    
    # Calculate ratio
    wick_body_ratio = lower_wick / body
    
    # Condition 2: Lower Wick >= 2 * Body
    qualified = lower_wick >= 2 * body
    
    return {
        "qualified": qualified,
        "reason": "Qualified" if qualified else "Lower Wick < 2 * Body",
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "wick_body_ratio": wick_body_ratio,
    }


def run_test(test_name: str, open_price: float, high_price: float, low_price: float, close_price: float, expected_qualified: bool) -> dict:
    """Run a single test and return results."""
    result = check_lw001(open_price, high_price, low_price, close_price)
    
    passed = result["qualified"] == expected_qualified
    
    return {
        "test_name": test_name,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "expected": expected_qualified,
        "actual": result["qualified"],
        "passed": passed,
        "details": result,
    }


def main():
    """Run all unit tests A-F."""
    print("=" * 80)
    print("LW-001 UNIT TESTS A-F")
    print("=" * 80)
    
    tests = []
    
    # Test A - SHOULD PASS
    # Red candle with huge upper wick but lower wick >= 2x body
    print("\n" + "=" * 80)
    print("TEST A - SHOULD PASS")
    print("Red candle with huge upper wick but lower wick >= 2x body")
    print("=" * 80)
    test_a = run_test(
        test_name="Test A",
        open_price=100,
        high_price=150,
        low_price=65,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test_a['open']}")
    print(f"High: {test_a['high']}")
    print(f"Low: {test_a['low']}")
    print(f"Close: {test_a['close']}")
    print(f"Body: {test_a['details']['body']}")
    print(f"Lower Wick: {test_a['details']['lower_wick']}")
    print(f"Upper Wick: {test_a['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test_a['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test_a['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_a['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_a['passed'] else '[FAIL]'}")
    tests.append(test_a)
    
    # Test B - SHOULD FAIL
    # Red candle with huge upper wick but lower wick < 2x body
    print("\n" + "=" * 80)
    print("TEST B - SHOULD FAIL")
    print("Red candle with huge upper wick but lower wick < 2x body")
    print("=" * 80)
    test_b = run_test(
        test_name="Test B",
        open_price=100,
        high_price=150,
        low_price=85,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_b['open']}")
    print(f"High: {test_b['high']}")
    print(f"Low: {test_b['low']}")
    print(f"Close: {test_b['close']}")
    print(f"Body: {test_b['details']['body']}")
    print(f"Lower Wick: {test_b['details']['lower_wick']}")
    print(f"Upper Wick: {test_b['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test_b['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test_b['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_b['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_b['passed'] else '[FAIL]'}")
    tests.append(test_b)
    
    # Test C - CRITICAL - SHOULD FAIL
    # Red candle with NO lower wick (Close == Low) but huge upper wick
    print("\n" + "=" * 80)
    print("TEST C - CRITICAL - SHOULD FAIL")
    print("Red candle with NO lower wick (Close == Low) but huge upper wick")
    print("This is the case that was incorrectly passing before")
    print("=" * 80)
    test_c = run_test(
        test_name="Test C",
        open_price=100,
        high_price=150,
        low_price=90,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_c['open']}")
    print(f"High: {test_c['high']}")
    print(f"Low: {test_c['low']}")
    print(f"Close: {test_c['close']}")
    print(f"Body: {test_c['details']['body']}")
    print(f"Lower Wick: {test_c['details']['lower_wick']}")
    print(f"Upper Wick: {test_c['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test_c['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test_c['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_c['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_c['passed'] else '[FAIL]'}")
    tests.append(test_c)
    
    # Test D - EXACTLY 2X - SHOULD PASS
    # Red candle with lower wick exactly 2x body
    print("\n" + "=" * 80)
    print("TEST D - EXACTLY 2X - SHOULD PASS")
    print("Red candle with lower wick exactly 2x body")
    print("=" * 80)
    test_d = run_test(
        test_name="Test D",
        open_price=100,
        high_price=105,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test_d['open']}")
    print(f"High: {test_d['high']}")
    print(f"Low: {test_d['low']}")
    print(f"Close: {test_d['close']}")
    print(f"Body: {test_d['details']['body']}")
    print(f"Lower Wick: {test_d['details']['lower_wick']}")
    print(f"Upper Wick: {test_d['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test_d['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test_d['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_d['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_d['passed'] else '[FAIL]'}")
    tests.append(test_d)
    
    # Test E - JUST BELOW 2X - SHOULD FAIL
    # Red candle with lower wick just below 2x body
    print("\n" + "=" * 80)
    print("TEST E - JUST BELOW 2X - SHOULD FAIL")
    print("Red candle with lower wick just below 2x body")
    print("=" * 80)
    test_e = run_test(
        test_name="Test E",
        open_price=100,
        high_price=150,
        low_price=70.1,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_e['open']}")
    print(f"High: {test_e['high']}")
    print(f"Low: {test_e['low']}")
    print(f"Close: {test_e['close']}")
    print(f"Body: {test_e['details']['body']}")
    print(f"Lower Wick: {test_e['details']['lower_wick']}")
    print(f"Upper Wick: {test_e['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test_e['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test_e['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_e['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_e['passed'] else '[FAIL]'}")
    tests.append(test_e)
    
    # Test F - GREEN CANDLE - SHOULD FAIL
    # Green candle (Close > Open) - should always fail regardless of wick
    print("\n" + "=" * 80)
    print("TEST F - GREEN CANDLE - SHOULD FAIL")
    print("Green candle (Close > Open) - should always fail regardless of wick")
    print("=" * 80)
    test_f = run_test(
        test_name="Test F",
        open_price=90,
        high_price=150,
        low_price=65,
        close_price=100,
        expected_qualified=False
    )
    print(f"Open: {test_f['open']}")
    print(f"High: {test_f['high']}")
    print(f"Low: {test_f['low']}")
    print(f"Close: {test_f['close']}")
    print(f"Is Red: {test_f['details']['is_red']}")
    print(f"Expected: {'PASS' if test_f['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test_f['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test_f['passed'] else '[FAIL]'}")
    tests.append(test_f)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test in tests:
        status = "[OK]" if test["passed"] else "[FAIL]"
        print(f"{test['test_name']}: {status}")
    
    total_passed = sum(1 for t in tests if t["passed"])
    total_tests = len(tests)
    
    print("-" * 80)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n[SUCCESS] All unit tests passed!")
    else:
        print("\n[FAILURE] Some unit tests failed!")
        print("DO NOT proceed to signal search until all tests pass.")
    
    return tests


if __name__ == "__main__":
    main()
