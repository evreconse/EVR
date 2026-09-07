”r"""
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
            if context.market_event.exchange not in [Exchange.BINGX]:
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
            # LW-001: Only RED candles (Close < Open)
            is_red = close_price < open_price
            
            body = abs(close_price - open_price)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = close_price - low_price  # For red candles: Close is the lower body boundary
            candle_range = high_price - low_price

            # Wick-to-body ratio
            wick_body_ratio = lower_wick / body if body > 0 else 0.0

            # Body ratio (body size / total candle range)
            body_ratio = body / candle_range if candle_range > 0 else 0.0

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

            # LW-001 Qualification: RED candle AND Lower Wick / Body >= 2.0
            # Score is informational only and does NOT filter signals
            qualified = is_red and wick_body_ratio >= wick_ratio_threshold

            # =====================================================================
            # BUILD EXPLANATION
            # =====================================================================
            explanation = (
                f"LW-001 Result: {'QUALIFIED' if qualified else 'REJECTED'}\n"
                f"Final Score: {final_score:.1f}/100 (informational only)\n"
                f"  - Lower Wick Quality: {wick_score:.1f}/70 ({wick_explanation})\n"
                f"  - Candle Confirmation: {confirm_score:.1f}/30\n"
                f"Wick/Body Ratio: {wick_body_ratio:.2f}x (threshold: {wick_ratio_threshold}x)\n"
                f"Candle Data: O={open_price:.2f} H={high_price:.2f} L={low_price:.2f} C={close_price:.2f}\n"
                f"Body: {body_size:.2f}, Lower Wick: {lower_wick:.2f}, Upper Wick: {upper_wick:.2f}\n"
                f"Body/Range: {body_ratio:.2f}, Close Position: {close_position:.2f}"
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
        }Š *cascade08Š’ *cascade08’““• *cascade08•––É *cascade08ÉÌÌÖ
 *cascade08Ö
Ù
Ù
º *cascade08º¾ *cascade08¾Ñ *cascade08ÑÒ*cascade08ÒÓ *cascade08ÓÔ*cascade08ÔÍ *cascade08ÍĞ*cascade08ĞÑ! *cascade08Ñ!Ó!*cascade08Ó!‘" *cascade08‘""*cascade08"ª0 *cascade08ª0È0*cascade08È0É0 *cascade08É0å0*cascade08å0õ0 *cascade08õ0ö0*cascade08ö01 *cascade081›1*cascade08›1¦1 *cascade08¦1¨1*cascade08¨1©1 *cascade08©1¾1*cascade08¾1œ2 *cascade08œ22*cascade082Ÿ2 *cascade08Ÿ2 2*cascade08 2§2 *cascade08§2©2*cascade08©2¬2 *cascade08¬2­2*cascade08­2³2 *cascade08³2´2*cascade08´2µ2 *cascade08µ2¶2*cascade08¶2·2 *cascade08·2¸2*cascade08¸2¹2 *cascade08¹2»2*cascade08»2¼2 *cascade08¼2¿2*cascade08¿2À2 *cascade08À2Ä2*cascade08Ä2Å2 *cascade08Å2è2*cascade08è2÷9 *cascade08÷9ø9*cascade08ø9ù9 *cascade08ù9ú9*cascade08ú9ÚE *cascade08ÚEÛE*cascade08ÛE¦\ *cascade08¦\¨\ *cascade08¨\ª\*cascade08ª\¬\ *cascade08¬\³\*cascade08³\µ\ *cascade08µ\¶\*cascade08¶\·\ *cascade08·\º\*cascade08º\½\ *cascade08½\¿\*cascade08¿\À\ *cascade08À\Á\*cascade08Á\Â\ *cascade08Â\Æ\*cascade08Æ\Ç\ *cascade08Ç\È\*cascade08È\É\ *cascade08É\Í\*cascade08Í\Î\ *cascade08Î\Ğ\*cascade08Ğ\Ñ\ *cascade08Ñ\Õ\*cascade08Õ\Ö\ *cascade08Ö\Ú\*cascade08Ú\Ş\ *cascade08Ş\è\*cascade08è\é\ *cascade08é\÷\*cascade08÷\ƒ] *cascade08ƒ]Ÿ]*cascade08Ÿ]¬] *cascade08¬]Ö] *cascade08Ö]×] *cascade08×]Ù] *cascade08Ù]Ú]*cascade08Ú]æ] *cascade08æ]í]*cascade08í]Œ^ *cascade08Œ^^ *cascade08^^ *cascade08^^*cascade08^^ *cascade08^¥^*cascade08¥^˜_ *cascade08˜_Ÿ_*cascade08Ÿ_¬_ *cascade08¬_­_*cascade08­_®_ *cascade08®_±_*cascade08±_¹_ *cascade08¹_Á_*cascade08Á_Â_ *cascade08Â_Ã_ *cascade08Ã_Ä_*cascade08Ä_Ç_ *cascade08Ç_È_*cascade08È_É_ *cascade08É_Ë_*cascade08Ë_Í_ *cascade08Í_Ï_ *cascade08Ï_Õ_*cascade08Õ_â_ *cascade08â_å_*cascade08å_ê_ *cascade08ê_ì_*cascade08ì_í_ *cascade08í_ñ_*cascade08ñ_ó_ *cascade08ó_ô_*cascade08ô_ö_ *cascade08ö_÷_*cascade08÷_ø_ *cascade08ø_û_*cascade08û_ı_ *cascade08ı_`*cascade08`` *cascade08`‘`*cascade08‘`’` *cascade08’`—`*cascade08—`˜` *cascade08˜`š`*cascade08š`³` *cascade08³`¾`*cascade08¾`¿` *cascade08¿`À`*cascade08À`Á` *cascade08Á`Ã`*cascade08Ã`Ä` *cascade08Ä`Å`*cascade08Å`Æ` *cascade08Æ`É`*cascade08É`Ê` *cascade08Ê`Î`*cascade08Î`Ò` *cascade08Ò`Ó`*cascade08Ó`Ô` *cascade08Ô`Ö`*cascade08Ö`×` *cascade08×`Û`*cascade08Û`Ü` *cascade08Ü`ß`*cascade08ß`á` *cascade08á`æ`*cascade08æ`ö` *cascade08ö`Ïc *cascade08Ïcäc*cascade08äc•e *cascade08•e–e*cascade08–e—e *cascade08—e¥e*cascade08¥e¦e *cascade08¦e©e*cascade08©eªe *cascade08ªe­e*cascade08­e®e *cascade08®e±e*cascade08±e²e *cascade08²e¼e*cascade08¼e½e *cascade08½e¿e*cascade08¿eÊe *cascade08ÊeËe*cascade08ËeÌe *cascade08ÌeÎe*cascade08ÎeÏe *cascade08ÏeÓe*cascade08ÓeÔe *cascade08Ôe×e*cascade08×eÙe *cascade08ÙeŞe*cascade08Şeße *cascade08ßeáe*cascade08áešg *cascade08šg¡g*cascade08¡g¢g *cascade08¢g¤g*cascade08¤g§g *cascade08§gªg*cascade08ªg±g *cascade08±gÍg*cascade08ÍgĞg *cascade08ĞgÕg*cascade08ÕgÖg *cascade08Ög×g*cascade08×gØg *cascade08ØgÙg*cascade08ÙgŞg *cascade08Şgág*cascade08ágâg *cascade08âgîg*cascade08îgğg *cascade08ğgùg*cascade08ùgúg *cascade08úgüg*cascade08ügıg *cascade08ıgşg*cascade08şg€h *cascade08€h‰h*cascade08‰h”r *cascade082Rfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/strategy/lw_001.py