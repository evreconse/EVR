#!/usr/bin/env python3
"""
Debug Analysis: Investigate why only 5 signals were found

Hypothesis: The limit=1000 parameter is restricting data to only ~10 days instead of 60 days.
Expected candles for 60 days at 15m: 60 * 24 * 4 = 5760 candles
Actual with limit=1000: 1000 candles = ~10.4 days
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from datetime import datetime, UTC, timedelta


def calculate_expected_candles(days=60, interval_minutes=15):
    """Calculate expected number of candles for a time period."""
    minutes_per_day = 24 * 60
    candles_per_day = minutes_per_day / interval_minutes
    total_candles = days * candles_per_day
    return int(total_candles)


def calculate_days_from_candles(candles, interval_minutes=15):
    """Calculate how many days of data a given number of candles represents."""
    minutes_per_candle = interval_minutes
    total_minutes = candles * minutes_per_candle
    days = total_minutes / (24 * 60)
    return days


def main():
    print("="*100)
    print("DEBUG ANALYSIS: LIMIT PARAMETER IMPACT")
    print("="*100)
    print()
    
    # Expected vs Actual
    expected_candles = calculate_expected_candles(days=60, interval_minutes=15)
    actual_candles = 1000  # limit used in stage4_mass_search.py
    
    print(f"Expected candles for 60 days at 15m interval:")
    print(f"  60 days * 24 hours/day * 4 candles/hour = {expected_candles} candles")
    print()
    
    print(f"Actual candles fetched with limit=1000:")
    print(f"  {actual_candles} candles")
    print()
    
    actual_days = calculate_days_from_candles(actual_candles, interval_minutes=15)
    print(f"Actual days covered by 1000 candles:")
    print(f"  1000 candles * 15 minutes / (24 * 60) = {actual_days:.2f} days")
    print()
    
    print("="*100)
    print("ROOT CAUSE IDENTIFIED")
    print("="*100)
    print()
    print("The limit=1000 parameter restricts data to only ~10.4 days instead of 60 days.")
    print()
    print("This explains why:")
    print("  1. Only 5 new signals were found (instead of many more)")
    print("  2. All signals are from 22.08.2026 (only the last ~10 days were processed)")
    print("  3. June and July data were never fetched")
    print()
    print("="*100)
    print("SOLUTION")
    print("="*100)
    print()
    print("Option 1: Remove the limit parameter entirely")
    print("  - Let the pagination logic fetch all data within the time range")
    print()
    print("Option 2: Set a much higher limit")
    print("  - limit=6000 to cover 60 days at 15m interval")
    print()
    print("Option 3: Implement proper pagination without total limit")
    print("  - Only use time-based pagination (start_time, end_time)")
    print("  - Remove the overall limit constraint")
    print()
    print("Recommended: Option 1 or 3 - remove limit parameter for time-range queries")


if __name__ == "__main__":
    main()
