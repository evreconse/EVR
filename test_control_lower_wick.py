#!/usr/bin/env python3
"""
Control Tests for Lower Wick Verification

These tests specifically verify that the algorithm correctly distinguishes
between lower wick and upper wick, and that upper wick does NOT help qualification.

User's specification:
- Body = Open - Close (for red candles)
- Lower Wick = Close - Low (for red candles)
- Upper Wick = High - Open (for red candles, informational only)
- Qualification = (Close < Open) AND (Lower Wick >= 2 * Body)
"""

def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """
    Check if candle meets LW-001 conditions using USER'S STRICT SPECIFICATION.
    
    User's specification:
    - Body = Open - Close (for red candles)
    - Lower Wick = Close - Low (for red candles)
    - Upper Wick = High - Open (for red candles, informational only)
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


def run_control_test(test_name: str, open_price: float, high_price: float, low_price: float, close_price: float, expected_qualified: bool) -> dict:
    """Run a single control test and return results."""
    result = check_lw001_strict(open_price, high_price, low_price, close_price)
    
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
    """Run all control tests TEST 1-6."""
    print("=" * 80)
    print("CONTROL TESTS FOR LOWER WICK VERIFICATION")
    print("=" * 80)
    
    tests = []
    
    # TEST 1 — правильная свеча
    print("\n" + "=" * 80)
    print("TEST 1 - SHOULD PASS")
    print("Correct candle with lower wick >= 2x body")
    print("=" * 80)
    test1 = run_control_test(
        test_name="TEST 1",
        open_price=100,
        high_price=120,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test1['open']}")
    print(f"High: {test1['high']}")
    print(f"Low: {test1['low']}")
    print(f"Close: {test1['close']}")
    print(f"Body: {test1['details']['body']}")
    print(f"Lower Wick: {test1['details']['lower_wick']}")
    print(f"Upper Wick: {test1['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test1['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test1['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test1['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test1['passed'] else '[FAIL]'}")
    tests.append(test1)
    
    # TEST 2 — нет нижней тени
    print("\n" + "=" * 80)
    print("TEST 2 - CRITICAL - SHOULD FAIL")
    print("NO lower wick (Close == Low)")
    print("Even if High is very large")
    print("=" * 80)
    test2 = run_control_test(
        test_name="TEST 2",
        open_price=100,
        high_price=120,
        low_price=90,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test2['open']}")
    print(f"High: {test2['high']}")
    print(f"Low: {test2['low']}")
    print(f"Close: {test2['close']}")
    print(f"Body: {test2['details']['body']}")
    print(f"Lower Wick: {test2['details']['lower_wick']}")
    print(f"Upper Wick: {test2['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test2['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test2['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test2['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test2['passed'] else '[FAIL]'}")
    tests.append(test2)
    
    # TEST 3 — большая верхняя тень НЕ должна помогать
    print("\n" + "=" * 80)
    print("TEST 3 - CRITICAL - SHOULD FAIL")
    print("HUGE upper wick should NOT help qualification")
    print("Lower Wick = 0, Upper Wick = 100")
    print("=" * 80)
    test3 = run_control_test(
        test_name="TEST 3",
        open_price=100,
        high_price=200,
        low_price=90,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test3['open']}")
    print(f"High: {test3['high']}")
    print(f"Low: {test3['low']}")
    print(f"Close: {test3['close']}")
    print(f"Body: {test3['details']['body']}")
    print(f"Lower Wick: {test3['details']['lower_wick']}")
    print(f"Upper Wick: {test3['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test3['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test3['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test3['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test3['passed'] else '[FAIL]'}")
    tests.append(test3)
    
    # TEST 4 — нижняя тень ровно 2× тела
    print("\n" + "=" * 80)
    print("TEST 4 - SHOULD PASS")
    print("Lower wick exactly 2x body")
    print("=" * 80)
    test4 = run_control_test(
        test_name="TEST 4",
        open_price=100,
        high_price=120,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test4['open']}")
    print(f"High: {test4['high']}")
    print(f"Low: {test4['low']}")
    print(f"Close: {test4['close']}")
    print(f"Body: {test4['details']['body']}")
    print(f"Lower Wick: {test4['details']['lower_wick']}")
    print(f"Upper Wick: {test4['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test4['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test4['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test4['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test4['passed'] else '[FAIL]'}")
    tests.append(test4)
    
    # TEST 5 — нижняя тень меньше 2× тела
    print("\n" + "=" * 80)
    print("TEST 5 - SHOULD FAIL")
    print("Lower wick less than 2x body")
    print("=" * 80)
    test5 = run_control_test(
        test_name="TEST 5",
        open_price=100,
        high_price=120,
        low_price=75,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test5['open']}")
    print(f"High: {test5['high']}")
    print(f"Low: {test5['low']}")
    print(f"Close: {test5['close']}")
    print(f"Body: {test5['details']['body']}")
    print(f"Lower Wick: {test5['details']['lower_wick']}")
    print(f"Upper Wick: {test5['details']['upper_wick']}")
    print(f"Lower Wick / Body: {test5['details']['wick_body_ratio']:.2f}x")
    print(f"Expected: {'PASS' if test5['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test5['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test5['passed'] else '[FAIL]'}")
    tests.append(test5)
    
    # TEST 6 — зелёная свеча
    print("\n" + "=" * 80)
    print("TEST 6 - SHOULD FAIL")
    print("Green candle (Close > Open)")
    print("Even with large lower wick")
    print("=" * 80)
    test6 = run_control_test(
        test_name="TEST 6",
        open_price=90,
        high_price=120,
        low_price=70,
        close_price=100,
        expected_qualified=False
    )
    print(f"Open: {test6['open']}")
    print(f"High: {test6['high']}")
    print(f"Low: {test6['low']}")
    print(f"Close: {test6['close']}")
    print(f"Is Red: {test6['details']['is_red']}")
    print(f"Expected: {'PASS' if test6['expected'] else 'FAIL'}")
    print(f"Actual: {'PASS' if test6['actual'] else 'FAIL'}")
    print(f"Result: {'[OK]' if test6['passed'] else '[FAIL]'}")
    tests.append(test6)
    
    # Summary
    print("\n" + "=" * 80)
    print("CONTROL TEST SUMMARY")
    print("=" * 80)
    for test in tests:
        status = "[OK]" if test["passed"] else "[FAIL]"
        print(f"{test['test_name']}: {status}")
    
    total_passed = sum(1 for t in tests if t["passed"])
    total_tests = len(tests)
    
    print("-" * 80)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n[SUCCESS] All control tests passed!")
        print("The formula is correct.")
    else:
        print("\n[FAILURE] Some control tests failed!")
        print("The formula is INCORRECT.")
        print("DO NOT proceed to signal search until all tests pass.")
    
    return tests


if __name__ == "__main__":
    main()
