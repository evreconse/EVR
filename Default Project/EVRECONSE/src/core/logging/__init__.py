"""
EVRECONSE Logging Layer - Structured Logging.

Production-ready structured logging with:
- JSON and console formatters
- File rotation
- UTC timestamps
- Correlation ID / Event ID / Signal ID support
- Async-safe, thread-safe
- Configurable log levels
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import logging.handlers
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Context Variables for Correlation IDs
# =============================================================================

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)
_event_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("event_id", default=None)
_signal_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("signal_id", default=None)
_strategy_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("strategy_id", default=None)
_exchange: contextvars.ContextVar[str | None] = contextvars.ContextVar("exchange", default=None)
_symbol: contextvars.ContextVar[str | None] = contextvars.ContextVar("symbol", default=None)
_timeframe: contextvars.ContextVar[str | None] = contextvars.ContextVar("timeframe", default=None)


def set_correlation_id(correlation_id: str | None) -> None:
    """Set correlation ID for current context."""
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get correlation ID for current context."""
    return _correlation_id.get()


def set_event_id(event_id: str | None) -> None:
    """Set event ID for current context."""
    _event_id.set(event_id)


def get_event_id() -> str | None:
    """Get event ID for current context."""
    return _event_id.get()


def set_signal_id(signal_id: str | None) -> None:
    """Set signal ID for current context."""
    _signal_id.set(signal_id)


def get_signal_id() -> str | None:
    """Get signal ID for current context."""
    return _signal_id.get()


def set_strategy_id(strategy_id: str | None) -> None:
    """Set strategy ID for current context."""
    _strategy_id.set(strategy_id)


def get_strategy_id() -> str | None:
    """Get strategy ID for current context."""
    return _strategy_id.get()


def set_exchange(exchange: str | None) -> None:
    """Set exchange for current context."""
    _exchange.set(exchange)


def get_exchange() -> str | None:
    """Get exchange for current context."""
    return _exchange.get()


def set_symbol(symbol: str | None) -> None:
    """Set symbol for current context."""
    _symbol.set(symbol)


def get_symbol() -> str | None:
    """Get symbol for current context."""
    return _symbol.get()


def set_timeframe(timeframe: str | None) -> None:
    """Set timeframe for current context."""
    _timeframe.set(timeframe)


def get_timeframe() -> str | None:
    """Get timeframe for current context."""
    return _timeframe.get()


def get_all_context() -> dict[str, str | None]:
    """Get all context variables as dictionary."""
    return {
        "correlation_id": get_correlation_id(),
        "event_id": get_event_id(),
        "signal_id": get_signal_id(),
        "strategy_id": get_strategy_id(),
        "exchange": get_exchange(),
        "symbol": get_symbol(),
        "timeframe": get_timeframe(),
    }


def clear_context() -> None:
    """Clear all context variables."""
    _correlation_id.set(None)
    _event_id.set(None)
    _signal_id.set(None)
    _strategy_id.set(None)
    _exchange.set(None)
    _symbol.set(None)
    _timeframe.set(None)


# =============================================================================
# Log Formatters
# =============================================================================

class JsonFormatter(logging.Formatter):
    """
    JSON log formatter with structured fields.

    Outputs structured JSON logs with:
    - timestamp (UTC ISO 8601)
    - level
    - logger name
    - message
    - correlation_id, event_id, signal_id, strategy_id
    - exchange, symbol, timeframe
    - exception info (if present)
    - extra fields
    """

    def __init__(self, include_extra: bool = True) -> None:
        super().__init__()
        self._include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context variables
        context = get_all_context()
        for key, value in context.items():
            if value is not None:
                log_entry[key] = value

        # Add source location
        log_entry["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add process/thread info
        log_entry["process"] = record.process
        log_entry["thread"] = record.thread

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Add extra fields from record
        if self._include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info", "getMessage"
                }:
                    extra_fields[key] = value

            if extra_fields:
                log_entry["extra"] = extra_fields

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with colors.

    Includes context information in a compact format.
    """

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self._use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S.%f")[:-3]

        # Level with color
        level = record.levelname
        if self._use_colors:
            color = self.COLORS.get(level, "")
            level = f"{color}{level}{self.RESET}"

        # Logger name (shortened)
        logger_name = record.name
        logger_name = logger_name.removeprefix("src.")

        # Context prefix
        context_parts = []
        if get_correlation_id():
            context_parts.append(f"cid={get_correlation_id()[:8]}")
        if get_event_id():
            context_parts.append(f"eid={get_event_id()[:8]}")
        if get_signal_id():
            context_parts.append(f"sid={get_signal_id()[:8]}")
        if get_strategy_id():
            context_parts.append(f"strat={get_strategy_id()}")
        if get_exchange():
            context_parts.append(f"ex={get_exchange()}")
        if get_symbol():
            context_parts.append(f"sym={get_symbol()}")

        context_str = f" [{' '.join(context_parts)}]" if context_parts else ""

        # Message
        message = record.getMessage()

        # Format
        return f"{timestamp} | {level:>10} | {logger_name}{context_str} | {message}"


# =============================================================================
# Log Handlers
# =============================================================================

def create_file_handler(
    log_path: str | Path,
    level: int = logging.DEBUG,
    max_bytes: int = 10_000_000,  # 10 MB
    backup_count: int = 10,
    formatter: logging.Formatter | None = None,
) -> logging.handlers.RotatingFileHandler:
    """
    Create a rotating file handler.

    Args:
        log_path: Path to log file
        level: Log level
        max_bytes: Max size before rotation
        backup_count: Number of backup files to keep
        formatter: Optional custom formatter

    Returns:
        Configured RotatingFileHandler
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter or JsonFormatter())
    return handler


