±v"""
EVRECONSE Strategy - LW-001 Long Lower Wick Reversal.

Strategy implementation for Long Lower Wick Reversal pattern.
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


class LW001Strategy:
    """
    LW-001: Long Lower Wick Reversal Strategy.

    Identifies bullish reversal patterns where a candle has a long
    lower wick (>= 2x body) on M15 timeframe.

    Only operates on M15 timeframe with real BingX data.
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
            "Identifies bullish reversal patterns where a candle has a long "
            "lower wick (>= 2x body). Only operates on M15 timeframe with real BingX data."
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

        # Wick ratio parameter
        wick_ratio = params.get("lower_wick_ratio", 2.0)
        if not isinstance(wick_ratio, (int, float)) or wick_ratio < 1.0:
            raise StrategyValidationError(
                "lower_wick_ratio must be a number >= 1.0",
                field="lower_wick_ratio",
            )


        # Min confidence score
        min_score = params.get("min_confidence_score", 30)
        if not isinstance(min_score, (int, float)) or not (0 <= min_score <= 100):
            raise StrategyValidationError(
                "min_confidence_score must be between 0 and 100",
                field="min_confidence_score",
            )


        # Scoring weights
        weights = params.get("scoring", {})
        for key in ("lower_wick_weight", "confirmation_weight"):
            if key in weights:
                weight = weights[key]
                if not isinstance(weight, (int, float)) or weight < 0:
                    raise StrategyValidationError(
                        f"scoring.{key} must be non-negative number",
                        field=f"scoring.{key}",
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
            if context.market_event.exchange not in [Exchange.BYBIT, Exchange("bybit_testnet")]:
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
        Evaluate the market event for long lower wick reversal pattern.

        Args:
            context: Evaluation context containing market event and dependencies

        Returns:
            StrategyResult with qualification decision and scoring

        Raises:
            StrategyExecutionError: If evaluation fails
        """
        # print(f"DEBUG STRATEGY: evaluate() called for {context.market_event.market_data.symbol if context.market_event and context.market_event.market_data else 'unknown'}")
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

            # =====================================================================
            # VALIDATE CANDLE IS CLOSED (confirmed)
            # =====================================================================
            if not getattr(strategy_data, "confirm", False):
                raise StrategyExecutionError("Candle not confirmed/closed yet")

            # =====================================================================
            # EXTRACT MARKET DATA (OHLC from Bybit)
            # =====================================================================
            open_price = market_data.open
            high_price = market_data.high
            low_price = market_data.low
            close_price = market_data.close
            volume = market_data.volume

            # =====================================================================
            # COMPUTE CANDLE STRUCTURE FROM OHLC (not from strategy_data)
            # =====================================================================
            body = close_price - open_price
            body_size = abs(body)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price
            candle_range = high_price - low_price

            # Wick-to-body ratio
            wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0

            # Body ratio (body size / total candle range)
            body_ratio = body_size / candle_range if candle_range > 0 else 0.0

            # Close position (where close is within the candle range)
            close_position = (close_price - low_price) / candle_range if candle_range > 0 else 0.0


            # =====================================================================
            # CONFIG PARAMETERS
            # =====================================================================
            params = context.config.parameters
            scoring = params.get("scoring", {})
            condition = params.get("condition", {})

            # Condition parameters
            wick_ratio_threshold = condition.get("lower_wick_ratio", 2.0)
            min_confidence_score = condition.get("min_confidence_score", 80)

            # Scoring weights
            wick_weight = scoring.get("lower_wick_weight", 70)
            confirm_weight = scoring.get("confirmation_weight", 30)

            # Wick scoring tiers
            wick_tiers = {
                "3x": scoring.get("wick_tier_3x", 70),
                "2_5x": scoring.get("wick_tier_2_5x", 60),
                "2x": scoring.get("wick_tier_2x", 50),
                "1_5x": scoring.get("wick_tier_1_5x", 35),
                "1x": scoring.get("wick_tier_1x", 20),
                "doji": scoring.get("wick_tier_doji", 25),
            }


            # Confirmation tiers
            confirm_tiers = {
                "bull_0_6": scoring.get("confirm_tier_bull_0_6", 30),
                "bull_0_4": scoring.get("confirm_tier_bull_0_4", 25),
                "bull_0_2": scoring.get("confirm_tier_bull_0_2", 20),
                "bull_0_1": scoring.get("confirm_tier_bull_0_1", 15),
                "bear_0_4": scoring.get("confirm_tier_bear_0_4", 20),
                "bear_below": scoring.get("confirm_tier_bear_below", 10),
            }
            close_near_high_bonus = scoring.get("confirm_close_near_high_bonus", 5)
            close_near_high_threshold = scoring.get("confirm_close_near_high_threshold", 0.8)

            # =====================================================================
            # SCORING COMPONENTS
            # =====================================================================

            # 1. Lower Wick Quality (0-70 points)
            wick_score = 0.0
            wick_explanation = ""

            if body_size > 0:
                ratio = lower_wick / body_size

                if ratio >= 3.0:
                    wick_score = wick_tiers["3x"]
                    wick_explanation = f"Excellent wick-to-body ratio: {ratio:.2f}x"
                elif ratio >= 2.5:
                    wick_score = wick_tiers["2_5x"]
                    wick_explanation = f"Strong wick-to-body ratio: {ratio:.2f}x"
                elif ratio >= 2.0:
                    wick_score = wick_tiers["2x"]
                    wick_explanation = f"Good wick-to-body ratio: {ratio:.2f}x"
                elif ratio >= 1.5:
                    wick_score = wick_tiers["1_5x"]
                    wick_explanation = f"Moderate wick-to-body ratio: {ratio:.2f}x"
                elif ratio >= 1.0:
                    wick_score = wick_tiers["1x"]
                    wick_explanation = f"Weak wick-to-body ratio: {ratio:.2f}x"
                else:
                    wick_score = 0
                    wick_explanation = f"Insufficient wick-to-body ratio: {ratio:.2f}x"
            else:
                # No body (doji-like)
                wick_score = wick_tiers["doji"]
                wick_explanation = "Doji-like candle with lower wick"


            # 2. Candle Confirmation (0-30 points)
            confirm_score = 0.0
            confirm_explanation = ""

            if candle_range == 0:
                confirm_score = 0
                confirm_explanation = "Zero candle range"
            else:
                body_ratio = body_size / candle_range

                # Body ratio scoring
                if body > 0:  # Bullish candle
                    if body_ratio >= 0.6:
                        confirm_score = confirm_tiers["bull_0_6"]
                    elif body_ratio >= 0.4:
                        confirm_score = confirm_tiers["bull_0_4"]
                    elif body_ratio >= 0.2:
                        confirm_score = confirm_tiers["bull_0_2"]
                    else:
                        confirm_score = confirm_tiers["bull_0_1"]

                    # Bonus for close near high (bullish confirmation)
                    close_position = (close_price - low_price) / candle_range
                    if close_position >= 0.8:
                        confirm_score += 5
                else:  # Bearish or doji
                    if body_ratio >= 0.4:
                        confirm_score = confirm_tiers["bear_0_4"]
                    else:
                        confirm_score = confirm_tiers["bear_below"]

            # =====================================================================
            # FINAL SCORE CALCULATION
            # =====================================================================

            # Weighted score using configured weights
            # Scores are already scaled (max 70 for wick, max 30 for confirm)
            # Apply weights directly to get final score
            total_score = (
                wick_score * (wick_weight / 100) +
                confirm_score * (confirm_weight / 100)
            )

            max_score = 100.0
            final_score = min(total_score, max_score)

            # Qualification threshold
            min_score = params.get("min_confidence_score", 80)
            qualified = final_score >= min_score

            # DEBUG: Print high scores for investigation
            if final_score >= 50:
                print(f"DEBUG HIGH SCORE: {context.market_event.market_data.symbol if context.market_event and context.market_event.market_data else 'unknown'} - final={final_score:.1f}, wick={wick_score:.1f}, confirm={confirm_score:.1f}, ratio={lower_wick/body_size if body_size > 0 else 0:.2f}")

            # =====================================================================
            # BUILD EXPLANATION
            # =====================================================================
            explanation = (
                f"LW-001 Result: {'QUALIFIED' if qualified else 'REJECTED'}\n"
                f"Final Score: {final_score:.1f}/100\n"
                f"  - Lower Wick Quality: {wick_score:.1f}/70 ({wick_explanation})\n"
                f"  - Candle Confirmation: {confirm_score:.1f}/30\n"
                f"Min Score Threshold: {min_score}\n"
                f"Candle Data: O={open_price:.2f} H={high_price:.2f} L={low_price:.2f} C={close_price:.2f}\n"
                f"Body: {body_size:.2f}, Lower Wick: {lower_wick:.2f}, Ratio: {(lower_wick/body_size if body_size > 0 else 0):.2f}x"
            )

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            return StrategyResult(
                qualified=qualified,
                final_score=round(final_score, 2),
                max_score=max_score,
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
        }±v2Rfile:///c:/Users/user/Documents/Default%20Project/EVRECONSE/src/strategy/lw_001.py