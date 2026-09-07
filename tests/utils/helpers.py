"""
Test utilities and helpers for EVRECONSE tests.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models import EventStatus, Exchange, MarketEvent, Timeframe
from models.enums import EventOutcome


def create_market_event(
    symbol: str = "BTC-USDT",
    exchange: Exchange = Exchange.BINGX,
    timeframe: Timeframe = Timeframe.M15,
    open_price: float = 50000.0,
    high_price: float = 50100.0,
    low_price: float = 49900.0,
    close_price: float = 50050.0,
    volume: float = 100.5,
) -> MarketEvent:
    """Create a test MarketEvent."""
    return MarketEvent.new(
        symbol=symbol,
        exchange=exchange,
        timeframe=timeframe,
        event_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
    )


def advance_event_to_qualified(event: MarketEvent, strategy_id: str = "LW-001") -> MarketEvent:
    """Advance a MarketEvent to QUALIFIED status."""
    return event.qualified(
        strategy_id=strategy_id,
        lower_wick=100.0,
        body=50.0,
        wick_body_ratio=2.0,
        lower_wick_pct=66.6,
        body_pct=33.3,
    )


def advance_event_to_scored(event: MarketEvent, confidence_score: float = 85.0) -> MarketEvent:
    """Advance a MarketEvent to SCORED status."""
    return event.scored(
        confidence_score=confidence_score,
        score_breakdown=(
            ("lower_wick_quality", 40.0, 0.0),
            ("candle_confirmation", 35.0, 0.0),
        ),
    )


def advance_event_to_signal(event: MarketEvent, close_price: float = 50050.0) -> MarketEvent:
    """Advance a MarketEvent to SIGNAL status."""
    return event.notified(close_price=close_price)


def advance_event_to_monitoring(event: MarketEvent) -> MarketEvent:
    """Advance a MarketEvent to MONITORING status."""
    return event.monitoring()


def advance_event_to_completed(event: MarketEvent, outcome: EventOutcome = EventOutcome.TP, profit_pct: float = 3.0) -> MarketEvent:
    """Advance a MarketEvent to COMPLETED status."""
    return event.completed(outcome=outcome, actual_profit_pct=profit_pct)


def advance_event_to_expired(event: MarketEvent) -> MarketEvent:
    """Advance a MarketEvent to EXPIRED status."""
    return event.expired()


async def run_async(coro: Any, timeout: float = 5.0) -> Any:
    """Run an async coroutine with timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)


@asynccontextmanager
async def assert_raises_async(exception_type: type[Exception], match: str | None = None):
    """Context manager to assert an exception is raised in async code."""
    try:
        yield
    except exception_type as e:
        if match and match not in str(e):
            raise AssertionError(f"Expected '{match}' in exception message: {e}") from e
    except Exception as e:
        raise AssertionError(f"Expected {exception_type.__name__}, got {type(e).__name__}: {e}") from e
    else:
        raise AssertionError(f"Expected {exception_type.__name__} to be raised")


def assert_event_transition(event: MarketEvent, expected_status: EventStatus, message: str | None = None) -> None:
    """Assert that an event has transitioned to the expected status."""
    actual = event.metadata.status
    if actual != expected_status:
        msg = f"Expected status {expected_status.value}, got {actual.value}"
        if message:
            msg = f"{message}: {msg}"
        raise AssertionError(msg)


def assert_score_in_range(score: float, min_score: float = 0.0, max_score: float = 100.0) -> None:
    """Assert that a score is within the expected range."""
    if not (min_score <= score <= max_score):
        raise AssertionError(f"Score {score} not in range [{min_score}, {max_score}]")


def assert_event_qualified(event: MarketEvent) -> None:
    """Assert that an event is qualified (score >= threshold)."""
    if not event.metadata.status in {EventStatus.QUALIFIED, EventStatus.SCORED, EventStatus.SIGNAL, EventStatus.MONITORING, EventStatus.COMPLETED, EventStatus.EXPIRED}:
        raise AssertionError(f"Event not qualified: {event.metadata.status}")


def assert_event_dismissed(event: MarketEvent) -> None:
    """Assert that an event was dismissed."""
    if event.metadata.status != EventStatus.DISMISSED:
        raise AssertionError(f"Event not dismissed: {event.metadata.status}")


class AsyncTestCase:
    """Base class for async test cases with common utilities."""

    def __init__(self) -> None:
        self._events: list[MarketEvent] = []

    async def setup(self) -> None:
        """Override in subclasses for async setup."""

    async def teardown(self) -> None:
        """Override in subclasses for async teardown."""

    def record_event(self, event: MarketEvent) -> None:
        self._events.append(event)

    def get_recorded_events(self) -> list[MarketEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()


def temp_dir_path() -> Path:
    """Get a temporary directory path for test artifacts."""
    return Path(__file__).parent.parent / "temp"


def make_async_context_manager(coro_factory):
    """Create an async context manager from a coroutine factory."""
    @asynccontextmanager
    async def _manager():
        instance = await coro_factory()
        try:
            yield instance
        finally:
            if hasattr(instance, 'close') and callable(instance.close):
                await instance.close()
            elif hasattr(instance, 'disconnect') and callable(instance.disconnect):
                await instance.disconnect()
            elif hasattr(instance, 'shutdown') and callable(instance.shutdown):
                await instance.shutdown()
    return _manager()