def create_console_handler(
    level: int = logging.INFO,
    formatter: logging.Formatter | None = None,
    use_colors: bool = True,
) -> logging.StreamHandler:
    """
    Create a console handler.

    Args:
        level: Log level
        formatter: Optional custom formatter
        use_colors: Whether to use ANSI colors

    Returns:
        Configured StreamHandler
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter or ConsoleFormatter(use_colors=use_colors))
    return handler


# =============================================================================
# Logger Configuration
# =============================================================================

class LogLevel(Enum):
    """Log levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @classmethod
    def from_string(cls, value: str) -> LogLevel:
        """Parse log level from string."""
        value = value.upper()
        for member in cls:
            if member.name == value:
                return member
        return cls.INFO


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    log_path: Path | None = None
    console_enabled: bool = True
    file_enabled: bool = True
    json_format: bool = True
    max_bytes: int = 10_000_000
    backup_count: int = 10
    use_colors: bool = True
    third_party_level: int = logging.WARNING


class LoggingManager:
    """
    Centralized logging management.

    Handles:
    - Logger configuration
    - Handler management
    - Context propagation
    - Dynamic level changes
    """

    def __init__(self, config: LoggingConfig | None = None) -> None:
        self._config = config or LoggingConfig()
        self._initialized = False
        self._handlers: list[logging.Handler] = []
        self._lock = threading.RLock()

    def initialize(self) -> None:
        """Initialize logging system."""
        with self._lock:
            if self._initialized:
                return

            root_logger = logging.getLogger()
            root_logger.setLevel(self._config.level.value)

            # Clear existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()

            # Console handler
            if self._config.console_enabled:
                console_handler = create_console_handler(
                    level=self._config.level.value,
                    formatter=ConsoleFormatter(use_colors=self._config.use_colors),
                    use_colors=self._config.use_colors,
                )
                root_logger.addHandler(console_handler)
                self._handlers.append(console_handler)

            # File handler
            if self._config.file_enabled and self._config.log_path:
                file_handler = create_file_handler(
                    log_path=self._config.log_path,
                    level=self._config.level.value,
                    max_bytes=self._config.max_bytes,
                    backup_count=self._config.backup_count,
                    formatter=JsonFormatter() if self._config.json_format else ConsoleFormatter(use_colors=False),
                )
                root_logger.addHandler(file_handler)
                self._handlers.append(file_handler)

            # Suppress third-party loggers
            for logger_name in [
                "urllib3", "aiohttp", "websockets", "asyncio",
                "httpx", "httpcore", "ccxt", "ccxt.base",
            ]:
                logging.getLogger(logger_name).setLevel(self._config.third_party_level)

            self._initialized = True

    def shutdown(self) -> None:
        """Shutdown logging system."""
        with self._lock:
            root_logger = logging.getLogger()
            for handler in self._handlers:
                root_logger.removeHandler(handler)
                handler.close()
            self._handlers.clear()
            self._initialized = False

    def set_level(self, level: LogLevel | str) -> None:
        """Set log level dynamically."""
        if isinstance(level, str):
            level = LogLevel.from_string(level)

        with self._lock:
            root_logger = logging.getLogger()
            root_logger.setLevel(level.value)
            for handler in self._handlers:
                handler.setLevel(level.value)
            self._config = LoggingConfig(
                level=level,
                log_path=self._config.log_path,
                console_enabled=self._config.console_enabled,
                file_enabled=self._config.file_enabled,
                json_format=self._config.json_format,
                max_bytes=self._config.max_bytes,
                backup_count=self._config.backup_count,
                use_colors=self._config.use_colors,
                third_party_level=self._config.third_party_level,
            )

    def get_logger(self, name: str) -> logging.Logger:
        """Get logger instance."""
        return logging.getLogger(name)

    @property
    def config(self) -> LoggingConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# =============================================================================
# Global Logging Manager
# =============================================================================

