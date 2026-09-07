"""
EVRECONSE Notification - Notification Service Interface.

Abstract interface for notification services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .delivery_result import DeliveryResult


class Notification(ABC):
    """Abstract base class for notifications."""
    
    @property
    @abstractmethod
    def channel(self) -> str:
        """Notification channel identifier."""
        ...
    
    @property
    @abstractmethod
    def recipient(self) -> str:
        """Notification recipient identifier."""
        ...
    
    @property
    @abstractmethod
    def subject(self) -> str | None:
        """Notification subject/title."""
        ...
    
    @property
    @abstractmethod
    def body(self) -> str:
        """Notification body content."""
        ...
    
    @property
    @abstractmethod
    def format(self) -> str:
        """Message format (markdown, html, plain)."""
        ...
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Notification priority (higher = more urgent)."""
        ...


class NotificationService(ABC):
    """
    Abstract interface for notification services.
    
    All notification delivery services (Telegram, Email, Slack, etc.)
    must implement this interface.
    """
    
    @abstractmethod
    async def send(self, notification) -> DeliveryResult:
        """
        Send a single notification.
        
        Args:
            notification: Notification object to send
            
        Returns:
            DeliveryResult with delivery status and metadata
            
        Raises:
            ConnectionError: If connection to channel fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
            DeliveryError: If delivery fails
        """
        ...
    
    @abstractmethod
    async def send_batch(self, notifications: list) -> list:
        """
        Send multiple notifications.
        
        Args:
            notifications: List of notification objects
            
        Returns:
            List of DeliveryResult objects
        """
        ...
    
    @abstractmethod
    async def validate(self, notification) -> bool:
        """
        Validate notification before sending.
        
        Args:
            notification: Notification to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check channel connectivity and health.
        
        Returns:
            True if channel is healthy
        """
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        ...
    
    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Get channel name."""
        ...
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if service is connected."""
        ...


class NotificationEngine:
    """
    Notification orchestration engine.
    
    Manages multiple notification services and handles
    routing, queueing, retry logic, and delivery tracking.
    """
    
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._queue: Any = None
        self._running = False
        self._lock = __import__("threading").RLock()
    
    def register_service(self, service: NotificationService) -> None:
        """Register a notification service."""
        with self._lock:
            self._services[service.channel_name] = service
    
    def unregister_service(self, channel: str) -> None:
        """Unregister a notification service."""
        with self._lock:
            self._services.pop(channel, None)
    
    def get_service(self, channel: str):
        """Get service by channel name."""
        with self._lock:
            return self._services.get(channel)
    
    def list_services(self) -> list[str]:
        """List all registered service channels."""
        with self._lock:
            return list(self._services.keys())
    
    async def send(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        format: str = "markdown",
        priority: int = 0,
    ) -> DeliveryResult:
        """
        Send notification via specified channel.
        
        Args:
            channel: Channel name (telegram, email, slack, etc.)
            recipient: Recipient identifier
            subject: Message subject
            body: Message body
            format: Message format (markdown, html, plain)
            priority: Message priority
            
        Returns:
            DeliveryResult
        """
        service = self.get_service(channel)
        if not service:
            raise ValueError(f"No service registered for channel: {channel}")
        
        # Use a simple notification object that matches the interface
        class SimpleNotification:
            def __init__(self):
                self.channel = channel
                self.recipient = recipient
                self.subject = subject
                self.body = body
                self.format = format
                self.priority = priority
            
            @property
            def channel_name(self):
                return self.channel
        
        notification = SimpleNotification()
        
        return await service.send(notification)
    
    async def send_batch(
        self,
        channel: str,
        notifications: list,
    ) -> list:
        """Send batch of notifications via channel."""
        service = self.get_service(channel)
        if not service:
            raise ValueError(f"No service registered for channel: {channel}")
        return await service.send_batch(notifications)
    
    async def health_check(self, channel: str | None = None) -> dict[str, bool]:
        """Check health of services."""
        with self._lock:
            channels = [channel] if channel else list(self._services.keys())
            results = {}
            for ch in channels:
                service = self._services.get(ch)
                if service:
                    try:
                        results[ch] = await service.health_check()
                    except Exception:
                        results[ch] = False
            return results
    
    async def close(self) -> None:
        """Close all services."""
        with self._lock:
            for service in self._services.values():
                try:
                    await service.close()
                except Exception:
                    pass
            self._services.clear()
            self._running = False


# Placeholder imports for type hints


class SimpleNotification:
    """Simple notification data class."""
    
    def __init__(
        self,
        channel: str,
        recipient: str,
        subject: str = "",
        body: str = "",
        format: str = "markdown",
        priority: int = 0,
    ):
        self.channel = channel
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.format = format
        self.priority = priority
        self.channel_name = "custom"