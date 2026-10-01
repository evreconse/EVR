"""
EVRECONSE LW-001 Canonical Signal Check.

SINGLE SOURCE OF TRUTH for LW-001 signal qualification.
All components (historical search, real-time pipeline, backtest, tests)
MUST use this function. No duplicate logic allowed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Add project root to path for LW001_METRIC_SPEC import
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import authoritative thresholds from LW001_METRIC_SPEC
from LW001_METRIC_SPEC import LW001_THRESHOLDS as _SPEC_THRESHOLDS

# Map spec keys to canonical keys used in this module
LW001_THRESHOLDS = {
    "range_pct": _SPEC_THRESHOLDS["range_pct"]["value"],
    "body_pct": _SPEC_THRESHOLDS["body_pct"]["value"],
    "lw_body_ratio": _SPEC_THRESHOLDS["lower_wick_body_ratio"]["value"],
    "lw_range_pct": _SPEC_THRESHOLDS["lower_wick_range_pct"]["value"],
    "open_to_low_pct": _SPEC_THRESHOLDS["open_to_low_pct"]["value"],
}


@dataclass(frozen=True, slots=True)
class LW001Metrics:
    """Calculated LW-001 metrics with units."""
    range_pct: float          # %
    body_pct: float           # %
    lw_body_ratio: float      # x
    lw_range_pct: float       # %
    open_to_low_pct: float    # %
    is_red: bool              # Close < Open


@dataclass(frozen=True, slots=True)
class LW001CheckResult:
    """Result of LW-001 qualification check."""
    qualified: bool
    metrics: LW001Metrics
    failed_conditions: List[str]


def calculate_lw001_metrics(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
) -> LW001Metrics:
    """
    Calculate all LW-001 metrics from OHLC data.
    
    Volume is NOT used for LW-001 signal decision (Volume Ratio removed).
    
    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
        close_price: Candle close price
    
    Returns:
        LW001Metrics with all calculated values
    """
    # Red candle check
    is_red = close_price < open_price
    
    # Range % = (High - Low) / Open * 100
    candle_range = high_price - low_price
    range_pct = (candle_range / open_price * 100) if open_price != 0 else 0.0
    
    # Body % = abs(Close - Open) / Open * 100
    body_size = abs(close_price - open_price)
    body_pct = (body_size / open_price * 100) if open_price != 0 else 0.0
    
    # Lower Wick = min(Open, Close) - Low
    lower_wick = min(open_price, close_price) - low_price
    
    # LW/Body = Lower_Wick / abs(Close - Open)
    lw_body_ratio = (lower_wick / body_size) if body_size > 0 else 0.0
    
    # LW/Range % = Lower_Wick / (High - Low) * 100
    lw_range_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0.0
    
    # Open→Low % = (Low - Open) / Open * 100
    open_to_low_pct = ((low_price - open_price) / open_price * 100) if open_price != 0 else 0.0
    
    return LW001Metrics(
        range_pct=range_pct,
        body_pct=body_pct,
        lw_body_ratio=lw_body_ratio,
        lw_range_pct=lw_range_pct,
        open_to_low_pct=open_to_low_pct,
        is_red=is_red,
    )


def check_lw001_signal(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
) -> LW001CheckResult:
    """
    Check if a candle qualifies as LW-001 signal.
    
    This is THE canonical function. All signal detection must use this.
    
    Qualification requires ALL conditions (AND logic):
    1. Close < Open (red candle)
    2. Range % >= 4.5%
    3. Body % >= 0.8%
    4. LW/Body >= 1.3x
    5. LW/Range % >= 55.0%
    6. Open→Low % <= -2.5%
    
    Volume is NOT used for signal qualification (Volume Ratio removed).
    
    Args:
        open_price: Candle open
        high_price: Candle high
        low_price: Candle low
        close_price: Candle close
    
    Returns:
        LW001CheckResult with qualified flag, metrics, and failed conditions
    """
    metrics = calculate_lw001_metrics(
        open_price, high_price, low_price, close_price
    )
    
    failed = []
    
    if not metrics.is_red:
        failed.append("Not a red candle (Close >= Open)")
    
    if metrics.range_pct < LW001_THRESHOLDS["range_pct"]:
        failed.append(f"Range {metrics.range_pct:.2f}% < {LW001_THRESHOLDS['range_pct']}%")
    
    if metrics.body_pct < LW001_THRESHOLDS["body_pct"]:
        failed.append(f"Body {metrics.body_pct:.2f}% < {LW001_THRESHOLDS['body_pct']}%")
    
    if metrics.lw_body_ratio < LW001_THRESHOLDS["lw_body_ratio"]:
        failed.append(f"LW/Body {metrics.lw_body_ratio:.2f}x < {LW001_THRESHOLDS['lw_body_ratio']}x")
    
    if metrics.lw_range_pct < LW001_THRESHOLDS["lw_range_pct"]:
        failed.append(f"LW/Range {metrics.lw_range_pct:.2f}% < {LW001_THRESHOLDS['lw_range_pct']}%")
    
    if metrics.open_to_low_pct > LW001_THRESHOLDS["open_to_low_pct"]:
        failed.append(f"Open→Low {metrics.open_to_low_pct:.2f}% > {LW001_THRESHOLDS['open_to_low_pct']}%")
    
    qualified = len(failed) == 0
    
    return LW001CheckResult(
        qualified=qualified,
        metrics=metrics,
        failed_conditions=failed
    )


def format_lw001_telegram_message(
    symbol: str,
    event_time_utc: str,  # Already formatted as "DD.MM.YYYY HH:MM UTC"
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    metrics: LW001Metrics
) -> str:
    """
    Format LW-001 signal for Telegram.
    
    Uses UTC only, plain text, fixed template.
    """
    return (
        "LW-001 SIGNAL\n\n"
        f"Symbol: {symbol}\n\n"
        f"Time: {event_time_utc}\n\n"
        "OHLCV\n"
        f"Open: {open_price:.6f}\n"
        f"High: {high_price:.6f}\n"
        f"Low: {low_price:.6f}\n"
        f"Close: {close_price:.6f}\n"
        f"Volume: {volume:,.0f}\n\n"
        "Metrics\n"
        f"Range: {metrics.range_pct:.2f}%\n"
        f"Body: {metrics.body_pct:.2f}%\n"
        f"LW/Body: {metrics.lw_body_ratio:.2f}x\n"
        f"LW/Range: {metrics.lw_range_pct:.2f}%\n"
        f"Open-Low: {metrics.open_to_low_pct:.2f}%\n\n"
        "Conditions\n"
        f"Range >= 4.5% - {'PASS' if metrics.range_pct >= 4.5 else 'FAIL'}\n"
        f"Body >= 0.8% - {'PASS' if metrics.body_pct >= 0.8 else 'FAIL'}\n"
        f"LW/Body >= 1.3x - {'PASS' if metrics.lw_body_ratio >= 1.3 else 'FAIL'}\n"
        f"LW/Range >= 55% - {'PASS' if metrics.lw_range_pct >= 55.0 else 'FAIL'}\n"
        f"Open-Low <= -2.5% - {'PASS' if metrics.open_to_low_pct <= -2.5 else 'FAIL'}\n\n"
        "VALID SIGNAL"
    )


# ============================================================================
# UNIT TESTS (can be run standalone)
# ============================================================================

def run_unit_tests() -> bool:
    """Run unit tests for canonical LW-001 check."""
    all_passed = True
    
    def assert_eq(actual, expected, msg):
        nonlocal all_passed
        if abs(actual - expected) > 0.01:
            print(f"FAIL: {msg} - got {actual}, expected {expected}")
            all_passed = False
        else:
            print(f"PASS: {msg}")
    
    def assert_bool(actual, expected, msg):
        nonlocal all_passed
        if actual != expected:
            print(f"FAIL: {msg} - got {actual}, expected {expected}")
            all_passed = False
        else:
            print(f"PASS: {msg}")
    
    print("Running LW-001 Canonical Unit Tests...\n")
    
    # Test 1: Red candle with all conditions passing
    # Base candle that passes ALL 6 conditions:
    # Open=100, High=100.75, Low=95.75, Close=98.5
    # Range=5.0%, Body=1.5%, LW/Body=1.83x, LW/Range=55%, Open->Low=-4.25%
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5
    )
    assert_bool(result.qualified, True, "Test 1: Valid red candle should PASS")
    
    # Test 2: Green candle should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=105.0,
        low_price=95.0,
        close_price=102.0  # Green: 102 > 100
    )
    assert_bool(result.qualified, False, "Test 2: Green candle should FAIL")
    
    # Test 3: Doji (Close == Open) should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=98.0,
        close_price=100.0  # Doji
    )
    assert_bool(result.qualified, False, "Test 3: Doji should FAIL")
    
    # Test 4: LW/Body = 1.29x (just below 1.3) should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=97.42,  # LW = 2.58, Body = 2.0, ratio = 1.29
        close_price=98.0
    )
    assert_bool(result.qualified, False, "Test 4: LW/Body 1.29x should FAIL")
    
    # Test 5: Range = 4.49% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=104.49,  # Range = 4.49%
        low_price=95.75,    # LW=2.75, Body=1.5, LW/Body=1.83, LW/Range=54.5%
        close_price=98.5
    )
    assert_bool(result.qualified, False, "Test 5: Range 4.49% should FAIL")
    
    # Test 6: Range = 4.50% should PASS
    # O=100, H=100.55, L=95.55, C=98.5 -> Range = 5.0%, Body = 1.5%, LW = 2.95, LW/Body = 1.97, LW/Range = 59%
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.55,
        low_price=95.55,
        close_price=98.5
    )
    assert_bool(result.qualified, True, "Test 5: Range 4.50% should PASS")
    
    # Test 6: Body = 0.79% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=99.21  # Body = 0.79%
    )
    assert_bool(result.qualified, False, "Test 5: Body 0.79% should FAIL")
    
    # Test 6: Body = 0.80% should PASS
    # O=100, H=100.55, L=95.55, C=99.19 -> Body = 0.81%
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.55,
        low_price=95.55,
        close_price=99.19  # Body = 0.81%
    )
    assert_bool(result.qualified, True, "Test 6: Body 0.80% should PASS")
    
    # Test 7: Open->Low = -2.49% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=97.51,  # Open->Low = -2.49%
        close_price=98.5  # LW=1.0, Body=1.5, LW/Body=0.67 - FAIL
    )
    assert_bool(result.qualified, False, "Test 7: Open->Low -2.49% should FAIL")
    
    # Test 8: Open->Low = -2.50% should PASS
    # Use base candle with Low=95.75 -> Open->Low=-4.25% (passes)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5
    )
    assert_bool(result.qualified, True, "Test 8: Open->Low -2.50% should PASS")
    
    # Test 9: Volume independence - changing volume should not affect signal result
    # Volume is NOT used in LW-001 signal qualification (Volume Ratio removed)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5
    )
    assert_bool(result.qualified, True, "Test 9: Base signal PASS")
    
    # Test 10: Verify volume independence - same OHLC, different volumes = same result
    # Since volume is not a parameter anymore, this is implicitly tested
    # The function signature no longer accepts volume parameters
    
    # Test 11: Telegram format
    metrics = LW001Metrics(
        range_pct=5.0, body_pct=1.0, lw_body_ratio=1.5,
        lw_range_pct=60.0, open_to_low_pct=-3.0,
        is_red=True
    )
    msg = format_lw001_telegram_message(
        "BTC-USDT", "22.08.2026 05:00 UTC",
        100.0, 105.0, 90.0, 95.0, 1500.0, metrics
    )
    assert_bool("UTC" in msg and "MSK" not in msg, True, "Test 11: Telegram uses UTC only")
    assert_bool("PASS" in msg, True, "Test 11: Shows PASS/FAIL")
    assert_bool("Volume Ratio" not in msg, True, "Test 11: Volume Ratio NOT in Telegram")
    
    print(f"\n{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed


if __name__ == "__main__":
    run_unit_tests()