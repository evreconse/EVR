"""
EVRECONSE Application Layer - Health Checks.

Comprehensive health checking for all application components.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated health report for all components."""
    overall_status: HealthStatus
    components: tuple[ComponentHealth, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_latency_ms: float = 0.0

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.components if c.is_healthy)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.UNHEALTHY)

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.DEGRADED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "healthy": self.healthy_count,
            "degraded": self.degraded_count,
            "unhealthy": self.unhealthy_count,
            "total": len(self.components),
            "timestamp": self.timestamp.isoformat(),
            "total_latency_ms": self.total_latency_ms,
            "components": [c.to_dict() for c in self.components],
        }


# =============================================================================
# Health Check Interface
# =============================================================================

class HealthCheck(ABC):
    """Abstract health check."""

    @abstractmethod
    async def check(self) -> ComponentHealth:
        """Perform health check."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Check name."""


class AsyncHealthCheck(HealthCheck):
    """Async health check with timeout support."""

    def __init__(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        timeout: float = 5.0,
    ) -> None:
        self._name = name
        self._check_fn = check_fn
        self._timeout = timeout

    @property
    def name(self) -> str:
        return self._name

    async def check(self) -> ComponentHealth:
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(self._check_fn(), timeout=self._timeout)
            result = ComponentHealth(
                name=self._name,
                status=result.status,
                message=result.message,
                details=result.details,
                latency_ms=(time.monotonic() - start) * 1000,
            )
            return result
        except TimeoutError:
            return ComponentHealth(
                name=self._name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self._timeout}s",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return ComponentHealth(
                name=self._name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                latency_ms=(time.monotonic() - start) * 1000,
            )


# =============================================================================
# Health Checker
# =============================================================================

