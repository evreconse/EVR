æ"""
EVRECONSE Scoring - Lower Wick Quality Parameter.

Evaluates the quality of the lower wick relative to body size.
"""

from __future__ import annotations

from typing import Any

from ..context import (
    ScoringContext,
)
from ..exceptions import ScoringComputationError, ScoringValidationError
from ..parameter import ScoringParameter


class LowerWickQualityScore(ScoringParameter):
    """
    Evaluates lower wick quality based on wick-to-body ratio
    and absolute wick size.
    """

    @property
    def parameter_id(self) -> str:
        return "lower_wick_quality"

    @property
    def name(self) -> str:
        return "Lower Wick Quality"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Evaluates lower wick quality based on wick-to-body ratio and absolute wick size"

    @property
    def max_score(self) -> float:
        return 70.0

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def min_score(self) -> float:
        return 0.0

    def supports(self, context: ScoringContext) -> bool:
        if not context.market_event or not context.market_event.market_data:
            return False
        if not context.market_event.strategy_data:
            return False
        return True

    def validate_config(self, config: Any) -> None:
        params = config.parameters
        wick_ratio = params.get("lower_wick_ratio", 2.0)
        if not isinstance(wick_ratio, (int, float)) or wick_ratio < 1.0:
            raise ScoringValidationError(
                "lower_wick_ratio must be a number >= 1.0",
                field="lower_wick_ratio"
            )

    async def evaluate(self, context: ScoringContext) -> tuple[float, list[Any], str]:
        try:
            market_data = context.market_event.market_data
            strategy_data = context.market_event.strategy_data
            
            if not market_data or not market_data.open:
                return 0.0, [], "No market data available"
            
            if not context.market_event.strategy_data:
                return 0.0, [], "No strategy data available"
            
            strategy_data = context.market_event.strategy_data
            lower_wick = strategy_data.lower_wick
            body = strategy_data.body
            lower_wick_ratio = context.config.parameters.get("lower_wick_ratio", 2.0)

            if body <= 0:
                return 25.0, [], "Doji-like candle (no body)"

            ratio = lower_wick / body if body > 0 else 0

            if ratio >= 3.0:
                score = 70.0
                explanation = f"Excellent wick-to-body ratio: {ratio:.2f}x"
            elif ratio >= 2.5:
                score = 60.0
                explanation = f"Strong wick-to-body ratio: {ratio:.2f}x"
            elif ratio >= 2.0:
                score = 50.0
                explanation = f"Good wick-to-body ratio: {ratio:.2f}x"
            elif ratio >= 1.5:
                score = 35.0
                explanation = f"Moderate wick-to-body ratio: {ratio:.2f}x"
            elif ratio >= 1.0:
                score = 20.0
                explanation = f"Weak wick-to-body ratio: {ratio:.2f}x"
            else:
                score = 0.0
                explanation = f"Insufficient wick-to-body ratio: {ratio:.2f}x"

            return score, [], explanation

        except Exception as e:
            raise ScoringComputationError(f"Lower wick evaluation failed: {e}", "lower_wick_quality") from e« *cascade08«¬*cascade08¬í *cascade08íîî¸ *cascade08¸¹*cascade08¹Ï *cascade08ÏÐ*cascade08Ð× *cascade08×Ù*cascade08ÙÜ *cascade08ÜÝ*cascade08Ýß *cascade08ßá*cascade08áæ *cascade08æç*cascade08çæ *cascade082`file:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/scoring/parameters/lower_wick.py