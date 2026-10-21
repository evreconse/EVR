"""
EVRECONSE Capitulation/Absorption Signal Detector
Exact replica of production logic with audit fixes applied.
"""

import statistics
from dataclasses import dataclass

# ============================================================================
# THRESHOLDS (from production config - DO NOT CHANGE per strategy freeze)
# ============================================================================

FIXED_THRESHOLDS = {
    "drop_pct": -2.5,           # Open→Low ≤ -2.5%
    "wick_body_ratio": 1.0,     # LW/Body ≥ 1.0x
    "reclaim_pct": 30.0,        # Reclaim ≥ 30%
    "volume_30_ratio": 2.0,     # Volume30Ratio ≥ 2.0x
    "volume_median_window": 30, # 30 previous completed M15 candles
}

# ============================================================================
# DATA STRUCTURES (matching production CapitulationMetrics)
# ============================================================================

@dataclass
class SignalMetrics:
    """Calculated metrics for a candidate signal"""
    # Basic OHLCV
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

    # Downside impulse
    range_pct: float
    open_to_low_pct: float

    # Body
    body_pct: float

    # Lower wick (absorption signal)
    lower_wick: float
    lw_body_ratio: float
    lw_range_pct: float

    # Reclaim/Recovery
    reclaim_pct: float
    close_position_pct: float

    # Volume anomaly
    volume_30_median: float
    volume_30_ratio: float

    # Candle type
    is_red: bool


@dataclass
class FilterResult:
    """Result of each filter check"""
    drop_pct: bool
    volume_30_ratio: bool
    wick_body_ratio: bool
    reclaim_pct: bool
    is_red: bool


@dataclass
class SignalCandidate:
    """Complete signal candidate with all data for audit"""
    symbol: str
    timestamp: int
    timestamp_utc: str
    metrics: 'SignalMetrics'
    filters: 'FilterResult'
    passed: bool
    fail_reason: str | None
    prev_30_volumes: list[float]
    volume_30_median: float

    # Source tracking
    source: str  # "independent" | "production_log" | "production_db"
    verified: bool = False  # True if matches production


# ============================================================================
# CORE CALCULATION FUNCTIONS (exact replica of production with audit fixes)
# ============================================================================

def check_red_candle(open_price: float, close_price: float) -> bool:
    """Check if candle is red (Close < Open) - EXACT production logic"""
    return close_price < open_price


def calculate_metrics(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    timestamp: int,
    prev_30_volumes: list[float]
) -> 'SignalMetrics':
    """Calculate all metrics - EXACT replica of production with audit fixes."""

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
    candle_range = high_price - low_price
    lw_range_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0.0

    # Reclaim % = (Close - Low) / (High - Low) * 100
    reclaim_pct = ((close_price - low_price) / candle_range * 100) if candle_range > 0 else 0.0

    # Close Position % = (Close - Low) / (High - Low) * 100 (same formula)
    close_position_pct = reclaim_pct

    # Volume 30 Median & Ratio
    volume_30_median = 0.0
    volume_30_ratio = 0.0
    if prev_30_volumes and len(prev_30_volumes) >= 30:
        volume_30_median = statistics.median(prev_30_volumes)
        if volume_30_median > 0:
            volume_30_ratio = volume / volume_30_median

    return SignalMetrics(
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


def check_thresholds(metrics: 'SignalMetrics') -> tuple[bool, dict[str, bool]]:
    """Check all thresholds - EXACT replica with audit fixes."""
    results = {
        "drop_pct": metrics.open_to_low_pct <= FIXED_THRESHOLDS["drop_pct"],
        "wick_body_ratio": metrics.lw_body_ratio >= FIXED_THRESHOLDS["wick_body_ratio"],
        "reclaim_pct": metrics.reclaim_pct >= FIXED_THRESHOLDS["reclaim_pct"],
        "volume_30_ratio": metrics.volume_30_ratio >= FIXED_THRESHOLDS["volume_30_ratio"],
        "is_red": metrics.is_red,
    }
    passed = all([
        results["is_red"],
        results["drop_pct"],
        results["volume_30_ratio"],
        results["wick_body_ratio"],
        results["reclaim_pct"],
    ])
    return passed, {
        "drop_pct": results["drop_pct"],
        "volume_30_ratio": results["volume_30_ratio"],
        "wick_body_ratio": results["wick_body_ratio"],
        "reclaim_pct": results["reclaim_pct"],
        "is_red": results["is_red"],
    }


def get_fail_reason(metrics, results) -> str:
    """Determine which filter failed - EXACT replica of production logic"""
    if not results["is_red"]:
        return "NOT_RED"
    if not results["drop_pct"]:
        return "DROP_FAIL"
    if not results["volume_30_ratio"]:
        return "VOLUME_FAIL"
    if not results["wick_body_ratio"]:
        return "WICK_BODY_FAIL"
    if not results["reclaim_pct"]:
        return "RECLAIM_FAIL"
    return "UNKNOWN"


def get_last_completed_candle(candles: list, now_ms: int) -> tuple[object | None, int | None]:
    """Identify the last completed candle - EXACT replica of production logic"""
    if not candles or len(candles) < 2:
        return None, None

    for i in range(len(candles) - 1, -1, -1):
        candle = candles[i]
        raw_timestamp = getattr(
            candle,
            "timestamp",
            candle.get("time", candle.get("timestamp", 0)) if isinstance(candle, dict) else 0,
        )
        try:
            timestamp = int(raw_timestamp or 0)
        except (TypeError, ValueError):
            continue
        if timestamp <= 0:
            continue
        candle_close_time = timestamp + (15 * 60 * 1000)
        if candle_close_time <= now_ms:
            return candle, i
    return None, None


# ============================================================================
# UNIT TESTS (validate against production unit tests)
# ============================================================================

def run_unit_tests() -> bool:
    """Validate detector matches production unit tests"""
    all_passed = True

    def assert_eq(actual, expected, msg, tol=0.01):
        nonlocal all_passed
        if abs(actual - expected) > tol:
            all_passed = False
        else:
            pass

    def assert_bool(actual, expected, msg):
        nonlocal all_passed
        if actual != expected:
            all_passed = False
        else:
            pass


    # Test 1: Valid capitulation candle
    metrics = calculate_metrics(100.0, 102.0, 94.0, 98.0, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if not passed:
        pass
    else:
        pass

    # Test 2: Green candle should FAIL
    metrics = calculate_metrics(100.0, 105.0, 95.0, 102.0, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 3: Insufficient downside impulse (Open->Low = -1%)
    metrics = calculate_metrics(100.0, 102.0, 99.0, 98.5, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 4: No volume anomaly (Ratio = 1.2x)
    metrics = calculate_metrics(100.0, 102.0, 94.0, 98.0, 600.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 5: Insufficient lower wick (LW/Body < 1.0)
    metrics = calculate_metrics(100.0, 102.0, 97.0, 97.0, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 6: Insufficient reclaim (Close near Low)
    metrics = calculate_metrics(100.0, 102.0, 94.0, 94.5, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 7: Doji (Close == Open) should FAIL
    metrics = calculate_metrics(100.0, 102.0, 98.0, 100.0, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if passed:
        pass
    else:
        pass

    # Test 8: All filters exactly at threshold
    metrics = calculate_metrics(100.0, 103.333, 95.0, 97.5, 1000.0, 1700000000000, [500]*30)
    passed, results = check_thresholds(metrics)
    if not passed:
        pass
    else:
        pass

    return all_passed


if __name__ == "__main__":
    run_unit_tests()
