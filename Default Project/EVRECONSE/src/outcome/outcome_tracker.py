"""Outcome Tracker for TP/SL monitoring."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from models import EventID, EventOutcome, EventStatus, MarketEvent


class MonitoringStatus(Enum):
    """Status of outcome monitoring."""
    ACTIVE = "active"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class OutcomeConfig:
    """Configuration for outcome tracking."""
    take_profit_percent: float = 3.0
    stop_loss_percent: float = -3.0
    max_duration_hours: int = 24
    expire_after_hours: int = 48

    @classmethod
    def from_dict(cls, data: dict) -> OutcomeConfig:
        """Create from config dict."""
        risk = data.get("risk", {})
        monitoring = risk.get("monitoring", {})
        return cls(
            take_profit_percent=risk.get("take_profit_percent", 3.0),
            stop_loss_percent=risk.get("stop_loss_percent", -3.0),
            max_duration_hours=monitoring.get("max_duration_hours", 24),
            expire_after_hours=monitoring.get("expire_after_hours", 48),
        )


@dataclass(slots=True)
class MonitoredSignal:
    """A signal being monitored for outcome."""
    signal_id: EventID
    entry_price: float
    tp_price: float
    sl_price: float
    entry_time: datetime
    symbol: str
    status: MonitoringStatus = MonitoringStatus.ACTIVE
    outcome: Optional[EventOutcome] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None

    def is_expired(self, config: OutcomeConfig) -> bool:
        """Check if signal has expired."""
        expiry_time = self.entry_time + timedelta(hours=config.expire_after_hours)
        return datetime.now(timezone.utc) > expiry_time

    def should_stop_monitoring(self, config: OutcomeConfig) -> bool:
        """Check if monitoring should stop."""
        if self.status != MonitoringStatus.ACTIVE:
            return True
        return self.is_expired(config)


class OutcomeTracker:
    """Tracks outcomes for trading signals."""

    def __init__(self, config: OutcomeConfig):
        self._config = config
        self._monitored: dict[EventID, MonitoredSignal] = {}
        self._lock = asyncio.Lock()

    async def start_monitoring(
        self,
        signal: MarketEvent,
        entry_price: float,
    ) -> MonitoredSignal:
        """Start monitoring a signal."""
        async with self._lock:
            tp_price = entry_price * (1 + self._config.take_profit_percent / 100)
            sl_price = entry_price * (1 + self._config.stop_loss_percent / 100)

            monitored = MonitoredSignal(
                signal_id=signal.id,
                entry_price=entry_price,
                tp_price=tp_price,
                sl_price=sl_price,
                entry_time=datetime.now(timezone.utc),
                symbol=signal.data.market.symbol,
            )

            self._monitored[signal.id] = monitored
            return monitored

    async def update_price(
        self,
        signal_id: EventID,
        current_price: float,
    ) -> Optional[MonitoredSignal]:
        """Update with current price and check for TP/SL."""
        async with self._lock:
            monitored = self._monitored.get(signal_id)
            if not monitored or monitored.status != MonitoringStatus.ACTIVE:
                return None

            # Check TP
            if current_price >= monitored.tp_price:
                monitored.status = MonitoringStatus.TP_HIT
                monitored.outcome = EventOutcome.TAKE_PROFIT
                monitored.exit_price = current_price
                monitored.exit_time = datetime.now(timezone.utc)
                return monitored

            # Check SL
            if current_price <= monitored.sl_price:
                monitored.status = MonitoringStatus.SL_HIT
                monitored.outcome = EventOutcome.STOP_LOSS
                monitored.exit_price = current_price
                monitored.exit_time = datetime.now(timezone.utc)
                return monitored

            # Check expiration
            if monitored.is_expired(self._config):
                monitored.status = MonitoringStatus.EXPIRED
                monitored.outcome = EventOutcome.EXPIRED
                monitored.exit_price = current_price
                monitored.exit_time = datetime.now(timezone.utc)
                return monitored

            return None

    async def get_monitored(self, signal_id: EventID) -> Optional[MonitoredSignal]:
        """Get monitored signal."""
        async with self._lock:
            return self._monitored.get(signal_id)

    async def remove_monitored(self, signal_id: EventID) -> bool:
        """Remove from monitoring."""
        async with self._lock:
            if signal_id in self._monitored:
                del self._monitored[signal_id]
                return True
            return False

    async def get_all_active(self) -> list[MonitoredSignal]:
        """Get all actively monitored signals."""
        async with self._lock:
            return [
                m for m in self._monitored.values()
                if m.status == MonitoringStatus.ACTIVE
            ]

    async def cleanup_expired(self) -> list[MonitoredSignal]:
        """Remove and return expired signals."""
        async with self._lock:
            expired = []
            to_remove = []

            for signal_id, monitored in self._monitored.items():
                if monitored.should_stop_monitoring(self._config):
                    expired.append(monitored)
                    to_remove.append(signal_id)

            for signal_id in to_remove:
                del self._monitored[signal_id]

            return expired
