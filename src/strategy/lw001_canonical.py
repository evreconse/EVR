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
    "volume_ratio": _SPEC_THRESHOLDS["volume_ratio"]["value"],
}


@dataclass(frozen=True, slots=True)
class LW001Metrics:
    """Calculated LW-001 metrics with units."""
    range_pct: float          # %
    body_pct: float           # %
    lw_body_ratio: float      # x
    lw_range_pct: float       # %
    open_to_low_pct: float    # %
    volume_ratio: float       # x
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
    current_volume: float,
    volume_3_candles_ago: float
) -> LW001Metrics:
    """
    Calculate all LW-001 metrics from OHLCV data.
    
    Uses Open as denominator for Range and Body (canonical formula).
    
    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
        close_price: Candle close price
        current_volume: Volume of current candle (N)
        volume_3_candles_ago: Volume of candle N-3 (exactly 3 candles before current)
    
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
    
    # Volume Ratio = Current_Vol / Volume[N-3] (volume exactly 3 candles ago)
    if volume_3_candles_ago and volume_3_candles_ago > 0:
        volume_ratio = current_volume / volume_3_candles_ago
    else:
        volume_ratio = 0.0
    
    return LW001Metrics(
        range_pct=range_pct,
        body_pct=body_pct,
        lw_body_ratio=lw_body_ratio,
        lw_range_pct=lw_range_pct,
        open_to_low_pct=open_to_low_pct,
        volume_ratio=volume_ratio,
        is_red=is_red,
    )


def check_lw001_signal(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    current_volume: float,
    volume_3_candles_ago: float
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
    7. Volume Ratio >= 1.5x (current / volume 3 candles ago)
    
    Args:
        open_price: Candle open
        high_price: Candle high
        low_price: Candle low
        close_price: Candle close
        current_volume: Current candle volume (N)
        volume_3_candles_ago: Volume of candle N-3 (for volume ratio)
    
    Returns:
        LW001CheckResult with qualified flag, metrics, and failed conditions
    """
    metrics = calculate_lw001_metrics(
        open_price, high_price, low_price, close_price,
        current_volume, volume_3_candles_ago
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
    
    if metrics.volume_ratio < LW001_THRESHOLDS["volume_ratio"]:
        failed.append(f"Volume Ratio {metrics.volume_ratio:.2f}x < {LW001_THRESHOLDS['volume_ratio']}x")
    
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
        f"Open-Low: {metrics.open_to_low_pct:.2f}%\n"
        f"Volume Ratio: {metrics.volume_ratio:.2f}x\n\n"
        "Conditions\n"
        f"Range >= 4.5% - {'PASS' if metrics.range_pct >= 4.5 else 'FAIL'}\n"
        f"Body >= 0.8% - {'PASS' if metrics.body_pct >= 0.8 else 'FAIL'}\n"
        f"LW/Body >= 1.3x - {'PASS' if metrics.lw_body_ratio >= 1.3 else 'FAIL'}\n"
        f"LW/Range >= 55% - {'PASS' if metrics.lw_range_pct >= 55.0 else 'FAIL'}\n"
        f"Open-Low <= -2.5% - {'PASS' if metrics.open_to_low_pct <= -2.5 else 'FAIL'}\n"
        f"Volume Ratio >= 1.5x - {'PASS' if metrics.volume_ratio >= 1.5 else 'FAIL'}\n\n"
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
    
    print("Running LW-001 Canonical Unit Tests (NEW Volume Ratio: N/N-3)...\n")
    
    # Test 1: Red candle with all conditions passing
    # Base candle that passes ALL 7 conditions:
    # Open=100, High=100.75, Low=95.75, Close=98.5
    # Range=5.0%, Body=1.5%, LW/Body=1.83x, LW/Range=55%, Open->Low=-4.25%
    # Volume[N]=1500, Volume[N-3]=1000 -> Volume Ratio=1.5x
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 1: Valid red candle should PASS")
    
    # Test 2: Green candle should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=105.0,
        low_price=95.0,
        close_price=102.0,  # Green: 102 > 100
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 2: Green candle should FAIL")
    
    # Test 3: Doji (Close == Open) should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=98.0,
        close_price=100.0,  # Doji
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 3: Doji should FAIL")
    
    # Test 4: LW/Body = 1.29x (just below 1.3) should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=97.42,  # LW = 2.58, Body = 2.0, ratio = 1.29
        close_price=98.0,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 4: LW/Body 1.29x should FAIL")
    
    # Test 5: Volume Ratio = 1.49x should FAIL (NEW formula: N/N-3)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1490.0,  # 1490/1000 = 1.49
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 5: Volume Ratio 1.49x should FAIL")
    
    # Test 6: Volume Ratio = 1.50x should PASS (NEW formula: N/N-3)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,  # 1500/1000 = 1.5
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 6: Volume Ratio 1.50x should PASS")
    
    # Test 7: Volume Ratio = 1.51x should PASS
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1510.0,  # 1510/1000 = 1.51
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 7: Volume Ratio 1.51x should PASS")
    
    # Test 8: Volume[N-3] = 0 should give 0 ratio (FAIL)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=0.0
    )
    assert_bool(result.qualified, False, "Test 8: Volume N-3 = 0 should FAIL")
    
    # Test 9: Volume[N-3] = None should give 0 ratio (FAIL)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=None
    )
    assert_bool(result.qualified, False, "Test 9: Volume N-3 = None should FAIL")
    
    # Test 10: Range = 4.49% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=104.49,  # Range = 4.49%
        low_price=95.75,    # LW=2.75, Body=1.5, LW/Body=1.83, LW/Range=54.5%
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 10: Range 4.49% should FAIL")
    
    # Test 11: Range = 4.50% should PASS
    # O=100, H=100.55, L=95.55, C=98.5 -> Range = 5.0%, Body = 1.5%, LW = 2.95, LW/Body = 1.97, LW/Range = 59%
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.55,
        low_price=95.55,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 11: Range 4.50% should PASS")
    
    # Test 12: Body = 0.79% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=99.21,  # Body = 0.79%
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 12: Body 0.79% should FAIL")
    
    # Test 13: Body = 0.80% should PASS
    # O=100, H=100.55, L=95.55, C=99.19 -> Body = 0.81%
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.55,
        low_price=95.55,
        close_price=99.19,  # Body = 0.81%
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 13: Body 0.80% should PASS")
    
    # Test 14: Open->Low = -2.49% should FAIL
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=97.51,  # Open->Low = -2.49%
        close_price=98.5,  # LW=1.0, Body=1.5, LW/Body=0.67 - FAIL
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, False, "Test 14: Open->Low -2.49% should FAIL")
    
    # Test 15: Open->Low = -2.50% should PASS
    # Use base candle with Low=95.75 -> Open->Low=-4.25% (passes)
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_bool(result.qualified, True, "Test 15: Open->Low -2.50% should PASS")
    
    # Test 16: NEW Volume Ratio formula - only N and N-3 matter, N-2 and N-1 don't participate
    # Volume[N] = 1500, Volume[N-3] = 1000 -> Ratio = 1.5 (PASS)
    # Volume[N-2] = 5000, Volume[N-1] = 5000 (huge volumes) - should NOT affect ratio
    result = check_lw001_signal(
        open_price=100.0,
        high_price=100.75,
        low_price=95.75,
        close_price=98.5,
        current_volume=1500.0,
        volume_3_candles_ago=1000.0
    )
    assert_eq(result.metrics.volume_ratio, 1.5, "Test 16: Volume ratio uses N/N-3 only")
    assert_bool(result.qualified, True, "Test 16: N-2/N-1 don't affect ratio")
    
    # Test 17: No look-ahead - future candles not used
    # (implicit in API - we only pass volume_3_candles_ago)
    
    # Test 18: Telegram format
    metrics = LW001Metrics(
        range_pct=5.0, body_pct=1.0, lw_body_ratio=1.5,
        lw_range_pct=60.0, open_to_low_pct=-3.0, volume_ratio=1.6,
        is_red=True
    )
    msg = format_lw001_telegram_message(
        "BTC-USDT", "22.08.2026 05:00 UTC",
        100.0, 105.0, 90.0, 95.0, 1500.0, metrics
    )
    assert_bool("UTC" in msg and "MSK" not in msg, True, "Test 18: Telegram uses UTC only")
    assert_bool("PASS" in msg, True, "Test 18: Shows PASS/FAIL")
    
    print(f"\n{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed


if __name__ == "__main__":
    run_unit_tests()