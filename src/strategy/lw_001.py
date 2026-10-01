"""
EVRECONSE Strategy - LW-001 Long Lower Wick Reversal.

Strategy implementation for Long Lower Wick Reversal pattern.

IMPORTANT: This strategy uses the CANONICAL LW-001 check function from
lw001_canonical.py as the single source of truth for signal qualification.
All metric calculations and threshold checks are delegated to the canonical function.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from models.enums import Exchange, Timeframe

from .context import (
    StrategyConfig,
    StrategyContext,
    StrategyResult,
)
from .exceptions import (
    StrategyExecutionError,
    StrategyValidationError,
)
from .lw001_canonical import check_lw001_signal, LW001CheckResult


class LW001Strategy:
    """
    LW-001: Long Lower Wick Reversal Strategy.

    Identifies bullish reversal patterns based on 6 canonical conditions:
    1. Close < Open (red candle)
    2. Range % >= 4.5%
    3. Body % >= 0.8%
    4. LW/Body >= 1.3x
    5. LW/Range % >= 55.0%
    6. Open->Low % <= -2.5%

    Volume Ratio REMOVED - not part of LW-001 strategy.

    Only operates on M15 timeframe with real BingX data.
    Only uses CLOSED candles.
    """

    # =========================================================================
    # Strategy Metadata
    # =========================================================================

    @property
    def strategy_id(self) -> str:
        return "LW-001"

    @property
    def name(self) -> str:
        return "Long Lower Wick Reversal"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Identifies bullish reversal patterns using 6 canonical conditions: "
            "red candle, Range>=4.5%, Body>=0.8%, LW/Body>=1.3x, "
            "LW/Range>=55%, Open->Low<=-2.5%. "
            "Only operates on M15 timeframe with real BingX data. Only closed candles."
        )

    @property
    def supported_markets(self) -> list[str]:
        return ["bingx"]

    @property
    def supported_timeframes(self) -> list[str]:
        return ["15m"]

    # =========================================================================
    # Configuration
    # =========================================================================

    def validate_config(self, config: StrategyConfig) -> None:
        """
        Validate strategy configuration.

        Args:
            config: Strategy configuration

        Raises:
            StrategyValidationError: If configuration is invalid
        """
        params = config.parameters

        # All thresholds are fixed in canonical function - no config needed
        # But we validate that config doesn't override them (both canonical and legacy names)
        for forbidden in (
            "range_pct", "body_pct", "lw_body_ratio", "lw_range_pct", "open_to_low_pct",
            "lower_wick_ratio", "liquidation_window",  # Legacy parameter names
        ):
            if forbidden in params:
                raise StrategyValidationError(
                    f"Threshold '{forbidden}' is fixed in canonical spec and cannot be overridden",
                    field=forbidden,
                )

        # Validate min_confidence_score if present
        if "min_confidence_score" in params:
            score = params["min_confidence_score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                raise StrategyValidationError(
                    "min_confidence_score must be a number between 0 and 100",
                    field="min_confidence_score",
                )

    def supports(self, context: StrategyContext) -> bool:
        """Check if this strategy can evaluate the given context."""
        if not context.market_event:
            return False

        if not context.market_event.market_data:
            return False

        market_data = context.market_event.market_data

        if hasattr(market_data, "timeframe"):
            if market_data.timeframe != Timeframe.M15:
                return False

        if hasattr(context.market_event, "exchange"):
            if context.market_event.exchange != Exchange.BINGX:
                return False

        return True

    def initialize(self, config: StrategyConfig) -> None:
        """Initialize strategy with configuration."""
        self.validate_config(config)

    async def shutdown(self) -> None:
        """Cleanup resources."""

    # =========================================================================
    # Core Evaluation Logic
    # =========================================================================

    async def evaluate(self, context: StrategyContext) -> StrategyResult:
        """
        Evaluate the market event for LW-001 pattern using canonical check.

        Args:
            context: Evaluation context containing market event and dependencies

        Returns:
            StrategyResult with qualification decision

        Raises:
            StrategyExecutionError: If evaluation fails
        """
        start_time = time.perf_counter()

        try:
            # Validate context
            if not context.market_event:
                raise StrategyExecutionError("No market event in context")

            if not context.market_event.market_data:
                raise StrategyExecutionError("No market data in event")

            market_data = context.market_event.market_data
            strategy_data = context.market_event.strategy_data

            if not market_data:
                raise StrategyExecutionError("No market data available")

            if not strategy_data:
                raise StrategyExecutionError("No strategy data available")

            # Validate candle is closed (confirmed)
            if not getattr(strategy_data, "confirm", False):
                raise StrategyExecutionError("Candle not confirmed/closed yet")

            # Extract OHLCV
            open_price = market_data.open
            high_price = market_data.high
            low_price = market_data.low
            close_price = market_data.close
            volume = market_data.volume

            # Use CANONICAL check function - single source of truth
            # Volume is NOT used for signal qualification (Volume Ratio removed)
            result: LW001CheckResult = check_lw001_signal(
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
            )

            qualified = result.qualified
            metrics = result.metrics
            failed_conditions = result.failed_conditions

            # Build explanation
            if qualified:
                explanation = (
                    f"LW-001 Result: QUALIFIED\n"
                    f"All 6 conditions PASSED\n\n"
                    f"Candle Data: O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f}\n"
                    f"Volume: {volume:,.0f}\n\n"
                    f"Metrics:\n"
                    f"  Range: {metrics.range_pct:.2f}% (threshold: >= 4.5%)\n"
                    f"  Body: {metrics.body_pct:.2f}% (threshold: >= 0.8%)\n"
                    f"  LW/Body: {metrics.lw_body_ratio:.2f}x (threshold: >= 1.3x)\n"
                    f"  LW/Range: {metrics.lw_range_pct:.2f}% (threshold: >= 55.0%)\n"
                    f"  Open->Low: {metrics.open_to_low_pct:.2f}% (threshold: <= -2.5%)\n"
                )
            else:
                explanation = (
                    f"LW-001 Result: REJECTED\n"
                    f"Failed conditions:\n"
                    + "\n".join(f"  - {cond}" for cond in failed_conditions)
                    + f"\n\nCandle Data: O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f}\n"
                    f"Volume: {volume:,.0f}\n\n"
                    f"Metrics:\n"
                    f"  Range: {metrics.range_pct:.2f}% (threshold: >= 4.5%)\n"
                    f"  Body: {metrics.body_pct:.2f}% (threshold: >= 0.8%)\n"
                    f"  LW/Body: {metrics.lw_body_ratio:.2f}x (threshold: >= 1.3x)\n"
                    f"  LW/Range: {metrics.lw_range_pct:.2f}% (threshold: >= 55.0%)\n"
                    f"  Open->Low: {metrics.open_to_low_pct:.2f}% (threshold: <= -2.5%)\n"
                )

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            return StrategyResult(
                qualified=qualified,
                final_score=0.0,  # Score is informational only, not used for qualification
                max_score=100.0,
                contributions=tuple(),
                penalties=tuple(),
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                evaluation_id=uuid4(),
                evaluated_at=datetime.now(UTC),
                execution_time_ms=execution_time_ms,
                explanation=explanation,
            )

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            raise StrategyExecutionError(
                f"Strategy evaluation failed: {e}",
                strategy_id=self.strategy_id,
            ) from e

    def get_metadata(self) -> dict[str, Any]:
        """Get strategy metadata for registration."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "supported_markets": self.supported_markets,
            "supported_timeframes": self.supported_timeframes,
        }