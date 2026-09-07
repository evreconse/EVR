"""
EVRECONSE Notification - Queue.

Thread-safe notification queue with bounded capacity and priority support.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from .exceptions import QueueClosedError, QueueEmptyError, QueueFullError


@dataclass(frozen=True, slots=True)
class QueuedNotification:
    """A notification waiting in the queue."""
    
    notification_id: UUID
    channel: str
    recipient: str
    content: str
    format: str = "markdown"
    priority: int = 0  # Higher = more urgent
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    max_retries: int = 3
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Chart image attachment (for future Telegram photo support)
    chart_image_path: str | None = None
    chart_image_url: str | None = None
    
    def __post_init__(self) -> None:
        if self.scheduled_at is not None and self.scheduled_at.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")
        if self.scheduled_at is not None and self.scheduled_at < datetime.now(UTC):
            raise ValueError("scheduled_at cannot be in the past")
    
    def __lt__(self, other: QueuedNotification) -> bool:
        """Compare by priority (higher first), then by creation time."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


class NotificationQueue:
    """
    Thread-safe, async-safe notification queue.
    
    Features:
    - Bounded capacity with backpressure
    - Priority-based ordering
    - Scheduled notifications
    - Graceful shutdown
    - Backpressure handling
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        max_waiting: int = 100,
        default_timeout: float = 30.0,
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if max_waiting <= 0:
            raise ValueError("max_waiting must be positive")
        
        self._max_size = max_size
        self._max_waiting = max_waiting
        self._default_timeout = default_timeout
        
        self._queue: deque[QueuedNotification] = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._closed = False
        self._closed_event = asyncio.Event()
        
        # Statistics
        self._enqueued_count = 0
        self._dequeued_count = 0
        self._rejected_count = 0
        self._dropped_count = 0
        
        # For thread-safe operations
        self._thread_lock = threading.RLock()

    async def enqueue(
        self,
        notification: QueuedNotification,
        timeout: float | None = None,
    ) -> bool:
        """
        Add notification to queue.
        
        Args:
            notification: Notification to enqueue
            timeout: Maximum time to wait for space (None = default_timeout)
            
        Returns:
            True if enqueued, False if timeout
            
        Raises:
            QueueClosedError: If queue is closed
            QueueFullError: If queue is full and timeout=0
        """
        if timeout is None:
            timeout = self._default_timeout
        
        async with self._not_full:
            # Wait for space
            start_time = time.monotonic()
            while len(self._queue) >= self._max_size:
                if self._closed:
                    raise QueueClosedError("Queue is closed")
                
                if timeout == 0:
                    self._rejected_count += 1
                    raise QueueFullError("Queue is full")
                
                try:
                    remaining = timeout - (time.monotonic() - start_time)
                    if remaining <= 0:
                        self._rejected_count += 1
                        raise QueueFullError("Enqueue timeout")
                    await asyncio.wait_for(
                        self._not_full.wait(),
                        timeout=remaining,
                    )
                except TimeoutError:
                    self._rejected_count += 1
                    raise QueueFullError("Enqueue timeout") from None
            
            if self._closed:
                raise QueueClosedError("Queue is closed")
            
            # Insert with priority
            self._insert_sorted(notification)
            self._enqueued_count += 1
            self._not_empty.notify()
            return True
    
    def _insert_sorted(self, notification: QueuedNotification) -> None:
        """Insert notification maintaining priority order."""
        # Higher priority first, then earlier created_at
        insert_idx = 0
        for i, existing in enumerate(self._queue):
            if notification < existing:
                break
        self._queue.insert(insert_idx, notification)
    
    async def dequeue(self, timeout: float | None = None) -> QueuedNotification:
        """
        Dequeue next notification.
        
        Args:
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            Next notification in queue
            
        Raises:
            QueueClosedError: If queue is closed and empty
            QueueEmptyError: If queue is empty and timeout=0
            asyncio.TimeoutError: If timeout expires
        """
        if timeout is None:
            timeout = self._default_timeout
        
        async with self._not_empty:
            while not self._queue:
                if self._closed:
                    raise QueueClosedError("Queue is closed and empty")
                
                if timeout == 0:
                    raise QueueEmptyError("Queue is empty")
                
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=timeout,
                    )
                except TimeoutError:
                    # Return a special sentinel or re-raise to allow heartbeat
                    raise
            
            if self._closed and not self._queue:
                raise QueueClosedError("Queue is closed and empty")
            
            notification = self._queue.popleft()
            self._dequeued_count += 1
            self._not_full.notify()
            return notification
    
    def dequeue_nowait(self) -> QueuedNotification | None:
        """
        Try to dequeue without waiting.
        
        Returns:
            Notification or None if empty
        """
        with self._thread_lock:
            if self._queue:
                notification = self._queue.popleft()
                self._dequeued_count += 1
                self._not_full.notify()
                return notification
            return None
    
    def enqueue_nowait(self, notification: QueuedNotification) -> bool:
        """
        Try to enqueue without waiting.
        
        Args:
            notification: Notification to enqueue
            
        Returns:
            True if enqueued, False if queue full
            
        Raises:
            QueueClosedError: If queue is closed
        """
        with self._thread_lock:
            if self._closed:
                raise QueueClosedError("Queue is closed")
            
            if len(self._queue) >= self._max_size:
                self._rejected_count += 1
                return False
            
            self._insert_sorted(notification)
            self._enqueued_count += 1
            self._not_full.notify()
            return True
    
    def dequeue_nowait(self) -> QueuedNotification | None:
        """Try to dequeue without waiting."""
        with self._thread_lock:
            if self._queue:
                notification = self._queue.popleft()
                self._dequeued_count += 1
                self._not_full.notify()
                return notification
            return None
    
    def remove(self, notification_id: UUID) -> bool:
        """
        Remove a specific notification from queue.
        
        Args:
            notification_id: ID of notification to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._thread_lock:
            for i, notification in enumerate(self._queue):
                if notification.notification_id == notification_id:
                    del self._queue[i]
                    self._not_full.notify_all()
                    return True
            return False
    
    def cancel_scheduled(self, before: datetime) -> int:
        """
        Cancel all notifications scheduled before given time.
        
        Returns:
            Number of cancelled notifications
        """
        with self._thread_lock:
            original_len = len(self._queue)
            self._queue = deque(
                n for n in self._queue
                if n.scheduled_at is None or n.scheduled_at >= before
            )
            cancelled = original_len - len(self._queue)
            if cancelled:
                self._not_full.notify_all()
            return cancelled
    
    def close(self) -> None:
        """Close the queue, preventing further enqueue operations."""
        with self._thread_lock:
            if not self._closed:
                self._closed = True
                self._closed_event.set()
                # Wake all waiters
                self._not_empty.notify_all()
                self._not_full.notify_all()
    
    async def wait_closed(self) -> None:
        """Wait until queue is closed."""
        await self._closed_event.wait()
    
    def is_closed(self) -> bool:
        """Check if queue is closed."""
        with self._thread_lock:
            return self._closed
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._thread_lock:
            return len(self._queue) == 0
    
    def size(self) -> int:
        """Get current queue size."""
        with self._thread_lock:
            return len(self._queue)
    
    def capacity(self) -> int:
        """Get maximum queue capacity."""
        return self._max_size
    
    def stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        with self._thread_lock:
            return {
                "size": len(self._queue),
                "capacity": self._max_size,
                "utilization": len(self._queue) / self._max_size,
                "enqueued": self._enqueued_count,
                "dequeued": self._dequeued_count,
                "rejected": self._rejected_count,
                "dropped": self._dropped_count,
                "closed": self._closed,
            }
    
    def clear(self) -> int:
        """Remove all items from queue. Returns count of removed items."""
        with self._thread_lock:
            count = len(self._queue)
            self._queue.clear()
            self._not_full.notify_all()
            return count
    
    def __len__(self) -> int:
        return self.size()
    
    def __bool__(self) -> bool:
        return not self.is_empty()


