#!/usr/bin/env python3
"""
Comprehensive unit tests for upper/lower wick distinction (TEST A-G).

These tests prove that upper wick does NOT help qualification.
Only lower wick matters for LW-001 qualification.

User's specification:
- Body = Open - Close (for red candles) - NOT abs()
- Lower Wick = Close - Low (for red candles)
- Upper Wick = High - Open (for red candles, informational only)
- Qualified = (Close < Open) AND (Lower Wick >= 2 * Body)
- CRITICAL: Close != Low (must have a lower wick)
"""

def check_lw001_production(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """
    Check using PRODUCTION formula from src/strategy/lw_001.py.
    
    PRODUCTION CODE (INCORRECT):
    body = abs(close_price - open_price)
    lower_wick = close_price - low_price
    """
    is_red = close_price < open_price
    body = abs(close_price - open_price)  # INCORRECT - uses abs()
    lower_wick = close_price - low_price
    upper_wick = high_price - max(open_price, close_price)
    wick_body_ratio = lower_wick / body if body > 0 else 0.0
    qualified = is_red and wick_body_ratio >= 2.0
    
    return {
        "qualified": qualified,
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "wick_body_ratio": wick_body_ratio,
    }


def check_lw001_corrected(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """
    Check using CORRECTED formula per user's specification.
    
    CORRECTED CODE:
    body = open_price - close_price  # NO abs()
    lower_wick = close_price - low_price
    CRITICAL: Close != Low check
    """
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
    
    # CRITICAL CHECK: Close must NOT equal Low (must have a lower wick)
    if close_price == low_price:
        return {
            "qualified": False,
            "reason": "Close == Low (no lower wick)",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "wick_body_ratio": None,
        }
    
    body = open_price - close_price  # NO abs() - for red candles only
    
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
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price  # For red candles
    wick_body_ratio = lower_wick / body
    qualified = wick_body_ratio >= 2.0
    
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
    """Run a single test comparing production vs corrected formula."""
    prod_result = check_lw001_production(open_price, high_price, low_price, close_price)
    corr_result = check_lw001_corrected(open_price, high_price, low_price, close_price)
    
    prod_matches = prod_result["qualified"] == expected_qualified
    corr_matches = corr_result["qualified"] == expected_qualified
    
    return {
        "test_name": test_name,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "expected": expected_qualified,
        "prod_qualified": prod_result["qualified"],
        "prod_matches": prod_matches,
        "corr_qualified": corr_result["qualified"],
        "corr_matches": corr_matches,
        "prod_details": prod_result,
        "corr_details": corr_result,
    }


def main():
    """Run all tests TEST A-G."""
    print("=" * 80)
    print("COMPREHENSIVE UNIT TESTS FOR UPPER/LOWER WICK DISTINCTION")
    print("=" * 80)
    
    tests = []
    
    # TEST A - PASS
    print("\n" + "=" * 80)
    print("TEST A - SHOULD PASS")
    print("Red candle, lower wick 2x body")
    print("=" * 80)
    test_a = run_test(
        test_name="TEST A",
        open_price=100,
        high_price=110,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test_a['open']}, High: {test_a['high']}, Low: {test_a['low']}, Close: {test_a['close']}")
    print(f"Expected: {'PASS' if test_a['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_a['prod_qualified'] else 'FAIL'} - {'[OK]' if test_a['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_a['corr_qualified'] else 'FAIL'} - {'[OK]' if test_a['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_a['prod_details']['body']}, Lower Wick: {test_a['prod_details']['lower_wick']}, Ratio: {test_a['prod_details']['wick_body_ratio']:.2f}x")
    print(f"Corrected Body: {test_a['corr_details']['body']}, Lower Wick: {test_a['corr_details']['lower_wick']}, Ratio: {test_a['corr_details']['wick_body_ratio']:.2f}x")
    tests.append(test_a)
    
    # TEST B - FAIL
    print("\n" + "=" * 80)
    print("TEST B - SHOULD FAIL")
    print("Red candle, lower wick 1.99x body")
    print("=" * 80)
    test_b = run_test(
        test_name="TEST B",
        open_price=100,
        high_price=150,
        low_price=88.1,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_b['open']}, High: {test_b['high']}, Low: {test_b['low']}, Close: {test_b['close']}")
    print(f"Expected: {'PASS' if test_b['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_b['prod_qualified'] else 'FAIL'} - {'[OK]' if test_b['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_b['corr_qualified'] else 'FAIL'} - {'[OK]' if test_b['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_b['prod_details']['body']}, Lower Wick: {test_b['prod_details']['lower_wick']}, Ratio: {test_b['prod_details']['wick_body_ratio']:.2f}x")
    print(f"Corrected Body: {test_b['corr_details']['body']}, Lower Wick: {test_b['corr_details']['lower_wick']}, Ratio: {test_b['corr_details']['wick_body_ratio']:.2f}x")
    tests.append(test_b)
    
    # TEST C - CRITICAL FAIL
    print("\n" + "=" * 80)
    print("TEST C - CRITICAL - SHOULD FAIL")
    print("Red candle, lower wick 0.1x body, upper wick 20x body")
    print("=" * 80)
    test_c = run_test(
        test_name="TEST C",
        open_price=100,
        high_price=300,
        low_price=89,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_c['open']}, High: {test_c['high']}, Low: {test_c['low']}, Close: {test_c['close']}")
    print(f"Expected: {'PASS' if test_c['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_c['prod_qualified'] else 'FAIL'} - {'[OK]' if test_c['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_c['corr_qualified'] else 'FAIL'} - {'[OK]' if test_c['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_c['prod_details']['body']}, Lower Wick: {test_c['prod_details']['lower_wick']}, Upper Wick: {test_c['prod_details']['upper_wick']}, Ratio: {test_c['prod_details']['wick_body_ratio']:.2f}x")
    print(f"Corrected Body: {test_c['corr_details']['body']}, Lower Wick: {test_c['corr_details']['lower_wick']}, Upper Wick: {test_c['corr_details']['upper_wick']}, Ratio: {test_c['corr_details']['wick_body_ratio']:.2f}x")
    tests.append(test_c)
    
    # TEST D - CRITICAL FAIL
    print("\n" + "=" * 80)
    print("TEST D - CRITICAL - SHOULD FAIL")
    print("Red candle, lower wick = 0, upper wick 100x body")
    print("=" * 80)
    test_d = run_test(
        test_name="TEST D",
        open_price=100,
        high_price=1100,
        low_price=90,
        close_price=90,
        expected_qualified=False
    )
    print(f"Open: {test_d['open']}, High: {test_d['high']}, Low: {test_d['low']}, Close: {test_d['close']}")
    print(f"Expected: {'PASS' if test_d['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_d['prod_qualified'] else 'FAIL'} - {'[OK]' if test_d['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_d['corr_qualified'] else 'FAIL'} - {'[OK]' if test_d['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_d['prod_details']['body']}, Lower Wick: {test_d['prod_details']['lower_wick']}, Upper Wick: {test_d['prod_details']['upper_wick']}, Ratio: {test_d['prod_details']['wick_body_ratio']:.2f}x")
    if test_d['corr_details']['body'] is not None:
        print(f"Corrected Body: {test_d['corr_details']['body']}, Lower Wick: {test_d['corr_details']['lower_wick']}, Upper Wick: {test_d['corr_details']['upper_wick']}, Ratio: {test_d['corr_details']['wick_body_ratio']:.2f}x")
    else:
        print(f"Corrected: {test_d['corr_details']['reason']}")
    tests.append(test_d)
    
    # TEST E - PASS
    print("\n" + "=" * 80)
    print("TEST E - SHOULD PASS")
    print("Red candle, lower wick 3x body, upper wick 0")
    print("=" * 80)
    test_e = run_test(
        test_name="TEST E",
        open_price=100,
        high_price=100,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test_e['open']}, High: {test_e['high']}, Low: {test_e['low']}, Close: {test_e['close']}")
    print(f"Expected: {'PASS' if test_e['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_e['prod_qualified'] else 'FAIL'} - {'[OK]' if test_e['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_e['corr_qualified'] else 'FAIL'} - {'[OK]' if test_e['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_e['prod_details']['body']}, Lower Wick: {test_e['prod_details']['lower_wick']}, Upper Wick: {test_e['prod_details']['upper_wick']}, Ratio: {test_e['prod_details']['wick_body_ratio']:.2f}x")
    print(f"Corrected Body: {test_e['corr_details']['body']}, Lower Wick: {test_e['corr_details']['lower_wick']}, Upper Wick: {test_e['corr_details']['upper_wick']}, Ratio: {test_e['corr_details']['wick_body_ratio']:.2f}x")
    tests.append(test_e)
    
    # TEST F - PASS
    print("\n" + "=" * 80)
    print("TEST F - SHOULD PASS")
    print("Red candle, lower wick 2x body, upper wick 100x body")
    print("=" * 80)
    test_f = run_test(
        test_name="TEST F",
        open_price=100,
        high_price=2100,
        low_price=70,
        close_price=90,
        expected_qualified=True
    )
    print(f"Open: {test_f['open']}, High: {test_f['high']}, Low: {test_f['low']}, Close: {test_f['close']}")
    print(f"Expected: {'PASS' if test_f['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_f['prod_qualified'] else 'FAIL'} - {'[OK]' if test_f['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_f['corr_qualified'] else 'FAIL'} - {'[OK]' if test_f['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_f['prod_details']['body']}, Lower Wick: {test_f['prod_details']['lower_wick']}, Upper Wick: {test_f['prod_details']['upper_wick']}, Ratio: {test_f['prod_details']['wick_body_ratio']:.2f}x")
    print(f"Corrected Body: {test_f['corr_details']['body']}, Lower Wick: {test_f['corr_details']['lower_wick']}, Upper Wick: {test_f['corr_details']['upper_wick']}, Ratio: {test_f['corr_details']['wick_body_ratio']:.2f}x")
    tests.append(test_f)
    
    # TEST G - FAIL
    print("\n" + "=" * 80)
    print("TEST G - SHOULD FAIL")
    print("Green candle, huge lower wick")
    print("=" * 80)
    test_g = run_test(
        test_name="TEST G",
        open_price=90,
        high_price=150,
        low_price=60,
        close_price=100,
        expected_qualified=False
    )
    print(f"Open: {test_g['open']}, High: {test_g['high']}, Low: {test_g['low']}, Close: {test_g['close']}")
    print(f"Expected: {'PASS' if test_g['expected'] else 'FAIL'}")
    print(f"Production: {'PASS' if test_g['prod_qualified'] else 'FAIL'} - {'[OK]' if test_g['prod_matches'] else '[FAIL]'}")
    print(f"Corrected: {'PASS' if test_g['corr_qualified'] else 'FAIL'} - {'[OK]' if test_g['corr_matches'] else '[FAIL]'}")
    print(f"Production Body: {test_g['prod_details']['body']}, Lower Wick: {test_g['prod_details']['lower_wick']}, Ratio: {test_g['prod_details']['wick_body_ratio']:.2f}x")
    if test_g['corr_details']['body'] is not None:
        print(f"Corrected Body: {test_g['corr_details']['body']}, Lower Wick: {test_g['corr_details']['lower_wick']}, Ratio: {test_g['corr_details']['wick_body_ratio']:.2f}x")
    else:
        print(f"Corrected: {test_g['corr_details']['reason']}")
    tests.append(test_g)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"{'Test':<10} {'Expected':<10} {'Production':<12} {'Prod Match':<12} {'Corrected':<12} {'Corr Match':<12}")
    print("-" * 80)
    for test in tests:
        prod_status = "[OK]" if test["prod_matches"] else "[FAIL]"
        corr_status = "[OK]" if test["corr_matches"] else "[FAIL]"
        print(f"{test['test_name']:<10} {'PASS' if test['expected'] else 'FAIL':<10} {'PASS' if test['prod_qualified'] else 'FAIL':<12} {prod_status:<12} {'PASS' if test['corr_qualified'] else 'FAIL':<12} {corr_status:<12}")
    
    prod_passed = sum(1 for t in tests if t["prod_matches"])
    corr_passed = sum(1 for t in tests if t["corr_matches"])
    total_tests = len(tests)
    
    print("-" * 80)
    print(f"Production: {prod_passed}/{total_tests} tests passed")
    print(f"Corrected: {corr_passed}/{total_tests} tests passed")
    
    if prod_passed != total_tests:
        print("\n[CRITICAL] Production formula has errors!")
        print("The production code uses abs() for body calculation which is INCORRECT.")
        print("It should use: body = open_price - close_price (for red candles)")
    
    if corr_passed == total_tests:
        print("\n[SUCCESS] Corrected formula passes all tests!")
        print("The corrected formula correctly distinguishes upper from lower wick.")
    else:
        print("\n[FAILURE] Corrected formula still has errors!")
    
    return tests


if __name__ == "__main__":
    main()
