"""
EVRECONSE Scoring - Scoring Engine.

Main engine for orchestrating scoring parameter evaluation.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .context import Penalty, ScoreContribution, ScoringContext, ScoringResult
    from .parameter import ScoringParameter
    from .registry import ScoringParameterRegistry

from .context import (
    Penalty,
    ScoreContribution,
    ScoringContext,
    ScoringResult,
)
from .exceptions import (
    ScoringComputationError,
    ScoringConfigurationError,
    ScoringNotInitializedError,
)
from .registry import ScoringParameterRegistry, get_registry


@dataclass(frozen=True, slots=True)
class ScoringEngineConfig:
    """Configuration for the Scoring Engine."""

    max_concurrent_parameters: int = 10
    execution_timeout: float = 5.0  # seconds
    enable_metrics: bool = True


class ScoringEngine:
    """
    Scoring Engine - orchestrates scoring parameter evaluation.

    Responsibilities:
    - Loading parameters from registry
    - Validating context
    - Running parameter evaluations concurrently
    - Aggregating results with weights
    - Applying penalties
    - Computing final score and qualification
    """

    def __init__(
        self,
        config: ScoringEngineConfig | None = None,
        registry: ScoringParameterRegistry | None = None,
    ) -> None:

        self._config = config or ScoringEngineConfig()
        self._registry = registry or get_registry()
        self._parameters: list[ScoringParameter] = []
        self._lock = threading.RLock()
        self._initialized = False

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the scoring engine with parameters from registry.

        Args:
            config: Optional configuration overrides
        """
        with self._lock:
            if self._initialized:
                return

            # Load enabled parameters from registry
            self._parameters = self._registry.get_enabled_parameters()

            self._initialized = True

    def is_initialized(self) -> bool:
        """Check if engine is initialized."""
        return self._initialized

    def get_parameters(self) -> list[ScoringParameter]:
        """Get list of loaded parameters."""
        with self._lock:
            return self._parameters.copy()

    def reload_parameters(self) -> None:
        """Reload parameters from registry."""
        with self._lock:
            self._parameters = self._registry.get_enabled_parameters()

    async def evaluate(self, context: ScoringContext) -> ScoringResult:
        """
        Evaluate scoring context with all registered parameters.

        Args:
            context: Scoring context to evaluate

        Returns:
            ScoringResult with final score and details

        Raises:
            ScoringNotInitializedError: If engine not initialized
            ScoringConfigurationError: If configuration is invalid
            ScoringComputationError: If computation fails
        """
        if not self._initialized:
            raise ScoringNotInitializedError("ScoringEngine not initialized")

        # Validate context
        self._validate_context(context)

        start_time = time.perf_counter()
        start_dt = datetime.now(UTC)

        # Run parameter evaluations concurrently
        contributions: list[ScoreContribution] = []
        penalties: list[Penalty] = []
        errors: list[str] = []

        # Use the running event loop (don't create a new one)
        loop = asyncio.get_running_loop()
        try:
            # Run all parameter evaluations concurrently
            tasks = []
            for param in self._parameters:
                task = loop.create_task(self._evaluate_parameter(param, context))
                tasks.append((param.parameter_id, task))

            # Wait for all with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*[t for _, t in tasks], return_exceptions=True),
                    timeout=self._config.execution_timeout
                )
            except TimeoutError:
                return self._create_timeout_result(start_dt, start_time)
            except Exception as e:
                import traceback
                print(f"DEBUG-SCORING-ENGINE: Inner exception: {e}")
                traceback.print_exc()
                return self._create_error_result(start_dt, time.perf_counter(), str(e))

            # Process results
            for (param_id, _), result in zip(tasks, results):
                print(f"DEBUG-SCORING-ENGINE: param={param_id}, result_type={type(result)}")
                if isinstance(result, Exception):
                    errors.append(str(result))
                    print(f"DEBUG-SCORING-ENGINE: param={param_id} FAILED: {result}")
                else:
                    score, param_penalties, explanation = result
                    param = next((p for p in self._parameters if p.parameter_id == param_id), None)
                    if param:
                        contributions.append(ScoreContribution(
                            parameter_id=param.parameter_id,
                            score=score,
                            max_score=param.max_score,
                            explanation=explanation,
                            weight=param.weight,
                        ))
                        penalties.extend(param_penalties)
                        print(f"DEBUG-SCORING-ENGINE: param={param_id} score={score}, max={param.max_score}, weight={param.weight}")
        except Exception as e:
            import traceback
            print(f"DEBUG-SCORING-ENGINE: Exception in evaluate: {e}")
            traceback.print_exc()
            return self._create_error_result(start_dt, time.perf_counter(), str(e))

        return self._aggregate_results(
            context=context,
            start_time=start_time,
            start_dt=start_dt,
            contributions=contributions,
            penalties=penalties,
            errors=errors,
        )

    def _validate_context(self, context: ScoringContext) -> None:
        """Validate scoring context."""
        if not context.market_event:
            raise ScoringConfigurationError("No market event in context")
        if not context.market_event.market_data:
            raise ScoringConfigurationError("No market data in event")
        if not context.market_event.strategy_data:
            raise ScoringConfigurationError("No strategy data in event")

    async def _evaluate_parameter(self, param: ScoringParameter, context: ScoringContext) -> tuple[float, list, str]:
        """Evaluate a single parameter."""
        try:
            return await param.evaluate(context)
        except Exception as e:
            raise ScoringComputationError(f"Parameter {param.parameter_id} evaluation failed: {e}") from e

    def _create_timeout_result(self, start_dt: datetime, start_time: float) -> ScoringResult:
        """Create result for timeout."""
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ScoringResult(
            qualified=False,
            final_score=0.0,
            max_score=100.0,
            contributions=tuple(),
            penalties=tuple(),
            scoring_id="scoring_engine",
            scoring_version="1.0",
            evaluation_id=None,
            evaluated_at=datetime.now(UTC),
            execution_time_ms=0.0,
            explanation="Evaluation timeout",
            metadata={"error": "timeout"},
        )

    def _create_error_result(self, start_dt: datetime, start_time: float, error: str) -> ScoringResult:
        """Create error result."""
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ScoringResult(
            qualified=False,
            final_score=0.0,
            max_score=100.0,
            contributions=tuple(),
            penalties=tuple(),
            scoring_id="scoring_engine",
            scoring_version="1.0",
            evaluation_id=None,
            evaluated_at=start_dt,
            execution_time_ms=execution_time_ms,
            explanation=f"Engine error: {error}",
            metadata={"error": error},
        )

    def _aggregate_results(
        self,
        context: ScoringContext,
        start_time: float,
        start_dt: datetime,
        contributions: list[ScoreContribution],
        penalties: list[Penalty],
        errors: list[str],
    ) -> ScoringResult:
        """Aggregate parameter results into final ScoringResult."""
        # Calculate scores
        total_score = sum(c.weighted_score for c in contributions)
        total_penalty = sum(p.points for p in penalties)

        final_score = max(0.0, total_score - total_penalty)
        max_score = 100.0

        # Qualification
        min_score = context.config.min_confidence_score
        qualified = final_score >= min_score

        # Build explanation
        explanation = self._build_explanation(
            contributions=contributions,
            penalties=penalties,
            qualified=qualified,
            final_score=final_score,
        )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ScoringResult(
            qualified=qualified,
            final_score=final_score,
            max_score=100.0,
            contributions=tuple(contributions),
            penalties=tuple(penalties),
            scoring_id="scoring_engine",
            scoring_version="1.0",
            evaluation_id=None,
            evaluated_at=start_dt,
            execution_time_ms=execution_time_ms,
            explanation=explanation,
            metadata={
                "parameter_count": len(self._parameters),
                "errors": errors,
            },
        )

    def _build_explanation(
        self,
        contributions: list[ScoreContribution],
        penalties: list[Penalty],
        qualified: bool,
        final_score: float,
    ) -> str:
        """Build human-readable explanation."""
        lines = []
        lines.append(f"Status: {'QUALIFIED' if qualified else 'REJECTED'}")
        lines.append(f"Final Score: {final_score:.1f}/100")

        for c in contributions:
            lines.append(f"  {c.parameter_id}: {c.score:.1f}/{c.max_score} ({c.explanation})")

        if penalties:
            for p in penalties:
                lines.append(f"  PENALTY: {p.reason} (-{p.points})")

        lines.append(f"Final: {'QUALIFIED' if qualified else 'REJECTED'}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "parameter_count": len(self._parameters),
                "config": {
                    "max_concurrent": self._config.max_concurrent_parameters,
                    "timeout": self._config.execution_timeout,
                }
            }

    def get_parameter(self, parameter_id: str) -> ScoringParameter | None:
        """Get parameter by ID."""
        with self._lock:
            for param in self._parameters:
                if param.parameter_id == parameter_id:
                    return param
        return None

    def reload_parameters(self) -> None:
        """Reload parameters from registry."""
        with self._lock:
            self._parameters = self._registry.get_enabled_parameters()

    def close(self) -> None:
        """Shutdown the engine."""
        with self._lock:
            for param in self._parameters:
                try:
                    asyncio.run(param.shutdown())
                except Exception:
                    pass
            self._parameters.clear()
            self._initialized = False


__all__ = [
    "ScoringEngine",
    "ScoringEngineConfig",
]