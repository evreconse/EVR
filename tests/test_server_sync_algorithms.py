"""Regression tests for the server-synchronized Capitulation and LW-001 logic.

The production service runs the Capitulation/Absorption monitor.  LW-001 is
retained in the repository as an inactive legacy strategy, but its canonical
metric specification must stay aligned with the server source as well.
"""

from __future__ import annotations

import pytest

from config.capitulation_thresholds import CAPITULATION_THRESHOLDS
from LW001_METRIC_SPEC import (
    LW001_THRESHOLDS,
    calculate_all_metrics,
    check_all_conditions,
)
from strategy.capitulation_detector import (
    calculate_capitulation_metrics,
    check_capitulation_signal,
)


def _capitulation_signal(
    *,
    open_price: float = 100.0,
    high_price: float = 102.0,
    low_price: float = 94.0,
    close_price: float = 98.0,
    volume: float = 1000.0,
    previous_volumes: list[float] | None = None,
):
    """Build a signal using stable 500-volume history by default."""
    return check_capitulation_signal(
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        1_700_000_000_000,
        previous_volumes if previous_volumes is not None else [500.0] * 30,
    )


class TestActiveCapitulationThresholds:
    def test_server_thresholds_are_exact(self) -> None:
        values = {name: spec["value"] for name, spec in CAPITULATION_THRESHOLDS.items()}
        assert values["open_to_low_pct"] == -5.0
        assert values["volume_30_ratio"] == 2.0
        assert values["lw_body_ratio"] == 1.0
        assert values["reclaim_pct"] == 30.0
        assert values["volume_median_window"] == 30
        assert "score" not in values

    def test_metrics_match_server_formulas(self) -> None:
        metrics = calculate_capitulation_metrics(100.0, 102.0, 94.0, 98.0, 1000.0, 1, [500.0] * 30)

        assert metrics.range_pct == pytest.approx(8.0)
        assert metrics.open_to_low_pct == pytest.approx(-6.0)
        assert metrics.body_pct == pytest.approx(2.0)
        assert metrics.lower_wick == pytest.approx(4.0)
        assert metrics.lw_body_ratio == pytest.approx(2.0)
        assert metrics.lw_range_pct == pytest.approx(50.0)
        assert metrics.reclaim_pct == pytest.approx(50.0)
        assert metrics.volume_30_ratio == pytest.approx(2.0)
        assert metrics.is_red is True

    def test_qualified_signal_has_no_score_gate(self) -> None:
        result = _capitulation_signal()
        assert result.qualified is True
        assert result.failed_conditions == []
        assert result.signal_direction == "LONG"
        assert result.signal_type == "CAPITULATION_ABSORPTION"
        # The server does not require, calculate, or gate on a score.
        assert not hasattr(result, "score")

    def test_open_to_low_boundary_is_inclusive(self) -> None:
        result = _capitulation_signal(low_price=95.0)
        assert result.metrics.open_to_low_pct == pytest.approx(-5.0)
        assert result.qualified is True

    def test_open_to_low_just_above_threshold_fails(self) -> None:
        result = _capitulation_signal(low_price=95.01)
        assert result.metrics.open_to_low_pct == pytest.approx(-4.99)
        assert result.qualified is False
        assert any("Open→Low" in reason for reason in result.failed_conditions)

    def test_volume_boundary_is_inclusive(self) -> None:
        result = _capitulation_signal(volume=1000.0)
        assert result.metrics.volume_30_ratio == pytest.approx(2.0)
        assert result.qualified is True

        failed = _capitulation_signal(volume=999.0)
        assert failed.qualified is False
        assert any("Volume30Ratio" in reason for reason in failed.failed_conditions)

    def test_lower_wick_body_boundary_is_inclusive(self) -> None:
        # Open 100 / Low 95 / High 103 / Close 97.5:
        # body=2.5, lower_wick=2.5, reclaim=31.25%, open->low=-5%.
        result = _capitulation_signal(high_price=103.0, low_price=95.0, close_price=97.5)
        assert result.metrics.lw_body_ratio == pytest.approx(1.0)
        assert result.qualified is True

        failed = _capitulation_signal(high_price=103.0, low_price=95.0, close_price=97.4)
        assert failed.qualified is False
        assert any("LW/Body" in reason for reason in failed.failed_conditions)

    def test_reclaim_boundary_is_inclusive(self) -> None:
        # range=8.333..., close-low=2.5 => reclaim=30%; all other filters pass.
        result = _capitulation_signal(high_price=103.3333333333, low_price=95.0, close_price=97.5)
        assert result.metrics.reclaim_pct == pytest.approx(30.0)
        assert result.qualified is True

        failed = _capitulation_signal(high_price=103.34, low_price=95.0, close_price=97.5)
        assert failed.qualified is False
        assert any("Reclaim" in reason for reason in failed.failed_conditions)

    def test_red_candle_is_required(self) -> None:
        result = _capitulation_signal(close_price=100.5)
        assert result.metrics.is_red is False
        assert result.qualified is False
        assert any("red candle" in reason.lower() for reason in result.failed_conditions)