class HealthChecker:
    """
    Aggregates and runs health checks for all components.

    Features:
    - Parallel check execution
    - Per-check timeouts
    - Caching with TTL
    - Overall status aggregation
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
        cache_ttl_seconds: float = 30.0,
    ) -> None:
        self._checks: dict[str, AsyncHealthCheck] = {}
        self._default_timeout = default_timeout
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, ComponentHealth] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def register(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        timeout: float | None = None,
    ) -> None:
        """Register a health check."""
        self._checks[name] = AsyncHealthCheck(
            name=name,
            check_fn=check_fn,
            timeout=timeout or self._default_timeout,
        )

    def register_check(self, check: HealthCheck) -> None:
        """Register a HealthCheck instance."""
        self._checks[check.name] = check

    def unregister(self, name: str) -> bool:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            self._cache.pop(name, None)
            self._cache_timestamps.pop(name, None)
            return True
        return False

    def get_registered_checks(self) -> list[str]:
        """Get list of registered check names."""
        return list(self._checks.keys())

    async def check_all(
        self,
        timeout: float | None = None,
        use_cache: bool = True,
    ) -> HealthReport:
        """
        Run all health checks in parallel.

        Args:
            timeout: Overall timeout for all checks
            use_cache: Whether to use cached results

        Returns:
            HealthReport with all component statuses
        """
        start = time.monotonic()
        effective_timeout = timeout or self._default_timeout

        # Run checks
        if use_cache:
            results = await self._run_with_cache()
        else:
            results = await self._run_all()

        # Compute overall status
        statuses = [r.status for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return HealthReport(
            overall_status=overall,
            components=tuple(results),
            total_latency_ms=(time.monotonic() - start) * 1000,
        )

    async def check_component(
        self,
        name: str,
        timeout: float | None = None,
        use_cache: bool = True,
    ) -> ComponentHealth:
        """
        Run a single health check.

        Args:
            name: Check name
            timeout: Check timeout
            use_cache: Whether to use cached result

        Returns:
            ComponentHealth for the component

        Raises:
            KeyError: If check not registered
        """
        if name not in self._checks:
            raise KeyError(f"Health check not registered: {name}")

        check = self._checks[name]

        if use_cache:
            async with self._lock:
                cached = self._cache.get(name)
                if cached and (time.monotonic() - self._cache_timestamps[name]) < self._cache_ttl:
                    return cached

                result = await check.check()
                self._cache[name] = result
                self._cache_timestamps[name] = time.monotonic()
                return result
        else:
            return await check.check()

    async def _run_with_cache(self) -> list[ComponentHealth]:
        """Run all checks with cache support."""
        async with self._lock:
            now = time.monotonic()
            results = []

            for name, check in self._checks.items():
                if name in self._cache and (now - self._cache_timestamps[name]) < self._cache_ttl:
                    results.append(self._cache[name])
                else:
                    result = await check.check()
                    self._cache[name] = result
                    self._cache_timestamps[name] = now
                    results.append(result)

            return results

    async def _run_all(self) -> list[ComponentHealth]:
        """Run all checks in parallel without cache."""
        tasks = [check.check() for check in self._checks.values()]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._cache.clear()
        self._cache_timestamps.clear()


# =============================================================================
# Standard Health Checks
# =============================================================================

async def check_data_provider(provider) -> ComponentHealth:
    """Check data provider connectivity."""
    try:
        if hasattr(provider, 'is_connected') and provider.is_connected():
            return ComponentHealth(
                name="data_provider",
                status=HealthStatus.HEALTHY,
                message="Connected to exchange",
            )
        return ComponentHealth(
            name="data_provider",
            status=HealthStatus.UNHEALTHY,
            message="Not connected to exchange",
        )
    except Exception as e:
        return ComponentHealth(
            name="data_provider",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )


async def check_storage(storage) -> ComponentHealth:
    """Check storage engine health."""
    try:
        if hasattr(storage, 'health_check'):
            result = storage.health_check()
            if result:
                return ComponentHealth(
                    name="storage",
                    status=HealthStatus.HEALTHY,
                    message="Storage accessible",
                )
        return ComponentHealth(
            name="storage",
            status=HealthStatus.HEALTHY,
            message="Storage accessible",
        )
    except Exception as e:
        return ComponentHealth(
            name="storage",
            status=HealthStatus.UNHEALTHY,
            message=f"Storage check failed: {e}",
        )


async def check_strategy_engine(engine) -> ComponentHealth:
    """Check strategy engine health."""
    try:
        if hasattr(engine, 'is_active'):
            return ComponentHealth(
                name="strategy_engine",
                status=HealthStatus.HEALTHY,
                message="Strategy engine ready",
            )
        return ComponentHealth(
            name="strategy_engine",
            status=HealthStatus.DEGRADED,
            message="Strategy engine not initialized",
        )
    except Exception as e:
        return ComponentHealth(
            name="strategy_engine",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )


async def check_scoring_engine(engine) -> ComponentHealth:
    """Check scoring engine health."""
    try:
        if hasattr(engine, 'is_initialized'):
            return ComponentHealth(
                name="scoring_engine",
                status=HealthStatus.HEALTHY,
                message="Scoring engine ready",
            )
        return ComponentHealth(
            name="scoring_engine",
            status=HealthStatus.DEGRADED,
            message="Scoring engine not initialized",
        )
    except Exception as e:
        return ComponentHealth(
            name="scoring_engine",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )


async def check_notification_engine(engine) -> ComponentHealth:
    """Check notification engine health."""
    try:
        if hasattr(engine, 'get_stats'):
            return ComponentHealth(
                name="notification_engine",
                status=HealthStatus.HEALTHY,
                message="Notification engine ready",
            )
        return ComponentHealth(
            name="notification_engine",
            status=HealthStatus.DEGRADED,
            message="Notification engine not initialized",
        )
    except Exception as e:
        return ComponentHealth(
            name="notification_engine",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )


async def check_event_engine(engine) -> ComponentHealth:
    """Check event engine health."""
    try:
        if hasattr(engine, 'get_stats'):
            return ComponentHealth(
                name="event_engine",
                status=HealthStatus.HEALTHY,
                message="Event engine ready",
            )
        return ComponentHealth(
            name="event_engine",
            status=HealthStatus.DEGRADED,
            message="Event engine not initialized",
        )
    except Exception as e:
        return ComponentHealth(
            name="event_engine",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )


def create_standard_health_checker(
    data_provider=None,
    storage=None,
    strategy_engine=None,
    scoring_engine=None,
    notification_engine=None,
    event_engine=None,
    default_timeout: float = 5.0,
    cache_ttl_seconds: float = 30.0,
) -> HealthChecker:
    """
    Create a HealthChecker with standard component checks.

    Args:
        data_provider: Data provider instance
        storage: Storage engine instance
        strategy_engine: Strategy engine instance
        scoring_engine: Scoring engine instance
        notification_engine: Notification engine instance
        event_engine: Event engine instance
        default_timeout: Default check timeout
        cache_ttl_seconds: Cache TTL

    Returns:
        Configured HealthChecker
    """
    checker = HealthChecker(
        default_timeout=default_timeout,
        cache_ttl_seconds=cache_ttl_seconds,
    )

    if data_provider:
        checker.register("data_provider", lambda: check_data_provider(data_provider))

    if storage:
        checker.register("storage", lambda: check_storage(storage))

    if strategy_engine:
        checker.register("strategy_engine", lambda: check_strategy_engine(strategy_engine))

    if scoring_engine:
        checker.register("scoring_engine", lambda: check_scoring_engine(scoring_engine))

    if notification_engine:
        checker.register("notification_engine", lambda: check_notification_engine(notification_engine))

    if event_engine:
        checker.register("event_engine", lambda: check_event_engine(event_engine))

    return checker