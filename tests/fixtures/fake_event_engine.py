"""
Fake Event Engine for testing.

Provides a fake EventEngine that does not start real event processing.
"""

from __future__ import annotations

from typing import Any


class FakeEventEngine:
    """Fake EventEngine for unit tests."""

    def __init__(self) -> None:
        self.is_running = False
        self.is_initialized = False
        self._processed_events = 0
        self._succeeded_events = 0
        self._failed_events = 0

    def initialize(self, config: dict | None = None) -> None:
        self.is_initialized = True

    def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False

    async def shutdown(self) -> None:
        self.is_running = False
        self.is_initialized = False

    async def reload(self, config: dict | None = None) -> None:
        await self.stop()
        self.initialize(config)
        self.start()

    def process_market_data(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        event_time: Any,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> dict:
        self._processed_events += 1
        return {
            "success": True,
            "event_id": "test-event-id",
            "final_status": "NEW",
            "duration_ms": 0.0,
            "score": 0.0,
            "qualified": False,
            "error": None,
        }

    def process_event(self, event: Any) -> dict:
        self._processed_events += 1
        self._succeeded_events += 1
        return {
            "success": True,
            "event_id": str(getattr(event, "event_id", "unknown")),
            "final_status": "NEW",
            "duration_ms": 0.0,
            "score": 0.0,
            "qualified": False,
            "error": None,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "processed": self._processed_events,
            "succeeded": self._succeeded_events,
            "failed": self._failed_events,
        }

    def get_metrics(self) -> dict[str, Any]:
        return {"metrics_enabled": False}


def create_fake_event_engine() -> FakeEventEngine:
    """Factory function to create a fake event engine."""
    return FakeEventEngine()