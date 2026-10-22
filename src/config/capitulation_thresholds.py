"""
EVRECONSE Capitulation/Absorption Thresholds Configuration

All thresholds are configurable here. No hardcoded values in detector code.
"""

from typing import Any

# Capitulation/Absorption thresholds
# These can be adjusted based on research without code changes
CAPITULATION_THRESHOLDS: dict[str, dict[str, Any]] = {
    # Downside impulse: Open→Low % must be <= this value (negative = price went down from open)
    "open_to_low_pct": {
        "value": -5.0,  # %
        "unit": "%",
        "operator": "<=",
        "description": "Minimum downside impulse from open to low"
    },

    # Volume anomaly: Current volume / Median(previous 30 completed M15)
    "volume_30_ratio": {
        "value": 2.0,   # x
        "unit": "x",
        "operator": ">=",
        "description": "Volume anomaly threshold (current vs median30)"
    },

    # Volume median window
    "volume_median_window": {
        "value": 30,    # candles
        "unit": "candles",
        "operator": "=",
        "description": "Number of previous completed M15 candles for median calculation"
    },

    # Lower wick / Body ratio (absorption signal)
    "lw_body_ratio": {
        "value": 1.0,   # x
        "unit": "x",
        "operator": ">=",
        "description": "Lower wick must be at least as large as body"
    },

    # Reclaim from Low (recovery signal)
    "reclaim_pct": {
        "value": 30.0,  # %
        "unit": "%",
        "operator": ">=",
        "description": "Minimum reclaim from Low to Close (percentage of full range)"
    },

    # Optional: Range minimum (can be 0 to disable)
    "range_pct_min": {
        "value": 0.0,   # %
        "unit": "%",
        "operator": ">=",
        "description": "Minimum range (0 = disabled)"
    },

    # Optional: Body maximum (can be large to disable)
    "body_pct_max": {
        "value": 100.0, # %
        "unit": "%",
        "operator": "<=",
        "description": "Maximum body size (100 = disabled)"
    },
}


def get_threshold(key: str) -> Any:
    """Get threshold value by key."""
    return CAPITULATION_THRESHOLDS.get(key, {}).get("value")


def get_all_thresholds() -> dict[str, Any]:
    """Get all threshold values as a flat dict."""
    return {k: v["value"] for k, v in CAPITULATION_THRESHOLDS.items()}
