#!/usr/bin/env python3
"""
Simple diagnostic test to verify LW-001 formula calculations.
"""

def check_lw001_current(open_price, high_price, low_price, close_price):
    """Current implementation from find_10_signals.py"""
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    # Calculate body and lower wick for red candle
    body = open_price - close_price  # Positive for red candle
    lower_wick = close_price - low_price
    
    if body == 0:
        return False, {"reason": "Zero body"}
    
    # Condition 2: Lower Wick / Body >= 2.0
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


def check_lw001_user_spec(open_price, high_price, low_price, close_price):
    """User's specified formula"""
    # Body = abs(Open - Close)
    body = abs(open_price - close_price)
    
    # Lower Wick = min(Open, Close) - Low
    lower_wick = min(open_price, close_price) - low_price
    
    # Upper Wick = High - max(Open, Close)
    upper_wick = high_price - max(open_price, close_price)
    
    # Ratio = Lower Wick / Body
    ratio = lower_wick / body if body > 0 else 0.0
    
    # Qualified = (Close < Open) AND (Ratio >= 2.0)
    is_red = close_price < open_price
    qualified = is_red and ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


# Test with BCH-USDT data from the report
print("="*80)
print("TESTING BCH-USDT CANDLE")
print("="*80)
print("From report: Open=214.85, High=214.93, Low=214.52, Close=214.70")
print()

open_price = 214.85
high_price = 214.93
low_price = 214.52
close_price = 214.70

print("OHLC:")
print(f"  Open: {open_price}")
print(f"  High: {high_price}")
print(f"  Low: {low_price}")
print(f"  Close: {close_price}")
print()

# Current implementation
qualified_current, details_current = check_lw001_current(open_price, high_price, low_price, close_price)
print("CURRENT IMPLEMENTATION:")
print(f"  Red Candle: {details_current['is_red']}")
print(f"  Body (Open - Close): {details_current['body']:.4f}")
print(f"  Lower Wick (Close - Low): {details_current['lower_wick']:.4f}")
print(f"  Ratio: {details_current['ratio']:.2f}x")
print(f"  Qualified: {details_current['qualified']}")
print()

# User's specification
qualified_user, details_user = check_lw001_user_spec(open_price, high_price, low_price, close_price)
print("USER SPECIFICATION:")
print(f"  Red Candle: {details_user['is_red']}")
print(f"  Body (abs(Open - Close)): {details_user['body']:.4f}")
print(f"  Lower Wick (min(Open, Close) - Low): {details_user['lower_wick']:.4f}")
print(f"  Upper Wick (High - max(Open, Close)): {details_user['upper_wick']:.4f}")
print(f"  Ratio: {details_user['ratio']:.2f}x")
print(f"  Qualified: {details_user['qualified']}")
print()

print("="*80)
print("COMPARISON")
print("="*80)
print(f"Current ratio: {details_current['ratio']:.2f}x")
print(f"User ratio: {details_user['ratio']:.2f}x")
print(f"Match: {abs(details_current['ratio'] - details_user['ratio']) < 0.01}")
print()

# Test with a green candle to verify min/max logic
print("="*80)
print("TESTING GREEN CANDLE (should FAIL)")
print("="*80)
print("Open=99, High=101, Low=97, Close=100")
print()

qualified_green, details_green = check_lw001_user_spec(99, 101, 97, 100)
print(f"  Red Candle: {details_green['is_red']}")
print(f"  Body: {details_green['body']:.4f}")
print(f"  Lower Wick: {details_green['lower_wick']:.4f}")
print(f"  Ratio: {details_green['ratio']:.2f}x")
print(f"  Qualified: {details_green['qualified']}")
print()

# Test with a perfect hammer
print("="*80)
print("TESTING PERFECT HAMMER (should PASS)")
print("="*80)
print("Open=100, High=101, Low=97, Close=99")
print()

qualified_hammer, details_hammer = check_lw001_user_spec(100, 101, 97, 99)
print(f"  Red Candle: {details_hammer['is_red']}")
print(f"  Body: {details_hammer['body']:.4f}")
print(f"  Lower Wick: {details_hammer['lower_wick']:.4f}")
print(f"  Ratio: {details_hammer['ratio']:.2f}x")
print(f"  Qualified: {details_hammer['qualified']}")
