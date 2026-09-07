#!/usr/bin/env python3
"""
LW-001 Canonical Metric Specification

This is the SINGLE SOURCE OF TRUTH for all LW-001 metric calculations.
All other code must use these functions.

Version: 1.0
Status: VALIDATED
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class MetricUnits:
    """Standard units for LW-001 metrics."""
    PERCENT: Literal["%"] = "%"
    RATIO: Literal["x"] = "x"


@dataclass
class LW001Metrics:
    """Canonical LW-001 metrics with units."""
    range_pct: float  # Unit: %
    body_pct: float  # Unit: %
    lower_wick_body_ratio: float  # Unit: x
    lower_wick_range_pct: float  # Unit: %
    open_to_low_pct: float  # Unit: %
    volume_ratio: Optional[float]  # Unit: x


def calculate_range_pct(open_price: float, high_price: float, low_price: float) -> float:
    """
    Calculate Range percentage.
    
    Formula: ((High - Low) / Open) * 100
    
    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
    
    Returns:
        Range in percentage points (e.g., 6.00 for 6%)
    
    Unit: %
    """
    candle_range = high_price - low_price
    if open_price == 0:
        raise ValueError("Open price cannot be zero")
    return (candle_range / open_price) * 100


def calculate_body_pct(open_price: float, close_price: float) -> float:
    """
    Calculate Body percentage.
    
    Formula: (abs(Close - Open) / Open) * 100
    
    Args:
        open_price: Candle open price
        close_price: Candle close price
    
    Returns:
        Body in percentage points (e.g., 1.90 for 1.9%)
    
    Unit: %
    """
    body = abs(close_price - open_price)
    if open_price == 0:
        raise ValueError("Open price cannot be zero")
    return (body / open_price) * 100


def calculate_lower_wick(open_price: float, close_price: float, low_price: float) -> float:
    """
    Calculate Lower Wick (lower shadow).
    
    Formula: min(Open, Close) - Low
    
    Args:
        open_price: Candle open price
        close_price: Candle close price
        low_price: Candle low price
    
    Returns:
        Lower Wick in price units
    
    Unit: price units (same as input prices)
    """
    return min(open_price, close_price) - low_price


def calculate_lower_wick_body_ratio(open_price: float, close_price: float, low_price: float) -> float:
    """
    Calculate Lower Wick to Body ratio.
    
    Formula: Lower_Wick / abs(Close - Open)
    
    Args:
        open_price: Candle open price
        close_price: Candle close price
        low_price: Candle low price
    
    Returns:
        LW/Body ratio (e.g., 2.50 for 2.5x)
    
    Unit: x
    """
    lower_wick = calculate_lower_wick(open_price, close_price, low_price)
    body = abs(close_price - open_price)
    
    if body == 0:
        return 0.0
    
    return lower_wick / body


def calculate_lower_wick_range_pct(open_price: float, high_price: float, low_price: float, close_price: float) -> float:
    """
    Calculate Lower Wick to Range percentage.
    
    Formula: (Lower_Wick / (High - Low)) * 100
    
    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
        close_price: Candle close price
    
    Returns:
        LW/Range in percentage points (e.g., 63.00 for 63%)
    
    Unit: %
    """
    lower_wick = calculate_lower_wick(open_price, close_price, low_price)
    candle_range = high_price - low_price
    
    if candle_range == 0:
        return 0.0
    
    return (lower_wick / candle_range) * 100


def calculate_open_to_low_pct(open_price: float, low_price: float) -> float:
    """
    Calculate Open to Low percentage.
    
    Formula: ((Low - Open) / Open) * 100
    
    Args:
        open_price: Candle open price
        low_price: Candle low price
    
    Returns:
        Open→Low in percentage points (e.g., -5.00 for -5%)
    
    Unit: %
    """
    if open_price == 0:
        raise ValueError("Open price cannot be zero")
    return ((low_price - open_price) / open_price) * 100


def calculate_volume_ratio(candle_volume: float, reference_average_volume: float) -> float:
    """
    Calculate Volume Ratio.
    
    Formula: Candle_Volume / Reference_Average_Volume
    
    Args:
        candle_volume: Volume of the signal candle
        reference_average_volume: Average volume from reference period
    
    Returns:
        Volume Ratio (e.g., 2.60 for 2.6x)
    
    Unit: x
    
    Note:
        Reference Average Volume is calculated from the last 20 candles
        BEFORE the signal candle (not including the signal candle itself).
    """
    if reference_average_volume == 0:
        return 0.0
    
    return candle_volume / reference_average_volume


def calculate_all_metrics(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    reference_average_volume: float
) -> LW001Metrics:
    """
    Calculate all LW-001 metrics from OHLCV data.
    
    This is the canonical function that should be used everywhere.
    
    Args:
        open_price: Candle open price
        high_price: Candle high price
        low_price: Candle low price
        close_price: Candle close price
        volume: Candle volume
        reference_average_volume: Average volume from reference period
    
    Returns:
        LW001Metrics object with all calculated metrics
    
    Units:
        range_pct: %
        body_pct: %
        lower_wick_body_ratio: x
        lower_wick_range_pct: %
        open_to_low_pct: %
        volume_ratio: x
    """
    return LW001Metrics(
        range_pct=calculate_range_pct(open_price, high_price, low_price),
        body_pct=calculate_body_pct(open_price, close_price),
        lower_wick_body_ratio=calculate_lower_wick_body_ratio(open_price, close_price, low_price),
        lower_wick_range_pct=calculate_lower_wick_range_pct(open_price, high_price, low_price, close_price),
        open_to_low_pct=calculate_open_to_low_pct(open_price, low_price),
        volume_ratio=calculate_volume_ratio(volume, reference_average_volume)
    )


def validate_metric_units(metric_value: float, metric_unit: str, threshold_value: float, threshold_unit: str) -> bool:
    """
    Validate that metric and threshold have matching units.
    
    Args:
        metric_value: The calculated metric value
        metric_unit: The unit of the metric (e.g., "%", "x")
        threshold_value: The threshold value
        threshold_unit: The unit of the threshold (e.g., "%", "x")
    
    Returns:
        True if units match, False otherwise
    
    Raises:
        ValueError: If units do not match
    """
    if metric_unit != threshold_unit:
        raise ValueError(
            f"UNIT_MISMATCH: Metric unit '{metric_unit}' does not match threshold unit '{threshold_unit}'. "
            f"Pipeline stopped. Metric value: {metric_value}, Threshold value: {threshold_value}"
        )
    return True


# Canonical thresholds for LW-001
LW001_THRESHOLDS = {
    "range_pct": {"value": 6.0, "unit": "%", "operator": ">="},
    "body_pct": {"value": 1.9, "unit": "%", "operator": ">="},
    "lower_wick_body_ratio": {"value": 2.5, "unit": "x", "operator": ">="},
    "lower_wick_range_pct": {"value": 63.0, "unit": "%", "operator": ">="},
    "open_to_low_pct": {"value": -5.0, "unit": "%", "operator": "<="},
    "volume_ratio": {"value": 2.6, "unit": "x", "operator": ">="}
}


def check_all_conditions(metrics: LW001Metrics) -> tuple[bool, list[str]]:
    """
    Check if metrics meet all LW-001 conditions.
    
    Uses canonical thresholds and unit validation.
    
    Args:
        metrics: LW001Metrics object
    
    Returns:
        Tuple of (pass: bool, failures: list[str])
    
    All conditions use AND logic - all must pass.
    """
    failures = []
    
    # Range >= 6%
    try:
        validate_metric_units(
            metrics.range_pct, "%",
            LW001_THRESHOLDS["range_pct"]["value"], LW001_THRESHOLDS["range_pct"]["unit"]
        )
        if metrics.range_pct < LW001_THRESHOLDS["range_pct"]["value"]:
            failures.append(f"Range {metrics.range_pct:.2f}% < {LW001_THRESHOLDS['range_pct']['value']}%")
    except ValueError as e:
        failures.append(str(e))
    
    # Body >= 1.9%
    try:
        validate_metric_units(
            metrics.body_pct, "%",
            LW001_THRESHOLDS["body_pct"]["value"], LW001_THRESHOLDS["body_pct"]["unit"]
        )
        if metrics.body_pct < LW001_THRESHOLDS["body_pct"]["value"]:
            failures.append(f"Body {metrics.body_pct:.2f}% < {LW001_THRESHOLDS['body_pct']['value']}%")
    except ValueError as e:
        failures.append(str(e))
    
    # LW/Body >= 2.5x
    try:
        validate_metric_units(
            metrics.lower_wick_body_ratio, "x",
            LW001_THRESHOLDS["lower_wick_body_ratio"]["value"], LW001_THRESHOLDS["lower_wick_body_ratio"]["unit"]
        )
        if metrics.lower_wick_body_ratio < LW001_THRESHOLDS["lower_wick_body_ratio"]["value"]:
            failures.append(f"LW/Body {metrics.lower_wick_body_ratio:.2f}x < {LW001_THRESHOLDS['lower_wick_body_ratio']['value']}x")
    except ValueError as e:
        failures.append(str(e))
    
    # LW/Range >= 63%
    try:
        validate_metric_units(
            metrics.lower_wick_range_pct, "%",
            LW001_THRESHOLDS["lower_wick_range_pct"]["value"], LW001_THRESHOLDS["lower_wick_range_pct"]["unit"]
        )
        if metrics.lower_wick_range_pct < LW001_THRESHOLDS["lower_wick_range_pct"]["value"]:
            failures.append(f"LW/Range {metrics.lower_wick_range_pct:.1f}% < {LW001_THRESHOLDS['lower_wick_range_pct']['value']}%")
    except ValueError as e:
        failures.append(str(e))
    
    # Open→Low <= -5%
    try:
        validate_metric_units(
            metrics.open_to_low_pct, "%",
            LW001_THRESHOLDS["open_to_low_pct"]["value"], LW001_THRESHOLDS["open_to_low_pct"]["unit"]
        )
        if metrics.open_to_low_pct > LW001_THRESHOLDS["open_to_low_pct"]["value"]:
            failures.append(f"Open to Low {metrics.open_to_low_pct:.2f}% > {LW001_THRESHOLDS['open_to_low_pct']['value']}%")
    except ValueError as e:
        failures.append(str(e))
    
    # Volume Ratio >= 2.6x
    try:
        if metrics.volume_ratio is None:
            failures.append("Volume Ratio is None")
        else:
            validate_metric_units(
                metrics.volume_ratio, "x",
                LW001_THRESHOLDS["volume_ratio"]["value"], LW001_THRESHOLDS["volume_ratio"]["unit"]
            )
            if metrics.volume_ratio < LW001_THRESHOLDS["volume_ratio"]["value"]:
                failures.append(f"Volume Ratio {metrics.volume_ratio:.2f}x < {LW001_THRESHOLDS['volume_ratio']['value']}x")
    except ValueError as e:
        failures.append(str(e))
    
    return (len(failures) == 0, failures)