_logging_manager: LoggingManager | None = None
_logging_lock = threading.Lock()


def get_logging_manager() -> LoggingManager:
    """Get global logging manager instance."""
    global _logging_manager
    with _logging_lock:
        if _logging_manager is None:
            _logging_manager = LoggingManager()
        return _logging_manager


def init_logging(config: LoggingConfig | None = None) -> LoggingManager:
    """Initialize global logging."""
    global _logging_manager
    with _logging_lock:
        if _logging_manager is not None:
            _logging_manager.shutdown()
        _logging_manager = LoggingManager(config)
        _logging_manager.initialize()
        return _logging_manager


def shutdown_logging() -> None:
    """Shutdown global logging."""
    global _logging_manager
    with _logging_lock:
        if _logging_manager is not None:
            _logging_manager.shutdown()
            _logging_manager = None


def get_logger(name: str) -> logging.Logger:
    """Get logger instance (alias for logging.getLogger)."""
    return logging.getLogger(name)


# =============================================================================
# Context Managers
# =============================================================================

from contextlib import contextmanager


@contextmanager
def log_context(
    correlation_id: str | None = None,
    event_id: str | None = None,
    signal_id: str | None = None,
    strategy_id: str | None = None,
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
):
    """
    Context manager for setting log context.

    All log messages within the context will include the provided IDs.
    """
    old_context = get_all_context()

    try:
        if correlation_id is not None:
            set_correlation_id(correlation_id)
        if event_id is not None:
            set_event_id(event_id)
        if signal_id is not None:
            set_signal_id(signal_id)
        if strategy_id is not None:
            set_strategy_id(strategy_id)
        if exchange is not None:
            set_exchange(exchange)
        if symbol is not None:
            set_symbol(symbol)
        if timeframe is not None:
            set_timeframe(timeframe)

        yield
    finally:
        # Restore old context
        for key, value in old_context.items():
            if key == "correlation_id":
                _correlation_id.set(value)
            elif key == "event_id":
                _event_id.set(value)
            elif key == "signal_id":
                _signal_id.set(value)
            elif key == "strategy_id":
                _strategy_id.set(value)
            elif key == "exchange":
                _exchange.set(value)
            elif key == "symbol":
                _symbol.set(value)
            elif key == "timeframe":
                _timeframe.set(value)


@contextmanager
def log_timing(logger: logging.Logger, operation: str, level: int = logging.INFO):
    """
    Context manager for timing operations.

    Logs start and end with duration.
    """
    start = time.monotonic()
    logger.log(level, f"Starting: {operation}")
    try:
        yield
    finally:
        duration = time.monotonic() - start
        logger.log(level, f"Completed: {operation} (duration: {duration:.3f}s)")


# =============================================================================
# Async-safe Logging Helpers
# =============================================================================

async def async_log_context(
    correlation_id: str | None = None,
    event_id: str | None = None,
    signal_id: str | None = None,
    strategy_id: str | None = None,
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
):
    """
    Async context manager for log context.

    Context variables work correctly with asyncio.
    """
    old_context = get_all_context()

    try:
        if correlation_id is not None:
            set_correlation_id(correlation_id)
        if event_id is not None:
            set_event_id(event_id)
        if signal_id is not None:
            set_signal_id(signal_id)
        if strategy_id is not None:
            set_strategy_id(strategy_id)
        if exchange is not None:
            set_exchange(exchange)
        if symbol is not None:
            set_symbol(symbol)
        if timeframe is not None:
            set_timeframe(timeframe)

        yield
    finally:
        for key, value in old_context.items():
            if key == "correlation_id":
                _correlation_id.set(value)
            elif key == "event_id":
                _event_id.set(value)
            elif key == "signal_id":
                _signal_id.set(value)
            elif key == "strategy_id":
                _strategy_id.set(value)
            elif key == "exchange":
                _exchange.set(value)
            elif key == "symbol":
                _symbol.set(value)
            elif key == "timeframe":
                _timeframe.set(value)


# =============================================================================
# Protocol for logging
# =============================================================================

from typing import Protocol


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None: ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Context
    "set_correlation_id", "get_correlation_id",
    "set_event_id", "get_event_id",
    "set_signal_id", "get_signal_id",
    "set_strategy_id", "get_strategy_id",
    "set_exchange", "get_exchange",
    "set_symbol", "get_symbol",
    "set_timeframe", "get_timeframe",
    "get_all_context", "clear_context",
    "log_context", "async_log_context",

    # Formatters
    "JsonFormatter", "ConsoleFormatter",

    # Handlers
    "create_file_handler", "create_console_handler",

    # Configuration
    "LoggingConfig", "LogLevel", "LoggingManager",
    "init_logging", "shutdown_logging", "get_logging_manager",

    # Logger
    "get_logger", "LoggerProtocol",

    # Timing
    "log_timing",
]