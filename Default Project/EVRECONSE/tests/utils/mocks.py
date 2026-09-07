"""
Test utilities and helpers for EVRECONSE tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock


def make_mock_with_spec(spec_class: type, **kwargs: Any) -> MagicMock:
    """Create a MagicMock with the spec of the given class."""
    return MagicMock(spec=spec_class, **kwargs)


def make_async_mock_with_spec(spec_class: type, **kwargs: Any) -> AsyncMock:
    """Create an AsyncMock with the spec of the given class."""
    return AsyncMock(spec=spec_class, **kwargs)


def mock_async_method(return_value: Any = None, side_effect: Any = None) -> AsyncMock:
    """Create an AsyncMock for an async method."""
    return AsyncMock(return_value=return_value, side_effect=side_effect)


def mock_method(return_value: Any = None, side_effect: Any = None) -> MagicMock:
    """Create a MagicMock for a sync method."""
    return MagicMock(return_value=return_value, side_effect=side_effect)


def assert_called_once_with(mock: MagicMock, *args: Any, **kwargs: Any) -> None:
    """Assert mock was called once with specific arguments."""
    mock.assert_called_once_with(*args, **kwargs)


def assert_called_with(mock: MagicMock, *args: Any, **kwargs: Any) -> None:
    """Assert mock was called with specific arguments (any number of times)."""
    mock.assert_called_with(*args, **kwargs)


def assert_not_called(mock: MagicMock) -> None:
    """Assert mock was not called."""
    mock.assert_not_called()


class MockRegistry:
    """Registry of created mocks for cleanup."""

    def __init__(self) -> None:
        self._mocks: list[MagicMock] = []

    def create_mock(self, spec: type | None = None, **kwargs: Any) -> MagicMock:
        mock = MagicMock(spec=spec, **kwargs)
        self._mocks.append(mock)
        return mock

    def create_async_mock(self, spec: type | None = None, **kwargs: Any) -> AsyncMock:
        mock = AsyncMock(spec=spec, **kwargs)
        self._mocks.append(mock)
        return mock

    def reset_all(self) -> None:
        for mock in self._mocks:
            mock.reset_mock()

    def assert_all_called(self) -> None:
        for mock in self._mocks:
            mock.assert_called()

    def get_call_counts(self) -> dict[str, int]:
        return {mock._mock_name or f"mock_{i}": mock.call_count for i, mock in enumerate(self._mocks)}


def create_mock_registry() -> MockRegistry:
    """Create a new mock registry."""
    return MockRegistry()