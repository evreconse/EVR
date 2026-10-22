"""Cross-check the active monitor's final gate against the detector config.

The production monitor has import-time side effects (SQLite and forensic log
paths under ``/home/evreconse``).  This test therefore extracts only the real
``FIXED_THRESHOLDS`` assignment and ``check_thresholds`` function from the
published monitor source, then compares its decision with the complete
detector qualification on identical candles.

This is a regression test for the dual-source threshold arrangement: the
monitor currently ignores ``result.qualified`` and applies its own four
thresholds.  The two paths must keep producing the same decision.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path
from typing import Any

from config.capitulation_thresholds import CAPITULATION_THRESHOLDS
from strategy.capitulation_detector import check_capitulation_signal

MONITOR_PATH = Path(__file__).resolve().parents[1] / "realtime_capitulation_monitor_fixed.py"


def _load_monitor_threshold_logic() -> tuple[dict[str, float], Any]:
    """Extract the monitor's threshold constant and final gate without importing it."""
    tree = ast.parse(MONITOR_PATH.read_text(encoding="utf-8"))
    selected: list[ast.stmt] = []

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "FIXED_THRESHOLDS"
            for target in node.targets
        ):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "check_thresholds":
            selected.append(node)

    assert len(selected) == 2, "monitor threshold constant/function not found exactly once"

    namespace: dict[str, Any] = {}
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(MONITOR_PATH), "exec"), namespace)  # noqa: S102
    return namespace["FIXED_THRESHOLDS"], namespace["check_thresholds"]


FIXED_THRESHOLDS, CHECK_THRESHOLDS = _load_monitor_threshold_logic()


def _monitor_decision(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    previous_volumes: list[float],
) -> tuple[bool, bool]:
    """Return (detector qualified, monitor final decision) for one candle."""
    result = check_capitulation_signal(
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        1_700_000_000_000,
        previous_volumes,
    )
    thresholds_passed, _ = CHECK_THRESHOLDS(result.metrics)
    monitor_qualified = (close_price < open_price) and thresholds_passed
    return result.qualified, monitor_qualified


def test_monitor_fixed_thresholds_match_detector_config() -> None:
    assert FIXED_THRESHOLDS == {
        "drop_pct": -5.0,
        "wick_body_ratio": 1.0,
        "reclaim_pct": 30.0,
        "volume_30_ratio": 2.0,
    }
    assert CAPITULATION_THRESHOLDS["open_to_low_pct"]["value"] == FIXED_THRESHOLDS["drop_pct"]
    assert CAPITULATION_THRESHOLDS["volume_30_ratio"]["value"] == FIXED_THRESHOLDS["volume_30_ratio"]
    assert CAPITULATION_THRESHOLDS["lw_body_ratio"]["value"] == FIXED_THRESHOLDS["wick_body_ratio"]
    assert CAPITULATION_THRESHOLDS["reclaim_pct"]["value"] == FIXED_THRESHOLDS["reclaim_pct"]


def test_random_candles_produce_identical_qualification() -> None:
    rng = random.Random(20261022)

    for _ in range(5000):
        open_price = rng.uniform(0.01, 1000.0)
        low_price = open_price * rng.uniform(0.80, 1.0)
        high_price = open_price * rng.uniform(1.0, 1.20)
        close_price = rng.uniform(low_price, high_price)
        volume = rng.uniform(0.0, 10_000.0)
        previous_volumes = [rng.uniform(0.0, 5000.0) for _ in range(30)]

        detector_qualified, monitor_qualified = _monitor_decision(
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            previous_volumes,
        )

        assert detector_qualified is monitor_qualified


def test_boundaries_and_degenerate_candles_produce_identical_qualification() -> None:
    cases = [
        # Exact boundaries: Open->Low -5%, Volume 2x, LW/Body 1x, Reclaim 30%.
        (100.0, 103.3333333333, 95.0, 97.5, 1000.0),
        # Same geometry, just beyond the boundaries.
        (100.0, 103.34, 95.0, 97.5, 1000.0),
        (100.0, 103.0, 95.01, 97.4, 999.0),
        # Zero body / zero range / zero open.
        (100.0, 100.0, 100.0, 100.0, 1000.0),
        (100.0, 102.0, 100.0, 100.0, 1000.0),
        (0.0, 0.0, 0.0, 0.0, 1000.0),
        # Green candle.
        (100.0, 103.0, 95.0, 100.5, 1000.0),
    ]

    for open_price, high_price, low_price, close_price, volume in cases:
        detector_qualified, monitor_qualified = _monitor_decision(
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            [500.0] * 30,
        )
        assert detector_qualified is monitor_qualified
