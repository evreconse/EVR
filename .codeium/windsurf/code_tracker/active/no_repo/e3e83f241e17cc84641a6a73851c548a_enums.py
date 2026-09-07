Â	"""
EVRECONSE Models - Enums.

Only enums that protect business invariants and are required for type safety.
Enums that limit extensibility without protecting invariants are removed.
"""

from __future__ import annotations

from enum import Enum


class EventStatus(str, Enum):
    """Event lifecycle statuses."""

    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    SCORED = "SCORED"
    SIGNAL = "SIGNAL"
    DISMISSED = "DISMISSED"
    MONITORING = "MONITORING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class EventOutcome(str, Enum):
    """Outcome of a completed signal tracking."""

    TP = "TP"
    SL = "SL"


class Exchange(str, Enum):
    """Supported exchanges."""

    BINGX = "bingx"
    BYBIT = "bybit"


class Timeframe(str, Enum):
    """Supported candle timeframes."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    TELEGRAM = "telegram"


class ScoreParameter(str, Enum):
    """Scoring parameter names - protects invariant of valid parameter names."""

    LOWER_WICK_QUALITY = "lower_wick_quality"
    CANDLE_CONFIRMATION = "candle_confirmation"Â	 *cascade082Ofile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/models/enums.py