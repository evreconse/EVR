"""
EVRECONSE Core Module.

Shared core utilities and cross-cutting concerns.
"""

from .logging import (  # noqa: F401,F403
    ConsoleFormatter,
    JsonFormatter,
    LoggerProtocol,
    LoggingConfig,
    LogLevel,
    async_log_context,
    create_console_handler,
    create_file_handler,
    get_logger,
    get_logging_manager,
    init_logging,
    log_context,
    log_timing,
    shutdown_logging,
)

__all__ = [
    "ConsoleFormatter",
    "JsonFormatter",
    "LogLevel",
    "LoggerProtocol",
    "LoggingConfig",
    "async_log_context",
    "create_console_handler",
    "create_file_handler",
    "get_logger",
    "get_logging_manager",
    "init_logging",
    "log_context",
    "log_timing",
    "shutdown_logging",
]