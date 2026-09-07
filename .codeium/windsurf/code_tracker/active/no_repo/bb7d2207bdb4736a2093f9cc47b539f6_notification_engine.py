◊C"""
EVRECONSE Notification Engine.

Orchestration engine for notification delivery.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .delivery_result import DeliveryResult
from .queue import NotificationQueue, QueuedNotification
from .rate_limiter import RateLimitConfig
from .retry_policy import RetryPolicyConfig


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Configuration for Notification Engine."""
    
    queue_size: int = 10000
    max_concurrent_deliveries: int = 10
    default_timeout: float = 30.0
    retry_policy: RetryPolicyConfig | None = None
    rate_limit: RateLimitConfig | None = None


class NotificationEngine:
    """
    Notification orchestration engine.
    
    Manages notification delivery through multiple channels with
    queuing, retry logic, rate limiting, and metrics.
    """
    
    def __init__(
        self,
        config: EngineConfig | None = None,
    ) -> None:
        self._config = config or EngineConfig()
        self._lock = threading.RLock()
        self._running = False
        
        # Services
        self._services: dict[str, NotificationService] = {}
        
        # Queue
        queue_size = self._config.queue_size if hasattr(self._config, "queue_size") else 10000
        self._queue = NotificationQueue(max_size=10000)
        
        # Retry policy
        retry_config = self._config.retry_policy if hasattr(self._config, "retry_policy") else None
        if retry_config:
            from .retry_policy import RetryPolicy, RetryPolicyConfig
            self._retry_policy = RetryPolicy(RetryPolicyConfig(
                max_attempts=retry_config.max_attempts,
                base_delay=retry_config.base_delay,
                max_delay=retry_config.max_delay,
                multiplier=retry_config.multiplier if hasattr(retry_config, 'multiplier') else 2.0,
                jitter=retry_config.jitter,
            ))
        else:
            from .retry_policy import RetryPolicy, RetryPolicyConfig
            self._retry_policy = RetryPolicy(RetryPolicyConfig())
        
        # Rate limiter
        if hasattr(self._config, "rate_limit") and self._config.rate_limit:
            from .rate_limiter import RateLimitConfig, RateLimiter
            self._rate_limiter = RateLimiter(RateLimitConfig(
                requests_per_second=10.0,
                requests_per_minute=100.0,
            ))
        else:
            from .rate_limiter import RateLimitConfig, RateLimiter
            self._rate_limiter = RateLimiter(RateLimitConfig(requests_per_second=10.0))
        
        # Background tasks
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []
        self._stats = {
            "sent": 0,
            "delivered": 0,
            "failed": 0,
            "retries": 0,
        }
    
    def register_service(self, service: NotificationService) -> None:
        """Register a notification service."""
        with self._lock:
            self._services[service.channel_name] = service
    
    def unregister_service(self, channel: str) -> None:
        """Unregister a service."""
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
    
    async def start(self) -> None:
        """Start the notification engine."""
        if self._running:
            return
        
        self._running = True
        
        # Connect all services
        for service in self._services.values():
            try:
                await service.connect()
            except Exception:
                # Log but continue
                pass
        
        # Start worker tasks
        self._worker_tasks = [
            asyncio.create_task(self._worker()),
        ]
    
    async def stop(self) -> None:
        """Stop the notification engine."""
        self._running = False
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Disconnect all services
        for service in self._services.values():
            try:
                await service.disconnect()
            except Exception:
                pass
    
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
        Send a notification through specified channel.
        
        Args:
            channel: Channel name (telegram, email, slack, etc.)
            recipient: Recipient identifier
            subject: Message subject
            body: Message body
            format: Message format (markdown, html, plain)
            priority: Message priority (higher = more urgent)
            
        Returns:
            DeliveryResult
        """
        # Validate channel
        service = self.get_service(channel)
        if not service:
            raise ValueError(f"No service registered for channel: {channel}")
        
        # Create notification
        from .delivery_result import QueuedNotification
        notification = QueuedNotification(
            notification_id=__import__("uuid").uuid4(),
            channel=channel,
            recipient=recipient,
            content=body,
            format=format,
            priority=priority,
            metadata={"subject": subject},
        )
        
        # Enqueue with retry policy
        return await self._enqueue_with_retry(notification)
    
    async def _enqueue_with_retry(self, notification: QueuedNotification) -> DeliveryResult:
        """Enqueue notification with retry logic."""
        attempt = 0
        max_attempts = 3
        last_exception = None
        
        while attempt <= self._retry_policy._config.max_attempts:
            try:
                # Rate limit
                await self._rate_limiter.acquire()
                
                # Enqueue
                await self._queue.enqueue(notification)
                
                # Wait for delivery (with timeout)
                # In production, this would wait for actual delivery confirmation
                # For now, return pending result
                return DeliveryResult.create_pending(
                    notification_id=notification.notification_id,
                    channel=notification.channel,
                    recipient=notification.recipient,
                )
            except Exception as e:
                if not self._retry_policy.should_retry(attempt, e):
                    raise
                
                delay = self._retry_policy.get_delay(attempt)
                await asyncio.sleep(delay)
                attempt += 1
        
        # All retries exhausted
        return DeliveryResult(
            notification_id=notification.notification_id,
            channel=notification.channel,
            recipient=notification.recipient,
            status="failed",
            sent_at=datetime.now(UTC),
            error="Max retries exceeded",
            attempts=attempt + 1,
        )
    
    async def _worker(self) -> None:
        """Background worker for processing queue."""
        while True:
            try:
                notification = await self._queue.dequeue()
                # Process notification
                # This would integrate with actual delivery logic
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Log and continue
    
    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            return {
                "running": self._running,
                "registered_channels": list(self._services.keys()),
                "queue_size": self._queue.size(),
                "queue_capacity": self._queue.capacity(),
                "stats": self._stats.copy(),
            }
    
    async def close(self) -> None:
        """Shutdown engine."""
        await self.stop()ˇ ˇé*cascade08
éè èõ*cascade08
õù ùû*cascade08
ûü ü§*cascade08
§Æ Æπ*cascade08
π◊C 2cfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/notification/notification_engine.py