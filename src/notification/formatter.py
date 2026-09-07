"""
EVRECONSE Notification - Formatter.

Message formatting for different channels and formats.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .enums import MessageFormat, NotificationChannel
from .delivery_result import DeliveryResult


class Formatter(ABC):
    """Abstract base class for message formatters."""

    @abstractmethod
    def format(self, template: str, context: dict[str, Any]) -> str:
        """
        Format a template with the given context.
        
        Args:
            template: Template string with placeholders
            context: Dictionary of values to substitute
            
        Returns:
            Formatted string
        """
        ...

    @abstractmethod
    def format_error(self, error: Exception, context: dict[str, Any]) -> str:
        """
        Format an error for delivery.
        
        Args:
            error: The exception to format
            context: Additional context
            
        Returns:
            Formatted error message
        """
        ...


@dataclass(frozen=True, slots=True)
class FormatOptions:
    """Options for message formatting."""
    
    format: str = "markdown_v2"  # MessageFormat value
    escape_html: bool = True
    escape_markdown: bool = True
    max_length: int = 4096
    truncate: bool = True
    prefix: str = ""
    suffix: str = ""


class BaseFormatter(ABC):
    """Base formatter with common utilities."""

    def __init__(self, options: Any = None) -> None:
        self._options = options or {}

    def format(self, template: str, context: dict[str, Any]) -> str:
        """Format template with context."""
        return self._render(template, context)

    @abstractmethod
    def _render(self, template: str, context: dict[str, Any]) -> str:
        """Internal render method."""
        ...

    def format_error(self, error: Exception, context: dict[str, Any]) -> str:
        """Format error for delivery."""
        return f"❌ **Error**: {type(error).__name__}: {str(error)}"

    def escape_markdown(self, text: str) -> str:
        """Escape special MarkdownV2 characters."""
        # MarkdownV2 special characters
        special_chars = r'_*[]()~`>#+-=|{}.!'
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        text = text.replace('&', '&')
        text = text.replace('<', '<')
        text = text.replace('>', '>')
        text = text.replace('"', '"')
        text = text.replace("'", "'")
        return text

    def truncate(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix


class MarkdownV2Formatter:
    """Telegram MarkdownV2 formatter."""

    def __init__(self, options: Any = None) -> None:
        pass

    def format(self, template: str, context: dict[str, Any]) -> str:
        """Format template with MarkdownV2 escaping."""
        result = self._render(template, context)
        return self._escape_markdown_v2(result)

    def _render(self, template: str, context: dict[str, Any]) -> str:
        """Simple template rendering."""
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def _escape_markdown_v2(self, text: str) -> str:
        """Escape special MarkdownV2 characters."""
        # Characters that must be escaped in MarkdownV2
        special_chars = r'_*[]()~`>#+-=|{}.!'
        result = []
        for char in text:
            if char in special_chars:
                result.append('\\')
            result.append(char)
        return ''.join(result)

    def format_error(self, error: Exception, context: dict[str, Any]) -> str:
        """Format error for MarkdownV2."""
        error_type = type(error).__name__
        message = str(error)
        escaped_type = self._escape_markdown_v2(error_type)
        escaped_message = self._escape_markdown_v2(message)
        return f"❌ **Error**: *{escaped_type}*: {escaped_message}"


class MarkdownFormatter(MarkdownV2Formatter):
    """Alias for MarkdownV2Formatter."""
    pass


class HTMLFormatter:
    """HTML formatter for Telegram."""

    def format(self, template: str, context: dict[str, Any]) -> str:
        """Format template with HTML escaping."""
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, self._escape_html(str(value)))
        return result

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace('&', '&')
            .replace('<', '<')
            .replace('>', '>')
            .replace('"', '"')
            .replace("'", "'")
        )

    def format_error(self, error: Exception, context: dict[str, Any]) -> str:
        """Format error for HTML."""
        error_type = type(error).__name__
        message = str(error)
        return f"❌ <b>Error</b>: <code>{error_type}</code>: {message}"


class PlainTextFormatter:
    """Plain text formatter (no formatting)."""

    def format(self, template: str, context: dict[str, Any]) -> str:
        """Format template without any formatting."""
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def format_error(self, error: Exception, context: dict[str, Any]) -> str:
        """Format error as plain text."""
        return f"Error: {type(error).__name__}: {str(error)}"


# Formatter factory
class FormatterFactory:
    """Factory for creating formatters."""

    _formatters = {
        "markdown": MarkdownV2Formatter,
        "markdown_v2": MarkdownV2Formatter,
        "markdown_v1": MarkdownFormatter,
        "html": HTMLFormatter,
        "plain": PlainTextFormatter,
    }

    @classmethod
    def create(cls, format_type: str, options: Any = None) -> Any:
        """Create formatter by format type."""
        formatter_class = cls._formatters.get(format_type.lower())
        if not formatter_class:
            raise ValueError(f"Unknown format type: {format_type}")
        return formatter_class(options)

    @classmethod
    def register(cls, format_type: str, formatter_class: type) -> None:
        """Register a custom formatter."""
        cls._formatters[format_type.lower()] = formatter_class