# Synchronous wrapper for NotificationQueue
class SyncNotificationQueue:
    """Synchronous wrapper for NotificationQueue."""
    
    def __init__(self, queue: NotificationQueue) -> None:
        self._queue = queue
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def enqueue(self, notification: QueuedNotification, timeout: float | None = None) -> bool:
        """Enqueue notification (blocking)."""
        loop = self._get_loop()
        return loop.run_until_complete(self._queue.enqueue(notification, timeout))
    
    def dequeue(self, timeout: float | None = None) -> QueuedNotification:
        """Dequeue notification (blocking)."""
        loop = self._get_loop()
        return loop.run_until_complete(self._queue.dequeue(timeout))
    
    def dequeue_nowait(self) -> QueuedNotification | None:
        """Try to dequeue without waiting."""
        return self._queue.dequeue_nowait()
    
    def enqueue_nowait(self, notification: QueuedNotification) -> bool:
        """Enqueue without waiting."""
        return self._queue.enqueue_nowait(notification)
    
    def close(self) -> None:
        """Close the queue."""
        self._queue.close()
    
    def close_async(self) -> None:
        """Close the queue (async)."""
        loop = self._get_loop()
        loop.run_until_complete(self._queue.wait_closed())
    
    def stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        loop = self._get_loop()
        return loop.run_until_complete(asyncio.coroutine(self._queue.stats)())
    
    def is_closed(self) -> bool:
        return self._queue.is_closed()
    
    def is_empty(self) -> bool:
        return self._queue.is_empty()
    
    def size(self) -> int:
        return self._queue.size()
    
    def capacity(self) -> int:
        return self._queue.capacity()