"""
Strategy tests for EVRECONSE.

Tests demonstrating strategy registration and execution works correctly.
"""

from __future__ import annotations

import pytest

from strategy import (
    LW001Strategy,
    StrategyConfig,
    StrategyContext,
    StrategyEngine,
    StrategyEngineConfig,
    StrategyRegistry,
)
from strategy.exceptions import (
    StrategyAlreadyRegisteredError,
    StrategyNotFoundError,
    StrategyValidationError,
)
from tests.fixtures.fake_data_provider import create_fake_data_provider
from tests.utils.helpers import create_market_event


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    @pytest.fixture
    def registry(self) -> StrategyRegistry:
        """Create a fresh registry."""
        return StrategyRegistry()

    @pytest.fixture
    def strategy_config(self) -> StrategyConfig:
        """Create a test strategy config."""
        return StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={
                "min_confidence_score": 80,
            },
            enabled=True,
        )

    def test_register_strategy(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test registering a strategy."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        assert registry.is_enabled("LW-001")
        assert registry.get("LW-001") is strategy

    def test_register_duplicate_raises(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test that registering duplicate raises error."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        with pytest.raises(StrategyAlreadyRegisteredError):
            registry.register(LW001Strategy(), strategy_config)

    def test_unregister_strategy(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test unregistering a strategy."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        registry.unregister("LW-001")
        with pytest.raises(StrategyNotFoundError):
            registry.get("LW-001")
        assert not registry.is_enabled("LW-001")

    def test_get_not_found_raises(self, registry: StrategyRegistry) -> None:
        """Test getting non-existent strategy raises error."""
        with pytest.raises(StrategyNotFoundError):
            registry.get("NONEXISTENT")

    def test_list_strategies(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test listing strategies."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        strategies = registry.list_strategies()
        assert len(strategies) == 1
        assert strategies[0].strategy_id == "LW-001"

    def test_get_enabled(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test getting enabled strategy IDs."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        enabled = registry.get_enabled()
        assert "LW-001" in enabled

    def test_enable_disable(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test enabling/disabling strategy."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)

        registry.disable("LW-001")
        disabled_registration = registry.get_registration("LW-001")
        disabled_config = registry.get_strategy_config("LW-001")
        assert disabled_registration is not None
        assert disabled_config is not None
        assert registry.is_enabled("LW-001") is False
        assert disabled_registration.enabled is False
        assert disabled_config.enabled is True  # stored config unchanged

        registry.enable("LW-001")
        enabled_registration = registry.get_registration("LW-001")
        enabled_config = registry.get_strategy_config("LW-001")
        assert enabled_registration is not None
        assert enabled_config is not None
        assert registry.is_enabled("LW-001") is True
        assert enabled_registration.enabled is True
        assert enabled_config.enabled is True

    def test_update_config(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test updating strategy config."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        new_config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.1",
            parameters={"min_confidence_score": 90},
            enabled=False,
        )

        registry.update_config("LW-001", new_config)

        stored_config = registry.get_strategy_config("LW-001")
        assert stored_config == new_config
        assert registry.is_enabled("LW-001") is False
        assert registry.list_strategies(enabled_only=True) == []

    def test_get_all_strategies(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test getting all strategies."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        strategies = registry.get_all_strategies()
        assert len(strategies) == 1

    def test_get_enabled_strategies(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test getting enabled strategies."""
        strategy = LW001Strategy()
        registry.register(strategy, strategy_config)
        enabled = registry.get_enabled_strategies()
        assert len(enabled) == 1

    def test_clear(self, registry: StrategyRegistry, strategy_config: StrategyConfig) -> None:
        """Test clearing registry."""
        registry.register(LW001Strategy(), strategy_config)
        registry.clear()

        assert registry.list_strategies() == []
        assert registry.get_enabled() == []
        with pytest.raises(StrategyNotFoundError):
            registry.get("LW-001")


class TestStrategyEngine:
    """Tests for StrategyEngine."""

    @pytest.fixture
    def engine(self) -> StrategyEngine:
        """Create a fresh engine."""
        return StrategyEngine(StrategyEngineConfig())

    @pytest.fixture
    def fake_provider(self):
        """Create a fake data provider."""
        return create_fake_data_provider()

    def test_register_strategy(self, engine: StrategyEngine) -> None:
        """Test registering a strategy with engine."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={"min_confidence_score": 80},
            enabled=True,
        )

        engine.register_strategy(strategy, config)

        assert engine.get_strategy("LW-001") is strategy
        assert "LW-001" in engine.list_strategies()
        with pytest.raises(StrategyAlreadyRegisteredError):
            engine.register_strategy(strategy, config)

    def test_unregister_strategy(self, engine: StrategyEngine) -> None:
        """Test unregistering a strategy."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={},
            enabled=True,
        )
        engine.register_strategy(strategy, config)
        engine.unregister_strategy("LW-001")
        with pytest.raises(StrategyNotFoundError):
            engine.get_strategy("LW-001")

    def test_get_strategy(self, engine: StrategyEngine) -> None:
        """Test getting a strategy."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={},
            enabled=True,
        )
        engine.register_strategy(strategy, config)
        retrieved = engine.get_strategy("LW-001")
        assert retrieved is strategy

    def test_list_strategies(self, engine: StrategyEngine) -> None:
        """Test listing strategies."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={},
            enabled=True,
        )
        engine.register_strategy(strategy, config)
        assert "LW-001" in engine.list_strategies()

    def test_activate_deactivate(self, engine: StrategyEngine) -> None:
        """Test activating/deactivating strategy."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={},
            enabled=True,
        )
        engine.register_strategy(strategy, config)
        engine.deactivate_strategy("LW-001")
        assert not engine.is_active("LW-001")
        engine.activate_strategy("LW-001")
        assert engine.is_active("LW-001")

    def test_get_metrics(self, engine: StrategyEngine) -> None:
        """Test getting engine metrics."""
        metrics = engine.get_metrics()
        assert "registered_strategies" in metrics
        assert "active_strategies" in metrics
        assert "total_executions" in metrics


class TestLW001Strategy:
    """Tests for LW001Strategy."""

    def test_strategy_metadata(self) -> None:
        """Test strategy metadata."""
        strategy = LW001Strategy()
        assert strategy.strategy_id == "LW-001"
        assert strategy.name == "Long Lower Wick Reversal"
        assert strategy.version == "1.0.0"
        assert "bingx" in strategy.supported_markets
        assert "15m" in strategy.supported_timeframes

    def test_validate_config_valid(self) -> None:
        """Test validating valid config (no threshold overrides)."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={
                "take_profit_percent": 3.0,
                "stop_loss_percent": -3.0,
                "min_confidence_score": 80,
            },
            enabled=True,
        )
        strategy.validate_config(config)  # Should not raise

    def test_validate_config_invalid_wick_ratio(self) -> None:
        """Test validating config with forbidden threshold override."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={"lower_wick_ratio": 0.5},  # Forbidden: threshold override
            enabled=True,
        )
        with pytest.raises(StrategyValidationError, match="lower_wick_ratio"):
            strategy.validate_config(config)

    def test_validate_config_invalid_liq_window(self) -> None:
        """Test validating config with forbidden threshold override."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={"liquidation_window": 1},  # Forbidden: threshold override
            enabled=True,
        )
        with pytest.raises(StrategyValidationError, match="liquidation_window"):
            strategy.validate_config(config)

    def test_validate_config_invalid_min_score(self) -> None:
        """Test validating config with invalid min score."""
        strategy = LW001Strategy()
        config = StrategyConfig(
            strategy_id="LW-001",
            version="1.0.0",
            parameters={"min_confidence_score": 150},  # Invalid: > 100
            enabled=True,
        )
        with pytest.raises(StrategyValidationError, match="min_confidence_score"):
            strategy.validate_config(config)

    def test_supports(self) -> None:
        """Test supports method."""
        strategy = LW001Strategy()
        config = StrategyConfig(strategy_id="LW-001", version="1.0.0", parameters={}, enabled=True)

        supported = strategy.supports(
            StrategyContext(market_event=create_market_event(), config=config)
        )
        assert supported is True

        from models import Timeframe

        wrong_timeframe = strategy.supports(
            StrategyContext(
                market_event=create_market_event(timeframe=Timeframe.M5),
                config=config,
            )
        )
        assert wrong_timeframe is False
