"""
EVRECONSE Event Engine - Event Scheduler (Async).

Async-native scheduler for event timeouts, monitoring, and periodic tasks.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from heapq import heappop, heappush
from uuid import uuid4


class SchedulerTaskType(str, Enum):
    """Scheduler task types."""
    EXPIRE_EVENTS = "expire_events"
    MONITOR_EVENTS = "monitor_events"
    CLEANUP_COMPLETED = "cleanup_completed"
    RECOVER_STUCK = "recover_stuck"
    PERSIST_SNAPSHOT = "persist_snapshot"
    HEARTBEAT = "heartbeat"


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    """Scheduled task with priority queue ordering."""
    task_id: str
    task_type: str
    event_id: str | None
    execute_at: datetime
    payload: dict
    recurring: bool = False
    interval: float | None = None
    
    def __lt__(self, other: ScheduledTask) -> bool:
        return self.execute_at < other.execute_at


class EventScheduler:
    """
    Async-native event scheduler for time-based operations.
    
    Manages:
    - Event timeouts and expirations
    - Periodic monitoring tasks
    - Delayed operations
    - Recurring tasks
    
    Uses asyncio for proper task lifecycle management.
    """
    
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._queue: list[ScheduledTask] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._handlers: dict[str, Callable] = {}
    
    async def start(self) -> None:
        """Start the scheduler."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self, timeout: float = 5.0) -> None:
        """Stop the scheduler gracefully."""
        async with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._stop_event.set()
            
            # Cancel main scheduler task
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await asyncio.wait_for(self._task, timeout=timeout)
                except (TimeoutError, asyncio.CancelledError):
                    pass
            
            # Cancel all running tasks
            for task_id, task in list(self._running_tasks.items()):
                if not task.done():
                    task.cancel()
            
            # Wait for all running tasks to complete
            if self._running_tasks:
                await asyncio.gather(
                    *self._running_tasks.values(),
                    return_exceptions=True
                )
            
            self._running_tasks.clear()
            self._task = None
    
    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running and not self._stop_event.is_set():
            try:
                await self._process_due_tasks()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log in production
                pass
            
            # Sleep briefly to prevent busy waiting
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=0.1)
            except TimeoutError:
                pass
    
    async def _process_due_tasks(self) -> None:
        """Process all due tasks."""
        now = datetime.now(UTC)
        
        async with self._lock:
            while self._queue and self._queue[0].execute_at <= now:
                task = heappop(self._queue)
                
                # Skip if already running
                if task.task_id in self._running_tasks:
                    continue
                
                # Schedule next occurrence if recurring
                if task.recurring and task.interval:
                    next_task = ScheduledTask(
                        task_id=task.task_id,
                        task_type=task.task_type,
                        event_id=task.event_id,
                        execute_at=datetime.now(UTC) + timedelta(seconds=task.interval),
                        payload=task.payload,
                        recurring=True,
                        interval=task.interval,
                    )
                    heappush(self._queue, next_task)
                
                # Execute task
                await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        handler = self._handlers.get(task.task_type)
        if not handler:
            # No handler registered - log and skip
            return
        
        try:
            if asyncio.iscoroutinefunction(handler):
                task_obj = asyncio.create_task(handler(task.payload))
            else:
                task_obj = asyncio.create_task(asyncio.to_thread(handler, task.payload))
            
            self._running_tasks[task.task_id] = task_obj
            
            # Clean up when done
            task_obj.add_done_callback(
                lambda t: self._running_tasks.pop(task.task_id, None)
            )
            
        except Exception:
            # Log in production
            pass
    
    # --- Scheduling Methods ---
    
    def schedule_event_expiration(self, event_id: str, expire_at: datetime) -> str:
        """Schedule event expiration check."""
        task = ScheduledTask(
            task_id=str(uuid4()),
            task_type=SchedulerTaskType.EXPIRE_EVENTS.value,
            event_id=event_id,
            execute_at=expire_at,
            payload={"event_id": event_id},
        )
        asyncio.create_task(self._add_task(task))
        return task.task_id
    
    def schedule_monitoring(self, event_id: str, interval_seconds: float = 30.0) -> str:
        """Schedule periodic event monitoring."""
        task = ScheduledTask(
            task_id=str(uuid4()),
            task_type=SchedulerTaskType.MONITOR_EVENTS.value,
            event_id=event_id,
            execute_at=datetime.now(UTC) + timedelta(seconds=interval_seconds),
            payload={"event_id": event_id},
            recurring=True,
            interval=interval_seconds,
        )
        asyncio.create_task(self._add_task(task))
        return task.task_id
    
    def schedule_one_time(self, task_type: str, execute_at: datetime, payload: dict) -> str:
        """Schedule a one-time task."""
        task = ScheduledTask(
            task_id=str(uuid4()),
            task_type=task_type,
            event_id=payload.get("event_id"),
            execute_at=execute_at,
            payload=payload,
        )
        asyncio.create_task(self._add_task(task))
        return task.task_id
    
    def schedule_recurring(self, task_type: str, interval_seconds: float, payload: dict) -> str:
        """Schedule a recurring task."""
        task = ScheduledTask(
            task_id=str(uuid4()),
            task_type=task_type,
            event_id=payload.get("event_id"),
            execute_at=datetime.now(UTC) + timedelta(seconds=interval_seconds),
            payload=payload,
            recurring=True,
            interval=interval_seconds,
        )
        asyncio.create_task(self._add_task(task))
        return task.task_id
    
    async def _add_task(self, task: ScheduledTask) -> None:
        """Add task to queue (thread-safe)."""
        async with self._lock:
            heappush(self._queue, task)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        # Note: This is O(n) but typically queue is small
        # For large queues, consider using a dict for O(1) lookup
        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                self._queue.pop(i)
                return True
        return False
    
    def cancel_event_tasks(self, event_id: str) -> int:
        """Cancel all tasks for an event."""
        count = 0
        new_queue = []
        for task in self._queue:
            if task.event_id == event_id:
                count += 1
            else:
                new_queue.append(task)
        self._queue = new_queue
        return count
    
    def get_pending_tasks(self, event_id: str | None = None) -> list[dict]:
        """Get pending tasks."""
        tasks = []
        for task in self._queue:
            if event_id is None or task.event_id == event_id:
                tasks.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "event_id": task.event_id,
                    "execute_at": task.execute_at.isoformat(),
                    "recurring": task.recurring,
                })
        return tasks
    
    def get_next_execution(self) -> datetime | None:
        """Get next scheduled execution time."""
        if self._queue:
            return self._queue[0].execute_at
        return None
    
    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            "pending_tasks": len(self._queue),
            "running_tasks": len(self._running_tasks),
            "running": self._running,
            "next_execution": self._queue[0].execute_at.isoformat() if self._queue else None,
        }
    
    @property
    def is_running(self) -> bool:
        return self._running