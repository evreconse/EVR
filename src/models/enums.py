"""
EVRECONSE Models - Enums.

Only enums that protect business invariants and are required for type safety.
Enums that limit extensibility without protecting invariants are removed.
"""

from __future__ import annotations

from enum import StrEnum


class EventStatus(StrEnum):
    """Event lifecycle statuses."""

    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    SCORED = "SCORED"
    SIGNAL = "SIGNAL"
    DISMISSED = "DISMISSED"
    MONITORING = "MONITORING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class EventOutcome(StrEnum):
    """Outcome of a completed signal tracking."""

    TP = "TP"
    SL = "SL"


class Exchange(StrEnum):
    """Supported exchanges."""

    BINGX = "bingx"


class Timeframe(StrEnum):
    """Supported candle timeframes."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class NotificationChannel(StrEnum):
    """Supported notification channels."""

    TELEGRAM = "telegram"


class ScoreParameter(StrEnum):
    """Scoring parameter names - protects invariant of valid parameter names."""

    LOWER_WICK_QUALITY = "lower_wick_quality"
    CANDLE_CONFIRMATION = "candle_confirmation"
