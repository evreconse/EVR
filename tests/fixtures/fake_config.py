"""
Fake ConfigLoader for testing.

Returns a test AppConfig without loading from files or environment.
"""

from __future__ import annotations

from typing import Any

from config.loader import ConfigLoader


class FakeConfigLoader(ConfigLoader):
    """Fake config loader that returns a default test configuration."""

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._overrides = overrides or {}

    def load(self) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "exchange": {
                "name": "bybit",
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "api_key": "test_key",
                "api_secret": "test_secret",
                "testnet": True,
            },
            "strategy": {
                "active": ["LW-001"],
                "strategies": {
                    "LW-001": {
                        "enabled": True,
                        "timeframe": "15m",
                        "condition": {
                            "lower_wick_ratio": 2,
                            "liquidation_window": 12,
                        },
                        "risk": {
                            "take_profit_percent": 3.0,
                            "stop_loss_percent": -3.0,
                        },
                        "notification": {
                            "channels": ["telegram"],
                        },
                    },
                },
            },
            "scoring": {
                "minimum_signal_score": 80,
                "maximum_score": 100,
                "minimum_score": 0,
                "parameters_active": [
                    "lower_wick_quality",
                    "liquidation_strength",
                    "candle_confirmation",
                ],
                "parameters": {
                    "lower_wick_quality": {"enabled": True, "max_score": 40},
                    "liquidation_strength": {"enabled": True, "max_score": 35},
                    "candle_confirmation": {"enabled": True, "max_score": 25},
                },
            },
            "notification": {
                "channels": ["telegram"],
                "telegram": {
                    "enabled": True,
                    "bot_token": "test_token",
                    "chat_id": "123456",
                },
            },
            "storage": {
                "data_path": "./data",
            },
            "system": {
                "log_level": "INFO",
                "log_path": "./logs",
            },
        }
        raw.update(self._overrides)
        return raw

    def get_source_name(self) -> str:
        return "fake (test defaults)"


def create_fake_config_loader(overrides: dict[str, Any] | None = None) -> FakeConfigLoader:
    """Factory function to create a fake config loader."""
    return FakeConfigLoader(overrides=overrides)