#!/usr/bin/env python3
"""
Diagnostic test to investigate zero-body candles.
"""

def check_lw001_corrected(open_price, high_price, low_price, close_price):
    """User's specified formula"""
    # Body = abs(Open - Close)
    body = abs(open_price - close_price)
    
    # Lower Wick = min(Open, Close) - Low
    lower_wick = min(open_price, close_price) - low_price
    
    # Calculate ratio
    ratio = lower_wick / body if body > 0 else 0.0
    
    # Qualified = (Close < Open) AND (Ratio >= 2.0)
    is_red = close_price < open_price
    qualified = is_red and ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


# Test with VET-USDT data (body = 0.0000, ratio = 4.00x)
print("="*80)
print("TESTING VET-USDT CANDLE (body=0.0000, ratio=4.00x)")
print("="*80)

# From the output: Open=0.0047, High=0.0047, Low=0.0047, Close=0.0047
open_price = 0.0047
high_price = 0.0047
low_price = 0.0047
close_price = 0.0047

qualified, details = check_lw001_corrected(open_price, high_price, low_price, close_price)

print(f"Open: {open_price}")
print(f"High: {high_price}")
print(f"Low: {low_price}")
print(f"Close: {close_price}")
print()
print(f"Body: {details['body']:.6f}")
print(f"Lower Wick: {details['lower_wick']:.6f}")
print(f"Ratio: {details['ratio']:.2f}x")
print(f"Qualified: {details['qualified']}")
print()

# This is a doji - all prices are the same
# Body = 0.0000
# Lower Wick = 0.0000
# Ratio = 0.0 / 0.0 = 0.0 (due to body > 0 check)
# But the output showed ratio = 4.00x

# Let me check what the actual OHLC might be
print("="*80)
print("TESTING WITH TINY BODY (noise candle)")
print("="*80)

# Maybe the actual candle has tiny differences
open_price = 0.004700
high_price = 0.004700
low_price = 0.004699
close_price = 0.004699

qualified, details = check_lw001_corrected(open_price, high_price, low_price, close_price)

print(f"Open: {open_price}")
print(f"High: {high_price}")
print(f"Low: {low_price}")
print(f"Close: {close_price}")
print()
print(f"Body: {details['body']:.6f}")
print(f"Lower Wick: {details['lower_wick']:.6f}")
print(f"Ratio: {details['ratio']:.2f}x")
print(f"Qualified: {details['qualified']}")
print()

print("CONCLUSION:")
print("Tiny bodies produce huge ratios but are visually noise/doji.")
print("Need to add minimum body size filter to exclude these.")
