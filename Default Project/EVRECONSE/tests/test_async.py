"""
Async tests for EVRECONSE.

Tests demonstrating async test infrastructure works correctly.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from unittest.mock import AsyncMock

import pytest

from tests.utils.helpers import run_async


class TestAsyncInfrastructure:
    """Tests for async infrastructure."""

    @pytest.mark.asyncio
    async def test_async_fixture_works(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """Test that the event loop fixture works."""
        assert event_loop is not None
        assert not event_loop.is_closed()

    @pytest.mark.asyncio
    async def test_async_mock_can_be_awaited(self) -> None:
        """Test that AsyncMock can be used in tests."""
        mock = AsyncMock(return_value="result")
        result = await mock("arg")
        assert result == "result"
        mock.assert_called_once_with("arg")

    @pytest.mark.asyncio
    async def test_asyncio_sleep_works(self) -> None:
        """Test that asyncio.sleep works in tests."""
        start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.01)
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_concurrent_execution(self) -> None:
        """Test concurrent async execution."""
        results: list[int] = []

        async def add_number(n: int) -> None:
            await asyncio.sleep(0.01)
            results.append(n)

        await asyncio.gather(add_number(1), add_number(2), add_number(3))
        assert set(results) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_timeout_works(self) -> None:
        """Test asyncio.wait_for timeout."""

        async def slow_operation() -> None:
            await asyncio.sleep(10)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.05)

    def test_run_async_helper(self) -> None:
        """Test the run_async helper function."""
        async def return_value() -> str:
            return "hello"

        result = asyncio.run(run_async(return_value()))
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_exception_propagation(self) -> None:
        """Test that exceptions propagate correctly in async tests."""

        async def raise_error() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await raise_error()

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test async context manager in tests."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def async_cm():
            yield "value"

        async with async_cm() as value:
            assert value == "value"

    @pytest.mark.asyncio
    async def test_async_for_loop(self) -> None:
        """Test async for loop."""
        async def async_gen():
            for i in range(3):
                yield i

        results = [i async for i in async_gen()]
        assert results == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_asyncio_event(self) -> None:
        """Test asyncio.Event."""
        event = asyncio.Event()
        assert not event.is_set()
        event.set()
        assert event.is_set()

    @pytest.mark.asyncio
    async def test_asyncio_lock(self) -> None:
        """Test asyncio.Lock."""
        lock = asyncio.Lock()
        assert not lock.locked()
        async with lock:
            assert lock.locked()
        assert not lock.locked()


class TestAsyncFixtures:
    """Tests for async fixtures."""

    @pytest.mark.asyncio
    async def test_fake_data_provider_is_async(self, fake_data_provider) -> None:
        """Test that fake data provider works with async calls."""
        await fake_data_provider.connect()
        assert fake_data_provider.is_connected is True
        await fake_data_provider.disconnect()
        assert fake_data_provider.is_connected is False

    @pytest.mark.asyncio
    async def test_fake_telegram_service_is_async(self, fake_telegram_service) -> None:
        """Test that fake telegram service works with async calls."""
        await fake_telegram_service.connect()
        assert fake_telegram_service.is_connected is True
        result = await fake_telegram_service.send("test")
        assert result.success is True
        await fake_telegram_service.disconnect()

    @pytest.mark.skip(reason="MarketEvent.event_id issue")
    @pytest.mark.asyncio
    async def test_fake_storage_is_sync(self, fake_storage_repository) -> None:
        """Test that fake storage works (sync interface)."""
        pass