"""
Scoring tests for EVRECONSE.

Tests demonstrating scoring parameter registration and evaluation works correctly.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from scoring import (
    CandleConfirmationScore,
    LowerWickQualityScore,
    ScoringEngine,
    ScoringEngineConfig,
    ScoringParameterRegistry,
    get_registry,
    reset_registry,
)
from scoring.context import ScoringConfig, ScoringContext
from scoring.exceptions import (
    ParameterAlreadyRegisteredError,
    ParameterNotFoundError,
    ScoringNotInitializedError,
)
from tests.utils.helpers import advance_event_to_qualified, create_market_event


class TestScoringParameterRegistry:
    """Tests for ScoringParameterRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry_fixture(self) -> Iterator[None]:
        """Reset registry before each test."""
        reset_registry()
        yield
        reset_registry()

    @pytest.fixture
    def registry(self) -> ScoringParameterRegistry:
        """Create a fresh registry."""
        return ScoringParameterRegistry()

    @pytest.fixture
    def scoring_config(self) -> ScoringConfig:
        """Create a test scoring config."""
        return ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={"lower_wick_ratio": 2.0},
            enabled=True,
            min_confidence_score=80.0,
        )

    def test_register_parameter(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test registering a scoring parameter."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        assert registry.is_enabled("lower_wick_quality")
        assert registry.get("lower_wick_quality") is param

    def test_register_duplicate_raises(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test that registering duplicate raises error."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        with pytest.raises(ParameterAlreadyRegisteredError):
            registry.register(LowerWickQualityScore(), scoring_config)

    def test_unregister_parameter(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test unregistering a parameter."""
        registry.register(LowerWickQualityScore(), scoring_config)

        registry.unregister("lower_wick_quality")

        assert registry.count() == 0
        assert registry.list_parameters() == []
        assert registry.get_enabled() == []
        with pytest.raises(ParameterNotFoundError):
            registry.get("lower_wick_quality")

    def test_get_not_found_raises(self, registry: ScoringParameterRegistry) -> None:
        """Test getting non-existent parameter raises error."""
        with pytest.raises(ParameterNotFoundError):
            registry.get("nonexistent")

    def test_list_parameters(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test listing parameters."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        params = registry.list_parameters()
        assert "lower_wick_quality" in params

    def test_get_enabled(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test getting enabled parameter IDs."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        enabled = registry.get_enabled()
        assert "lower_wick_quality" in enabled

    def test_enable_disable(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test enabling and disabling parameters."""
        registry.register(LowerWickQualityScore(), scoring_config)

        registry.disable("lower_wick_quality")
        assert registry.is_enabled("lower_wick_quality") is False
        assert registry.get_registration("lower_wick_quality").enabled is False
        assert registry.get_enabled_parameters() == []

        registry.enable("lower_wick_quality")
        assert registry.is_enabled("lower_wick_quality") is True
        assert registry.get_registration("lower_wick_quality").enabled is True
        assert len(registry.get_enabled_parameters()) == 1

    def test_update_config(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test updating parameter config."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        new_config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={"lower_wick_ratio": 3.0},
            enabled=True,
            min_confidence_score=80.0,
        )
        registry.update_config("lower_wick_quality", new_config)
        updated = registry.get_config("lower_wick_quality")
        assert updated is not None
        assert updated.parameters["lower_wick_ratio"] == 3.0

    def test_get_all_parameters(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test getting all parameters."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        params = registry.get_all_parameters()
        assert len(params) == 1

    def test_get_enabled_parameters(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test getting enabled parameters."""
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        enabled = registry.get_enabled_parameters()
        assert len(enabled) == 1

    def test_count(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test counting parameters."""
        assert registry.count() == 0
        param = LowerWickQualityScore()
        registry.register(param, scoring_config)
        assert registry.count() == 1

    def test_clear(self, registry: ScoringParameterRegistry, scoring_config: ScoringConfig) -> None:
        """Test clearing registry."""
        registry.register(LowerWickQualityScore(), scoring_config)
        registry.clear()

        assert registry.count() == 0
        assert registry.list_parameters() == []
        with pytest.raises(ParameterNotFoundError):
            registry.get("lower_wick_quality")


class TestScoringEngine:
    """Tests for ScoringEngine."""

    @pytest.fixture
    def engine(self) -> Iterator[ScoringEngine]:
        """Create a fresh engine."""
        reset_registry()
        engine = ScoringEngine(ScoringEngineConfig())
        yield engine
        engine.close()
        reset_registry()

    def test_initialize_loads_parameters(self, engine: ScoringEngine) -> None:
        """Test that initialize loads enabled parameters from registry."""
        config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={"lower_wick_ratio": 2.0},
            enabled=True,
            min_confidence_score=80.0,
        )
        param = LowerWickQualityScore()
        get_registry().register(param, config)

        engine.initialize()

        assert engine.is_initialized() is True
        assert engine.get_parameters() == [param]

    def test_initialize_without_parameters(self, engine: ScoringEngine) -> None:
        """Test initialize with no parameters registered."""
        engine.initialize()
        assert engine.is_initialized()
        assert len(engine.get_parameters()) == 0

    @pytest.mark.asyncio
    async def test_evaluate_not_initialized_raises(self, engine: ScoringEngine) -> None:
        """Test that evaluate raises when not initialized."""
        context = ScoringContext(
            market_event=advance_event_to_qualified(create_market_event()),
            config=ScoringConfig(
                scoring_id="test",
                version="1.0.0",
                parameters={},
                enabled=True,
                min_confidence_score=80.0,
            ),
        )

        with pytest.raises(ScoringNotInitializedError):
            await engine.evaluate(context)

    def test_get_parameter(self, engine: ScoringEngine) -> None:
        """Test getting parameter by ID."""
        config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={},
            enabled=True,
            min_confidence_score=80.0,
        )
        param = LowerWickQualityScore()
        get_registry().register(param, config)
        engine.initialize()

        assert engine.get_parameter("lower_wick_quality") is param

    def test_get_parameter_not_found(self, engine: ScoringEngine) -> None:
        """Test getting non-existent parameter returns None."""
        engine.initialize()
        assert engine.get_parameter("nonexistent") is None

    def test_reload_parameters(self, engine: ScoringEngine) -> None:
        """Test reloading parameters from registry."""
        config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={},
            enabled=True,
            min_confidence_score=80.0,
        )
        get_registry().register(LowerWickQualityScore(), config)
        engine.initialize()
        assert len(engine.get_parameters()) == 1

        get_registry().disable("lower_wick_quality")
        engine.reload_parameters()

        assert engine.get_parameters() == []

    def test_get_stats(self, engine: ScoringEngine) -> None:
        """Test getting engine statistics."""
        stats = engine.get_stats()
        assert "initialized" in stats
        assert "parameter_count" in stats
        assert "config" in stats

    def test_close(self, engine: ScoringEngine) -> None:
        """Test closing engine."""
        engine.initialize()
        engine.close()
        assert not engine.is_initialized()


class TestScoringParameters:
    """Tests for individual scoring parameters."""

    def test_lower_wick_quality_metadata(self) -> None:
        """Test LowerWickQualityScore metadata."""
        param = LowerWickQualityScore()
        assert param.parameter_id == "lower_wick_quality"
        assert param.name == "Lower Wick Quality"
        assert param.version == "1.0.0"
        assert param.max_score == 70.0
        assert param.min_score == 0.0
        assert param.weight == 1.0

    def test_candle_confirmation_metadata(self) -> None:
        """Test CandleConfirmationScore metadata."""
        param = CandleConfirmationScore()
        assert param.parameter_id == "candle_confirmation"
        assert param.max_score == 30.0
        assert param.min_score == 0.0

    def test_validate_config(self) -> None:
        """Test parameter config validation."""
        param = LowerWickQualityScore()
        config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={"lower_wick_ratio": 2.0},
            enabled=True,
            min_confidence_score=80.0,
        )
        param.validate_config(config)  # Should not raise

    def test_supports(self) -> None:
        """Test supports method."""
        param = LowerWickQualityScore()
        event = advance_event_to_qualified(create_market_event())
        context = ScoringContext(
            market_event=event,
            config=ScoringConfig(
                scoring_id="lower_wick_quality",
                version="1.0.0",
                parameters={},
                enabled=True,
                min_confidence_score=80.0,
            ),
        )

        assert param.supports(context) is True

    @pytest.mark.asyncio
    async def test_evaluate(self) -> None:
        """Test parameter evaluation."""
        param = LowerWickQualityScore()
        event = advance_event_to_qualified(create_market_event())
        context = ScoringContext(
            market_event=event,
            config=ScoringConfig(
                scoring_id="lower_wick_quality",
                version="1.0.0",
                parameters={},
                enabled=True,
                min_confidence_score=80.0,
            ),
        )

        score, penalties, explanation = await param.evaluate(context)

        assert score == 50.0
        assert penalties == []
        assert "Good wick-to-body ratio" in explanation

    @pytest.mark.asyncio
    async def test_engine_aggregates_contributions(self) -> None:
        """Test that the engine aggregates parameter scores into a result."""
        reset_registry()
        config = ScoringConfig(
            scoring_id="lower_wick_quality",
            version="1.0.0",
            parameters={},
            enabled=True,
            min_confidence_score=80.0,
        )
        get_registry().register(LowerWickQualityScore(), config)
        engine = ScoringEngine(ScoringEngineConfig())
        try:
            engine.initialize()
            event = advance_event_to_qualified(create_market_event())
            result = await engine.evaluate(ScoringContext(market_event=event, config=config))
        finally:
            engine.close()

        assert result.final_score == 50.0
        assert len(result.contributions) == 1
        assert result.qualified is False  # 50 < 80
        assert result.metadata["parameter_count"] == 1
