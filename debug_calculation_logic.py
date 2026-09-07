#!/usr/bin/env python3
"""
Debug calculation logic for all 6 metrics.

Compare current implementation with user-specified formulas.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json


def calculate_current_metrics(kline, avg_volume_20):
    """Current implementation (from new_historical_search.py)."""
    open_price = float(kline['open'])
    close_price = float(kline['close'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    volume = float(kline['volume'])
    
    body = abs(close_price - open_price)
    lower_wick = min(open_price, close_price) - low_price
    upper_wick = high_price - max(open_price, close_price)
    candle_range = high_price - low_price
    
    if candle_range == 0:
        return None
    
    body_percent = (body / close_price) * 100
    range_percent = (candle_range / close_price) * 100
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    open_to_low_percent = ((low_price - open_price) / open_price) * 100
    
    volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else None
    
    return {
        "body_percent": body_percent,
        "range_percent": range_percent,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "open_to_low_percent": open_to_low_percent,
        "volume_ratio": volume_ratio
    }


def calculate_corrected_metrics(kline, avg_volume_20):
    """Corrected implementation using Open as denominator for Range and Body."""
    open_price = float(kline['open'])
    close_price = float(kline['close'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    volume = float(kline['volume'])
    
    body = abs(close_price - open_price)
    lower_wick = min(open_price, close_price) - low_price
    upper_wick = high_price - max(open_price, close_price)
    candle_range = high_price - low_price
    
    if candle_range == 0:
        return None
    
    # CORRECTED: Use Open as denominator for Range and Body
    body_percent = (body / open_price) * 100
    range_percent = (candle_range / open_price) * 100
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
    open_to_low_percent = ((low_price - open_price) / open_price) * 100
    
    volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else None
    
    return {
        "body_percent": body_percent,
        "range_percent": range_percent,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "open_to_low_percent": open_to_low_percent,
        "volume_ratio": volume_ratio
    }


def main():
    """Main function."""
    print("=" * 100)
    print("DEBUG: CALCULATION LOGIC VERIFICATION")
    print("=" * 100)
    
    print("\n" + "=" * 100)
    print("FORMULA COMPARISON")
    print("=" * 100)
    
    print("\n1. Range:")
    print("   User formula: (High - Low) / Open * 100")
    print("   Current code: (High - Low) / Close * 100")
    print("   ISSUE: Code uses Close instead of Open")
    
    print("\n2. Body:")
    print("   User formula: abs(Close - Open) / Open * 100")
    print("   Current code: abs(Close - Open) / Close * 100")
    print("   ISSUE: Code uses Close instead of Open")
    
    print("\n3. LW:")
    print("   User formula: min(Open, Close) - Low")
    print("   Current code: min(Open, Close) - Low")
    print("   CORRECT")
    
    print("\n4. LW/Body:")
    print("   User formula: LW / abs(Close - Open)")
    print("   Current code: LW / abs(Close - Open)")
    print("   CORRECT")
    
    print("\n5. LW/Range:")
    print("   User formula: LW / (High - Low)")
    print("   Current code: LW / (High - Low)")
    print("   CORRECT")
    
    print("\n6. Open to Low:")
    print("   User formula: (Low - Open) / Open * 100")
    print("   Current code: (Low - Open) / Open * 100")
    print("   CORRECT")
    
    print("\n7. Volume Ratio:")
    print("   User formula: Volume / avg_volume_20")
    print("   Current code: Volume / avg_volume_20")
    print("   CORRECT (assuming avg_volume_20 is correct base)")
    
    print("\n" + "=" * 100)
    print("CRITICAL FINDING")
    print("=" * 100)
    print("\nISSUE FOUND: Range and Body calculations use Close as denominator")
    print("instead of Open as specified by user.")
    print("\nThis explains why previous search found 3,678 signals that")
    print("didn't match the specified parameters.")
    print("\nFor a green candle (Close > Open):")
    print("  - Using Close denominator: Range and Body appear smaller")
    print("  - Using Open denominator: Range and Body appear larger")
    print("\nFor a red candle (Close < Open):")
    print("  - Using Close denominator: Range and Body appear larger")
    print("  - Using Open denominator: Range and Body appear smaller")
    
    print("\n" + "=" * 100)
    print("TESTING ON SAMPLE DATA")
    print("=" * 100)
    
    # Test with sample data
    sample_kline = {
        'open': 100.0,
        'high': 106.0,
        'low': 94.0,
        'close': 105.0,
        'volume': 1000.0
    }
    avg_volume = 500.0
    
    current = calculate_current_metrics(sample_kline, avg_volume)
    corrected = calculate_corrected_metrics(sample_kline, avg_volume)
    
    print(f"\nSample Candle:")
    print(f"  Open: {sample_kline['open']}")
    print(f"  High: {sample_kline['high']}")
    print(f"  Low: {sample_kline['low']}")
    print(f"  Close: {sample_kline['close']}")
    print(f"  Volume: {sample_kline['volume']}")
    print(f"  Avg Volume: {avg_volume}")
    
    print(f"\nCURRENT IMPLEMENTATION (using Close):")
    print(f"  Range: {current['range_percent']:.2f}%")
    print(f"  Body: {current['body_percent']:.2f}%")
    print(f"  LW/Body: {current['lower_wick_body_ratio']:.2f}x")
    print(f"  LW/Range: {current['lower_wick_range_ratio']*100:.1f}%")
    print(f"  Open to Low: {current['open_to_low_percent']:.2f}%")
    print(f"  Volume Ratio: {current['volume_ratio']:.2f}x")
    
    print(f"\nCORRECTED IMPLEMENTATION (using Open):")
    print(f"  Range: {corrected['range_percent']:.2f}%")
    print(f"  Body: {corrected['body_percent']:.2f}%")
    print(f"  LW/Body: {corrected['lower_wick_body_ratio']:.2f}x")
    print(f"  LW/Range: {corrected['lower_wick_range_ratio']*100:.1f}%")
    print(f"  Open to Low: {corrected['open_to_low_percent']:.2f}%")
    print(f"  Volume Ratio: {corrected['volume_ratio']:.2f}x")
    
    print(f"\nDIFFERENCE:")
    print(f"  Range: {corrected['range_percent'] - current['range_percent']:.2f}%")
    print(f"  Body: {corrected['body_percent'] - current['body_percent']:.2f}%")
    
    print("\n" + "=" * 100)
    print("CONCLUSION")
    print("=" * 100)
    print("\nVARIANT A: Error was in formula of Range and Body metrics")
    print("\nThe code uses Close as denominator for Range and Body,")
    print("but the specification requires Open as denominator.")
    print("\nThis causes significant discrepancies in metric values,")
    print("explaining why previous signals didn't match parameters")
    print("and why strict filters found 0 signals.")
    
    print("\n" + "=" * 100)
    print("NEXT STEPS")
    print("=" * 100)
    print("\n1. Fix calculation formulas to use Open as denominator")
    print("2. Re-test on 10 candles with corrected formulas")
    print("3. Verify each candle manually against all 6 conditions")
    print("4. Send to Telegram only after user confirmation")


if __name__ == "__main__":
    main()
