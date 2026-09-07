"""
EVRECONSE Event Engine - Event Dispatcher.

Centralized event dispatching for internal events.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol


class EventHandler(Protocol):
    """Protocol for event handlers."""
    
    def __call__(self, event_type: str, event_data: dict) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class EventSubscription:
    """Immutable event subscription record."""
    subscription_id: str
    event_type: str
    handler: Callable
    filter_fn: Callable | None
    priority: int
    once: bool
    created_at: datetime


class EventDispatcher:
    """
    Centralized event dispatcher for internal events.
    
    Supports:
    - Multiple subscribers per event type
    - Async and sync handlers
    - Event filtering
    - Handler priorities
    - One-time subscriptions
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: dict[str, list[dict]] = {}
        self._subscription_counter = 0
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        filter_fn: Callable | None = None,
        priority: int = 0,
        once: bool = False,
    ) -> str:
        """
        Subscribe to event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Callable to invoke
            filter_fn: Optional filter function (event_type, event_data) -> bool
            priority: Handler priority (higher = called first)
            once: If True, auto-unsubscribe after first call
            
        Returns:
            Subscription ID
        """
        with self._lock:
            self._subscription_counter += 1
            subscription_id = f"{event_type}_{self._subscription_counter}"
            
            handler_info = {
                "subscription_id": subscription_id,
                "event_type": event_type,
                "handler": handler,
                "filter_fn": filter_fn,
                "priority": priority,
                "once": once,
                "created_at": datetime.now(UTC),
            }
            
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler_info)
            # Sort by priority (highest first)
            self._handlers[event_type].sort(key=lambda x: x["priority"], reverse=True)
            
            return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from event.
        
        Args:
            subscription_id: Subscription ID from subscribe()
            
        Returns:
            True if unsubscribed, False if not found
        """
        with self._lock:
            for event_type, handlers in self._handlers.items():
                for i, info in enumerate(handlers):
                    if info["subscription_id"] == subscription_id:
                        handlers.pop(i)
                        return True
        return False
    
    def unsubscribe_all(self, event_type: str | None = None) -> int:
        """
        Unsubscribe all handlers for event type or all types.
        
        Args:
            event_type: Specific event type, or None for all
            
        Returns:
            Number of unsubscribed handlers
        """
        with self._lock:
            if event_type:
                count = len(self._handlers.get(event_type, []))
                if event_type in self._handlers:
                    del self._handlers[event_type]
                return count
            else:
                count = sum(len(h) for h in self._handlers.values())
                self._handlers.clear()
                return count
    
    def publish(self, event_type: str, event_data: dict) -> int:
        """
        Publish event to all subscribers.
        
        Args:
            event_type: Event type
            event_data: Event data dictionary
            
        Returns:
            Number of handlers invoked
        """
        with self._lock:
            handlers = self._handlers.get(event_type, []).copy()
        
        if not handlers:
            return 0
        
        invoked = 0
        to_remove = []
        
        for info in handlers:
            try:
                # Apply filter
                if info["filter_fn"] and not info["filter_fn"](event_type, event_data):
                    continue
                
                # Execute handler
                handler = info["handler"]
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event_type, event_data))
                else:
                    handler(event_type, event_data)
                
                invoked += 1
                
                if info["once"]:
                    to_remove.append(info["subscription_id"])
                    
            except Exception:
                # Log in production - don't let one handler failure affect others
                pass
        
        # Remove one-time subscriptions
        for sub_id in to_remove:
            self.unsubscribe(sub_id)
        
        return invoked
    
    def publish_async(self, event_type: str, event_data: dict) -> int:
        """Publish event to async handlers."""
        return self.publish(event_type, event_data)
    
    def get_subscribers(self, event_type: str) -> list[dict]:
        """Get subscribers for event type."""
        with self._lock:
            return self._handlers.get(event_type, []).copy()
    
    def has_subscribers(self, event_type: str) -> bool:
        """Check if event type has subscribers."""
        with self._lock:
            return event_type in self._handlers and len(self._handlers[event_type]) > 0
    
    def get_stats(self) -> dict:
        """Get dispatcher statistics."""
        with self._lock:
            return {
                "event_types": len(self._handlers),
                "total_subscriptions": sum(len(h) for h in self._handlers.values()),
                "event_types": {
                    k: len(v) for k, v in self._handlers.items()
                },
            }