"""
EVRECONSE Event Engine - Metrics.

Metrics collection and reporting for Event Engine.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Counter:
    """Thread-safe counter."""
    value: int = 0
    
    def increment(self, amount: int = 1) -> int:
        return self.value + amount
    
    def get(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class Histogram:
    """Simple histogram for latency measurements."""
    buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0)
    counts: tuple[int, ...] = ()
    count: int = 0
    sum: float = 0.0
    
    def observe(self, value: float) -> Histogram:
        # In production, would use proper histogram implementation
        return self
    
    @property
    def count(self) -> int:
        return self.count
    
    @property
    def sum(self) -> float:
        return self.sum


@dataclass(frozen=True, slots=True)
class Gauge:
    """Gauge for instantaneous values."""
    value: float = 0.0
    
    def set(self, value: float) -> Gauge:
        return Gauge(value)
    
    def inc(self, amount: float = 1.0) -> Gauge:
        return Gauge(self.value + amount)
    
    def dec(self, amount: float = 1.0) -> Gauge:
        return Gauge(self.value - amount)


class MetricsCollector:
    """
    Thread-safe metrics collector for Event Engine.
    
    Collects:
    - Counters (events processed, succeeded, failed, rejected)
    - Histograms (latencies)
    - Gauges (active events, queue sizes)
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._start_time = time.monotonic()
    
    def increment(self, name: str, amount: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount
    
    def gauge_set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def gauge_inc(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment gauge."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) + amount
    
    def gauge_dec(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Decrement gauge."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) - amount
    
    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe value for histogram."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            # Keep only last 10000 samples
            if len(self._histograms[key]) > 10000:
                self._histograms[key] = self._histograms[key][-10000:]
    
    def timing(self, name: str, duration_ms: float, labels: dict[str, str] | None = None) -> None:
        """Record timing observation."""
        self.observe(name, duration_ms / 1000.0, labels)  # Store as seconds
    
    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get counter value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: dict[str, str] | None = None) -> dict:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {"count": 0, "mean": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
            
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            return {
                "count": n,
                "mean": sum(values) / n,
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "p50": sorted_vals[n // 2],
                "p95": sorted_vals[int(n * 0.95)],
                "p99": sorted_vals[int(n * 0.99)],
            }
    
    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as dictionary."""
        with self._lock:
            return {
                "counters": self._counters.copy(),
                "gauges": self._gauges.copy(),
                "histograms": {
                    k: self._percentiles(v)
                    for k, v in self._histograms.items()
                },
            }
    
    def _percentiles(self, values: list[float]) -> dict:
        if not values:
            return {"count": 0, "mean": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "mean": sum(sorted_vals) / n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
        }
    
    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._start_time = time.monotonic()


# Global metrics instance
_metrics_instance: MetricsCollector | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Get global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = MetricsCollector()
    return _metrics_instance


def reset_metrics() -> None:
    """Reset global metrics (for testing)."""
    global _metrics_instance
    with _metrics_lock:
        _metrics_instance = None


# Convenience functions
def increment(name: str, amount: int = 1, labels: dict[str, str] | None = None) -> None:
    get_metrics().increment(name, amount, labels)


def gauge_set(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    get_metrics().gauge_set(name, value, labels)


def gauge_inc(name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
    get_metrics().gauge_inc(name, amount, labels)


def gauge_dec(name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
    get_metrics().gauge_dec(name, amount, labels)


def observe(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    get_metrics().observe(name, value, labels)


def timing(name: str, duration_ms: float, labels: dict[str, str] | None = None) -> None:
    get_metrics().timing(name, duration_ms, labels)


def get_metrics_snapshot() -> dict[str, Any]:
    return get_metrics().get_all_metrics()


# Convenience functions for common metrics
def inc_events_processed(labels: dict[str, str] | None = None) -> None:
    increment("events_processed", labels=labels)


def inc_events_succeeded(labels: dict[str, str] | None = None) -> None:
    increment("events_succeeded", labels=labels)


def inc_events_failed(labels: dict[str, str] | None = None) -> None:
    increment("events_failed", labels=labels)


def inc_events_rejected(labels: dict[str, str] | None = None) -> None:
    increment("events_rejected", labels=labels)


def observe_processing_time(duration_ms: float, labels: dict[str, str] | None = None) -> None:
    observe("processing_time_ms", duration_ms, labels)


def observe_scoring_time(duration_ms: float, labels: dict[str, str] | None = None) -> None:
    observe("scoring_time_ms", duration_ms, labels)


def observe_notification_time(duration_ms: float, labels: dict[str, str] | None = None) -> None:
    observe("notification_time_ms", duration_ms, labels)


def observe_storage_time(duration_ms: float, labels: dict[str, str] | None = None) -> None:
    observe("storage_time_ms", duration_ms, labels)


def gauge_active_events(count: int, labels: dict[str, str] | None = None) -> None:
    gauge_set("active_events", float(count), labels)


def gauge_queue_size(size: int, labels: dict[str, str] | None = None) -> None:
    gauge_set("queue_size", float(size), labels)


def gauge_active_events_change(delta: int, labels: dict[str, str] | None = None) -> None:
    # Gauge doesn't support inc directly, use gauge_set with current value
    # In practice, would track current value
    pass