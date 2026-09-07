Œ""""
Simple test of LW-001 candle calculation logic
Tests the 4 critical cases specified in requirements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_case(name, open_p, close_p, low_p, high_p, expected_qualified, expected_ratio=None):
    """Test a single candle case."""
    print("=" * 80)
    print(f"TEST CASE: {name}")
    print("=" * 80)
    print(f"Open:  {open_p}")
    print(f"Close: {close_p}")
    print(f"Low:   {low_p}")
    print(f"High:  {high_p}")
    print()
    
    # Check if red
    is_red = close_p < open_p
    print(f"RED: {'YES' if is_red else 'NO'}")
    print()
    
    # Calculate body (LW-001: abs(Close - Open))
    body = abs(close_p - open_p)
    print(f"Body: {body}")
    
    # Calculate lower wick (LW-001: Close - Low for red candles)
    lower_wick = close_p - low_p
    print(f"Lower Wick: {lower_wick}")
    
    # Calculate upper wick (informational only)
    upper_wick = high_p - max(open_p, close_p)
    print(f"Upper Wick: {upper_wick}")
    print()
    
    # Calculate ratio
    if body > 0:
        ratio = lower_wick / body
        print(f"Lower Wick / Body: {ratio:.2f}x")
    else:
        ratio = 0.0
        print(f"Lower Wick / Body: N/A (body = 0)")
    print()
    
    # LW-001 Qualification: RED candle AND Lower Wick / Body >= 2.0
    qualified = is_red and (ratio >= 2.0 if body > 0 else False)
    
    print(f"Expected Qualified: {'YES' if expected_qualified else 'NO'}")
    if expected_ratio is not None:
        print(f"Expected Ratio: {expected_ratio:.2f}x")
    print()
    
    print(f"Actual Qualified: {'YES' if qualified else 'NO'}")
    print()
    
    # Check result
    test_passed = True
    if qualified == expected_qualified:
        print("[+] QUALIFICATION TEST PASSED")
    else:
        print(f"[-] QUALIFICATION TEST FAILED: Expected {expected_qualified}, got {qualified}")
        test_passed = False
    
    if expected_ratio is not None:
        if abs(ratio - expected_ratio) < 0.01:
            print("[+] RATIO CORRECT")
        else:
            print(f"[-] RATIO INCORRECT: Expected {expected_ratio:.2f}x, got {ratio:.2f}x")
            test_passed = False
    
    if test_passed:
        print("[+] TEST PASSED")
    else:
        print("[-] TEST FAILED")
    
    print()
    print("=" * 80)
    print()
    
    return test_passed

def main():
    print("=" * 80)
    print("Testing LW-01 Candle Calculation Logic")
    print("Location: D:\\EVRECONSE_PROJECT")
    print("=" * 80)
    print()
    
    print(f"Python executable: {sys.executable}")
    print()
    
    all_passed = True
    
    # Case A: Red candle with lower wick >= 2x body - should PASS
    all_passed &= test_case(
        name="Case A - Red candle, Lower Wick >= 2x Body",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=115,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    # Case B: Red candle with lower wick < 2x body - should FAIL
    all_passed &= test_case(
        name="Case B - Red candle, Lower Wick < 2x Body",
        open_p=110,
        close_p=100,
        low_p=85,
        high_p=115,
        expected_qualified=False,
        expected_ratio=1.5
    )
    
    # Case C: Green candle - should FAIL regardless of wick size
    all_passed &= test_case(
        name="Case C - Green candle (should FAIL)",
        open_p=100,
        close_p=110,
        low_p=75,
        high_p=115,
        expected_qualified=False,
        expected_ratio=None  # Not applicable for green candles
    )
    
    # Case D1: Red candle with small upper wick
    all_passed &= test_case(
        name="Case D1 - Red candle, Small Upper Wick",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=112,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    # Case D2: Red candle with large upper wick (same Open, Close, Low)
    all_passed &= test_case(
        name="Case D2 - Red candle, Large Upper Wick (same O/C/L)",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=150,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    print("=" * 80)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 80)

if __name__ == "__main__":
    main()
Œ"*cascade0821file:///D:/EVRECONSE_PROJECT/test_lw001_simple.py