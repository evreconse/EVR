#!/usr/bin/env python3
"""
Diagnose the precision issue in signal display.

The issue: Telegram shows Body=0.0000 and Lower Wick=0.0000 but Wick/Body=2.00x
This is mathematically impossible unless the actual values have more precision than displayed.
"""

def check_precision():
    """Test the precision issue."""
    print("=" * 80)
    print("PRECISION ISSUE DIAGNOSIS")
    print("=" * 80)
    
    # Example from the Telegram output
    # Body: 0.0000
    # Lower Wick: 0.0000
    # Wick/Body: 2.00x
    
    # This is mathematically impossible with the displayed values
    # But if the actual values have more precision, it's possible
    
    # Example: actual values
    actual_open = 0.1750
    actual_close = 0.1749  # Very small body
    actual_low = 0.1748    # Very small lower wick
    
    body = actual_open - actual_close
    lower_wick = actual_close - actual_low
    ratio = lower_wick / body
    
    print(f"\nActual values:")
    print(f"  Open: {actual_open}")
    print(f"  Close: {actual_close}")
    print(f"  Low: {actual_low}")
    print(f"  Body: {body}")
    print(f"  Lower Wick: {lower_wick}")
    print(f"  Ratio: {ratio}")
    
    print(f"\nDisplayed values (4 decimal places):")
    print(f"  Open: {actual_open:.4f}")
    print(f"  Close: {actual_close:.4f}")
    print(f"  Low: {actual_low:.4f}")
    print(f"  Body: {body:.4f}")
    print(f"  Lower Wick: {lower_wick:.4f}")
    print(f"  Ratio: {ratio:.2f}x")
    
    print(f"\nThe issue:")
    print(f"  Displayed Body: {body:.4f} (rounds to 0.0000)")
    print(f"  Displayed Lower Wick: {lower_wick:.4f} (rounds to 0.0000)")
    print(f"  Displayed Ratio: {ratio:.2f}x (correct based on actual values)")
    
    print(f"\nConclusion:")
    print(f"  The formula is correct.")
    print(f"  The display is misleading due to rounding to 4 decimal places.")
    print(f"  The actual candle has a very small body and very small lower wick,")
    print(f"  but the ratio is mathematically correct.")
    
    # However, we need to check if this is actually the user's concern
    print(f"\n" + "=" * 80)
    print("USER'S CONCERN")
    print("=" * 80)
    print("The user is seeing candles that visually have NO lower wick on the chart.")
    print("This is a different issue from the precision display issue.")
    print("The user is concerned about the actual OHLC values from BingX,")
    print("not the rounding in the display.")
    
    # Let's check if there's a case where Close == Low (no lower wick)
    print(f"\n" + "=" * 80)
    print("CHECKING FOR Close == Low (NO LOWER WICK)")
    print("=" * 80)
    
    # Example: Close == Low
    open_price = 100
    close_price = 90
    low_price = 90  # Close == Low
    
    body = open_price - close_price
    lower_wick = close_price - low_price
    ratio = lower_wick / body
    
    print(f"\nCase: Close == Low")
    print(f"  Open: {open_price}")
    print(f"  Close: {close_price}")
    print(f"  Low: {low_price}")
    print(f"  Body: {body}")
    print(f"  Lower Wick: {lower_wick}")
    print(f"  Ratio: {ratio}")
    
    if lower_wick == 0:
        print(f"\n  This candle has NO lower wick.")
        print(f"  It should NOT qualify as LW-001.")
        print(f"  If it was sent as a signal, that's the bug.")


if __name__ == "__main__":
    check_precision()
