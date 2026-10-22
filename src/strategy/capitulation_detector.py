# ruff: noqa: T201
"""
EVRECONSE Capitulation/Absorption Signal Detector

New strategy: LONG candidates based on capitulation + absorption pattern.
Not a SHORT strategy - red candles indicate downside impulse that gets absorbed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path for config import
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import thresholds from config
from config.capitulation_thresholds import CAPITULATION_THRESHOLDS  # noqa: E402


@dataclass(frozen=True, slots=True)
class CapitulationMetrics:
    """Calculated metrics for capitulation/absorption detection."""
    # Basic OHLCV
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

    # Downside impulse
    range_pct: float          # (High - Low) / Open * 100
    open_to_low_pct: float    # (Low - Open) / Open * 100

    # Body
    body_pct: float           # abs(Close - Open) / Open * 100

    # Lower wick (absorption signal)
    lower_wick: float         # min(Open, Close) - Low
    lw_body_ratio: float      # Lower_Wick / abs(Close - Open)
    lw_range_pct: float       # Lower_Wick / (High - Low) * 100

    # NEW: Reclaim/Recovery metrics
    reclaim_pct: float        # (Close - Low) / (High - Low) * 100
    close_position_pct: float # (Close - Low) / (High - Low) * 100 (same formula, different interpretation)

    # Volume anomaly
    volume_30_median: float
    volume_30_ratio: float    # Current / Median(previous 30 completed M15)

    # Candle type
    is_red: bool              # Close < Open


@dataclass(frozen=True, slots=True)
class CapitulationCheckResult:
    """Result of capitulation/absorption qualification check."""
    qualified: bool
    metrics: CapitulationMetrics
    failed_conditions: list[str]
    signal_direction: str = "LONG"
    signal_type: str = "CAPITULATION_ABSORPTION"


def calculate_capitulation_metrics(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    timestamp: int,
    prev_30_volumes: list[float],
) -> CapitulationMetrics:
    """
    Calculate all capitulation/absorption metrics from OHLCV + volume history.

    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
        close_price: Candle close price
        volume: Current candle volume
        timestamp: Candle timestamp (ms)
        prev_30_volumes: List of previous 30 completed M15 volumes (N-30 to N-1)

    Returns:
        CapitulationMetrics with all calculated values
    """
    # Basic candle type
    is_red = close_price < open_price

    # Range % = (High - Low) / Open * 100
    candle_range = high_price - low_price
    range_pct = (candle_range / open_price * 100) if open_price != 0 else 0.0

    # Open→Low % = (Low - Open) / Open * 100 (downside impulse)
    open_to_low_pct = ((low_price - open_price) / open_price * 100) if open_price != 0 else 0.0

    # Body % = abs(Close - Open) / Open * 100
    body_size = abs(close_price - open_price)
    body_pct = (body_size / open_price * 100) if open_price != 0 else 0.0

    # Lower Wick = min(Open, Close) - Low
    lower_wick = min(open_price, close_price) - low_price

    # LW/Body = Lower_Wick / abs(Close - Open)
    lw_body_ratio = (lower_wick / body_size) if body_size > 0 else 0.0

    # LW/Range % = Lower_Wick / (High - Low) * 100
    lw_range_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0.0

    # NEW: Reclaim % = (Close - Low) / (High - Low) * 100
    reclaim_pct = ((close_price - low_price) / candle_range * 100) if candle_range > 0 else 0.0

    # NEW: Close Position % = (Close - Low) / (High - Low) * 100
    close_position_pct = ((close_price - low_price) / candle_range * 100) if candle_range > 0 else 0.0

    # Volume 30 Median & Ratio
    volume_30_median = 0.0
    volume_30_ratio = 0.0
    if prev_30_volumes and len(prev_30_volumes) >= 2:
        import statistics
        volume_30_median = statistics.median(prev_30_volumes)
        if volume_30_median > 0:
            volume_30_ratio = volume / volume_30_median

    return CapitulationMetrics(
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        timestamp=timestamp,
        range_pct=range_pct,
        open_to_low_pct=open_to_low_pct,
        body_pct=body_pct,
        lower_wick=lower_wick,
        lw_body_ratio=lw_body_ratio,
        lw_range_pct=lw_range_pct,
        reclaim_pct=reclaim_pct,
        close_position_pct=close_position_pct,
        volume_30_median=volume_30_median,
        volume_30_ratio=volume_30_ratio,
        is_red=is_red,
    )


def check_capitulation_signal(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    timestamp: int,
    prev_30_volumes: list[float],
) -> CapitulationCheckResult:
    """
    Check if a candle qualifies as capitulation/absorption LONG candidate.

    Qualification requires ALL conditions (AND logic):
    1. Closed M15 candle (validated by caller)
    2. Significant downside impulse (Open→Low)
    3. Volume anomaly >= threshold (Volume30Ratio)
    4. Meaningful lower wick (LW/Body)
    5. Meaningful reclaim from Low (ReclaimPct)

    Volume is NOT used for signal qualification in the same way as before.
    Volume anomaly is a REQUIRED condition.

    Args:
        open_price: Candle open
        high_price: Candle high
        low_price: Candle low
        close_price: Candle close
        volume: Current candle volume
        timestamp: Candle timestamp (ms)
        prev_30_volumes: Previous 30 completed M15 volumes (N-30 to N-1)

    Returns:
        CapitulationCheckResult with qualified flag, metrics, and failed conditions
    """
    metrics = calculate_capitulation_metrics(
        open_price, high_price, low_price, close_price, volume, timestamp, prev_30_volumes
    )

    failed = []

    # 1. Must be a red candle (downside impulse indicator)
    if not metrics.is_red:
        failed.append("Not a red candle (Close >= Open) - no downside impulse")

    # 2. Significant downside impulse (configurable threshold)
    if metrics.open_to_low_pct > CAPITULATION_THRESHOLDS["open_to_low_pct"]["value"]:
        failed.append(
            f"Open→Low {metrics.open_to_low_pct:.2f}% > "
            f"{CAPITULATION_THRESHOLDS['open_to_low_pct']['value']}% "
            f"(insufficient downside impulse)"
        )

    # 3. Volume anomaly (REQUIRED)
    if metrics.volume_30_ratio < CAPITULATION_THRESHOLDS["volume_30_ratio"]["value"]:
        failed.append(
            f"Volume30Ratio {metrics.volume_30_ratio:.2f}x < "
            f"{CAPITULATION_THRESHOLDS['volume_30_ratio']['value']}x "
            f"(no volume anomaly)"
        )

    # 4. Meaningful lower wick (absorption)
    if metrics.lw_body_ratio < CAPITULATION_THRESHOLDS["lw_body_ratio"]["value"]:
        failed.append(
            f"LW/Body {metrics.lw_body_ratio:.2f}x < "
            f"{CAPITULATION_THRESHOLDS['lw_body_ratio']['value']}x "
            f"(insufficient lower wick / absorption)"
        )

    # 5. Meaningful reclaim from Low (recovery)
    if metrics.reclaim_pct < CAPITULATION_THRESHOLDS["reclaim_pct"]["value"]:
        failed.append(
            f"Reclaim {metrics.reclaim_pct:.2f}% < "
            f"{CAPITULATION_THRESHOLDS['reclaim_pct']['value']}% "
            f"(insufficient reclaim from Low)"
        )

    qualified = len(failed) == 0

    return CapitulationCheckResult(
        qualified=qualified,
        metrics=metrics,
        failed_conditions=failed,
        signal_direction="LONG",
        signal_type="CAPITULATION_ABSORPTION",
    )


def format_capitulation_telegram_message(
    symbol: str,
    event_time_utc: str,  # Already formatted as "DD.MM.YYYY HH:MM UTC"
    result: CapitulationCheckResult,
) -> str:
    """
    Format capitulation/absorption signal for Telegram.

    Uses UTC only, plain text, fixed template for LONG candidates.
    """
    m = result.metrics

    # Build conditions lines
    conditions = [
        f"Open→Low ≤ {CAPITULATION_THRESHOLDS['open_to_low_pct']['value']}% — "
        f"{'PASS' if m.open_to_low_pct <= CAPITULATION_THRESHOLDS['open_to_low_pct']['value'] else 'FAIL'}",
        f"Volume30Ratio ≥ {CAPITULATION_THRESHOLDS['volume_30_ratio']['value']}x — "
        f"{'PASS' if m.volume_30_ratio >= CAPITULATION_THRESHOLDS['volume_30_ratio']['value'] else 'FAIL'}",
        f"LW/Body ≥ {CAPITULATION_THRESHOLDS['lw_body_ratio']['value']}x — "
        f"{'PASS' if m.lw_body_ratio >= CAPITULATION_THRESHOLDS['lw_body_ratio']['value'] else 'FAIL'}",
        f"Reclaim ≥ {CAPITULATION_THRESHOLDS['reclaim_pct']['value']}% — "
        f"{'PASS' if m.reclaim_pct >= CAPITULATION_THRESHOLDS['reclaim_pct']['value'] else 'FAIL'}",
    ]

    message = (
        f"🟢 LONG CAPITULATION / ABSORPTION\n\n"
        f"Symbol: {symbol}\n\n"
        f"Time: {event_time_utc}\n\n"
        f"OHLCV\n"
        f"Open: {m.open:.6f}\n"
        f"High: {m.high:.6f}\n"
        f"Low: {m.low:.6f}\n"
        f"Close: {m.close:.6f}\n"
        f"Volume: {m.volume:,.0f}\n\n"
        f"Metrics\n"
        f"Range: {m.range_pct:.2f}%\n"
        f"Open→Low: {m.open_to_low_pct:.2f}%\n"
        f"Body: {m.body_pct:.2f}%\n"
        f"Lower Wick: {m.lower_wick:.6f}\n"
        f"LW/Body: {m.lw_body_ratio:.2f}x\n"
        f"LW/Range: {m.lw_range_pct:.2f}%\n"
        f"Reclaim: {m.reclaim_pct:.2f}%\n"
        f"Close Position: {m.close_position_pct:.2f}%\n\n"
        f"Volume\n"
        f"Median30: {m.volume_30_median:,.0f}\n"
        f"Volume Ratio: {m.volume_30_ratio:.2f}x\n\n"
        f"✅ Conditions\n"
        f"{chr(10).join(conditions)}\n\n"
        f"Direction: LONG\n"
        f"Type: CAPITULATION_ABSORPTION\n"
        f"Mode: SHADOW"
    )

    return message


# ============================================================================
# UNIT TESTS (can be run standalone)
# ============================================================================

def run_unit_tests() -> bool:
    """Run unit tests for capitulation detector."""
    all_passed = True

    def assert_eq(actual, expected, msg, tol=0.01):
        nonlocal all_passed
        if abs(actual - expected) > tol:
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

    print("Running Capitulation Detector Unit Tests...\n")

    # Test 1: Valid capitulation candle
    # Open=100, High=102, Low=94, Close=98, Volume=1000
    # Range=8%, Open->Low=-6%, Body=2%, LW=4 (min(100,98)-94), LW/Body=2.0x
    # LW/Range=4/8=50%, Reclaim=(98-94)/8=50%, Volume30Ratio=2.0
    prev_volumes = [500.0] * 30  # Median=500
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=94.0,
        close_price=98.0,
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=prev_volumes,
    )
    assert_bool(result.qualified, True, "Test 1: Valid capitulation candle should PASS")
    assert_eq(result.metrics.open_to_low_pct, -6.0, "Test 1: Open->Low")
    assert_eq(result.metrics.lw_body_ratio, 2.0, "Test 1: LW/Body")
    assert_eq(result.metrics.reclaim_pct, 50.0, "Test 1: Reclaim")
    assert_eq(result.metrics.volume_30_ratio, 2.0, "Test 1: Volume30Ratio")

    # Test 2: Green candle should FAIL
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=105.0,
        low_price=95.0,
        close_price=102.0,
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 2: Green candle should FAIL")
    assert any("red candle" in f for f in result.failed_conditions), "Test 2: Should fail on red candle check"

    # Test 3: Insufficient downside impulse
    # Open->Low = -1% (not enough)
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=99.0,
        close_price=98.5,
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 3: Insufficient Open->Low should FAIL")
    # Error message uses Unicode right arrow
    assert any("\u2192" in f for f in result.failed_conditions), "Test 3: Should fail on Open\u2192Low"

    # Test 4: No volume anomaly
    # Volume = 600, Median30 = 500, Ratio = 1.2x (< 2.0)
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=94.0,
        close_price=98.0,
        volume=600.0,  # Only 1.2x median
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 4: No volume anomaly should FAIL")
    assert any("Volume30Ratio" in f for f in result.failed_conditions), "Test 4: Should fail on volume"

    # Test 5: Insufficient lower wick (LW/Body < 1.0)
    # Body=3, LW=2, Ratio=0.67
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=97.0,
        close_price=97.0,  # Body=3, LW=0 (doji-like)
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 5: Insufficient LW/Body should FAIL")
    assert any("LW/Body" in f for f in result.failed_conditions), "Test 5: Should fail on LW/Body"

    # Test 6: Insufficient reclaim
    # Close stays near Low (Reclaim < threshold)
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=94.0,
        close_price=94.5,  # Close near Low, Reclaim = 0.5/8 = 6.25%
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 6: Insufficient Reclaim should FAIL")
    assert any("Reclaim" in f for f in result.failed_conditions), "Test 6: Should fail on Reclaim"

    # Test 7: Doji (Close == Open) should FAIL
    result = check_capitulation_signal(
        open_price=100.0,
        high_price=102.0,
        low_price=98.0,
        close_price=100.0,
        volume=1000.0,
        timestamp=1700000000000,
        prev_30_volumes=[500] * 30,
    )
    assert_bool(result.qualified, False, "Test 7: Doji should FAIL")

    # Test 8: Telegram format uses UTC only
    test_time = datetime.fromtimestamp(1700000000, tz=UTC)
    time_str = test_time.strftime("%d.%m.%Y %H:%M UTC")
    msg = format_capitulation_telegram_message("BTC-USDT", time_str, result)
    assert_bool("UTC" in msg and "MSK" not in msg, True, "Test 8: Telegram uses UTC only")
    assert_bool("LONG" in msg, True, "Test 8: Shows LONG direction")
    assert_bool("SHADOW" in msg, True, "Test 8: Shows SHADOW mode")

    print(f"\n{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed


if __name__ == "__main__":
    run_unit_tests()