class TestLW001ThresholdsAndFormulas:
    def test_server_thresholds_are_exact(self) -> None:
        assert {name: spec["value"] for name, spec in LW001_THRESHOLDS.items()} == {
            "range_pct": 4.5,
            "body_pct": 0.8,
            "lower_wick_body_ratio": 1.3,
            "lower_wick_range_pct": 55.0,
            "open_to_low_pct": -5.0,
        }

    def test_metrics_match_server_formulas(self) -> None:
        metrics = calculate_all_metrics(
            open_price=100.0,
            high_price=106.0,
            low_price=94.0,
            close_price=99.0,
            volume=1000.0,
            volume_3_candles_ago=500.0,
        )

        assert metrics.range_pct == pytest.approx(12.0)
        assert metrics.body_pct == pytest.approx(1.0)
        assert metrics.lower_wick_body_ratio == pytest.approx(5.0)
        assert metrics.lower_wick_range_pct == pytest.approx(5.0 / 12.0 * 100.0)
        assert metrics.open_to_low_pct == pytest.approx(-6.0)
        assert not hasattr(metrics, "volume_ratio")

    def test_passing_lw001_candle(self) -> None:
        metrics = calculate_all_metrics(100.0, 101.0, 95.0, 99.0, 1000.0, 500.0)
        passed, failures = check_all_conditions(metrics)
        assert passed is True
        assert failures == []

    def test_open_to_low_boundary_is_inclusive(self) -> None:
        metrics = calculate_all_metrics(100.0, 101.0, 95.0, 99.0, 1000.0, 500.0)
        assert metrics.open_to_low_pct == pytest.approx(-5.0)
        assert check_all_conditions(metrics)[0] is True

        failed = calculate_all_metrics(100.0, 101.0, 95.01, 99.0, 1000.0, 500.0)
        assert failed.open_to_low_pct == pytest.approx(-4.99)
        passed, failures = check_all_conditions(failed)
        assert passed is False
        assert any("Open to Low" in reason for reason in failures)

    def test_range_boundary_is_inclusive(self) -> None:
        passing = calculate_all_metrics(100.0, 99.5, 95.0, 99.0, 1000.0, 500.0)
        assert passing.range_pct == pytest.approx(4.5)
        assert check_all_conditions(passing)[0] is True

        failing = calculate_all_metrics(100.0, 99.49, 95.0, 99.0, 1000.0, 500.0)
        passed, failures = check_all_conditions(failing)
        assert passed is False
        assert any("Range" in reason for reason in failures)

    def test_body_boundary_is_inclusive(self) -> None:
        passing = calculate_all_metrics(100.0, 101.0, 95.0, 99.19, 1000.0, 500.0)
        assert passing.body_pct > 0.8
        assert check_all_conditions(passing)[0] is True

        failing = calculate_all_metrics(100.0, 101.0, 95.0, 99.21, 1000.0, 500.0)
        assert failing.body_pct < 0.8
        passed, failures = check_all_conditions(failing)
        assert passed is False
        assert any("Body" in reason for reason in failures)

    def test_lw_body_boundary_is_inclusive(self) -> None:
        passing = calculate_all_metrics(100.0, 99.5, 95.0, 97.84, 1000.0, 500.0)
        assert passing.lower_wick_body_ratio > 1.3
        assert check_all_conditions(passing)[0] is True

    def test_lw_range_boundary_is_inclusive(self) -> None:
        passing = calculate_all_metrics(100.0, 100.19, 95.0, 97.86, 1000.0, 500.0)
        assert passing.lower_wick_range_pct > 55.0
        assert check_all_conditions(passing)[0] is True

        failing = calculate_all_metrics(100.0, 100.21, 95.0, 97.86, 1000.0, 500.0)
        passed, failures = check_all_conditions(failing)
        assert passed is False
        assert any("LW/Range" in reason for reason in failures)

    def test_volume_ratio_is_not_a_lw001_condition(self) -> None:
        assert "volume_ratio" not in LW001_THRESHOLDS
        assert "volume_30_ratio" not in LW001_THRESHOLDS
