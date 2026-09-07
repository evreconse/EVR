°"""
EVRECONSE Scoring - Candle Confirmation Parameter.

Evaluates candle body confirmation and close position.
"""

from __future__ import annotations

from ..exceptions import ScoringComputationError, ScoringValidationError
from ..parameter import ScoringParameter


class CandleConfirmationScore(ScoringParameter):
    """
    Evaluates candle body confirmation and close position quality.
    """

    @property
    def parameter_id(self) -> str:
        return "candle_confirmation"

    @property
    def name(self) -> str:
        return "Candle Confirmation"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Evaluates candle body confirmation and close position quality"

    @property
    def max_score(self) -> float:
        return 30.0

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def min_score(self) -> float:
        return 0.0

    def supports(self, context) -> bool:
        if not context.market_event or not context.market_event.market_data:
            return False
        return True

    def validate_config(self, config) -> None:
        # No specific validation needed for this parameter
        pass

    async def evaluate(self, context):
        try:
            market_data = context.market_event.market_data
            if not market_data:
                return 0.0, [], "No market data available"

            open_price = market_data.open
            high_price = market_data.high
            low_price = market_data.low
            close_price = market_data.close
            volume = market_data.volume

            body = close_price - open_price
            body_size = abs(body)
            candle_range = high_price - low_price

            if candle_range == 0:
                return 0.0, [], "Zero candle range"

            body_size = abs(body)
            body_ratio = body_size / candle_range

            if body > 0:  # Bullish candle
                if body_ratio >= 0.6:
                    score = 30.0
                    explanation = f"Strong bullish body: {body_ratio:.1%} of range"
                elif body_ratio >= 0.4:
                    score = 25.0
                    explanation = f"Good bullish body: {body_ratio:.1%} of range"
                elif body_ratio >= 0.2:
                    score = 20.0
                    explanation = f"Moderate bullish body: {body_ratio:.1%} of range"
                elif body_ratio >= 0.1:
                    score = 15.0
                    explanation = f"Weak bullish body: {body_ratio:.1%} of range"
                else:
                    score = 10.0
                    explanation = f"Doji-like: {body_ratio:.1%} of range"

                # Bonus for close near high
                close_position = (close_price - low_price) / (high_price - low_price)
                if close_position >= 0.8:
                    score = min(30.0, score + 5.0)
                    explanation += " | Close near high"
            else:
                # Bearish or doji
                if abs(body) > 0:
                    body_ratio = abs(close_price - open_price) / (high_price - low_price)
                    if body_ratio >= 0.4:
                        score = 20.0
                    else:
                        score = 10.0
                else:
                    score = 10.0

            explanation = f"Candle confirmation: {score}/30"
            return min(score, 30.0), [], f"Candle confirmation: {score}/30"

        except Exception as e:
            from ..exceptions import ScoringComputationError
            raise ScoringComputationError(f"Candle confirmation evaluation failed: {e}", "candle_confirmation") from eº *cascade08º¼*cascade08¼ü *cascade08üıış *cascade08şÿÿ— *cascade08—™*cascade08™µ *cascade08µ¶*cascade08¶Ï *cascade08ÏÑ*cascade08Ñï *cascade08ïğ*cascade08ğ÷ *cascade08÷ù*cascade08ù“ *cascade08“•*cascade08•Ø *cascade08ØÚ*cascade08Ú— *cascade08—™*cascade08™Î *cascade08ÎĞ*cascade08Ğ *cascade08*cascade08¯ *cascade08¯±*cascade08±Ù *cascade08ÙÛ*cascade08Û° *cascade082ifile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/scoring/parameters/candle_confirmation.py