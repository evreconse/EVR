"""
EVRECONSE Event Engine - Lifecycle Manager.

Internal component for managing engine lifecycle:
- Initialization of all components
- Startup/shutdown orchestration
- Graceful shutdown with proper resource cleanup
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass

from .engine_config import EngineConfig, EngineStats
from .event_dispatcher import EventDispatcher
from .event_factory import EventFactory
from .event_pipeline import EventPipeline, PipelineConfig
from .event_registry import EventRegistry
from .event_scheduler import EventScheduler
from .metrics import MetricsCollector, get_metrics


@dataclass(frozen=True, slots=True)
class LifecycleState:
    """Immutable lifecycle state snapshot."""
    initialized: bool = False
    running: bool = False
    shutting_down: bool = False
    error: str | None = None


class LifecycleManager:
    """
    Manages the complete lifecycle of Event Engine components.
    
    This is an INTERNAL component - not exposed in public API.
    Handles:
    - Component initialization order
    - Dependency wiring
    - Startup sequence
    - Graceful shutdown with proper cleanup
    - State management
    """
    
    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._lock = threading.RLock()
        
        # State
        self._state = LifecycleState()
        self._init_error: str | None = None
        
        # Components (initialized lazily)
        self._factory: EventFactory | None = None
        self._registry: EventRegistry | None = None
        self._scheduler: EventScheduler | None = None
        self._dispatcher: EventDispatcher | None = None
        self._pipeline: EventPipeline | None = None
        self._metrics: MetricsCollector | None = None
        
        # Task management
        self._async_stack: AsyncExitStack | None = None
        self._background_tasks: set[asyncio.Task] = set()
        
        # Statistics
        self._stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "rejected": 0,
            "processing_times": [],
        }
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def is_initialized(self) -> bool:
        return self._state.initialized
    
    @property
    def is_running(self) -> bool:
        return self._state.running
    
    @property
    def is_shutting_down(self) -> bool:
        return self._state.shutting_down
    
    @property
    def factory(self) -> EventFactory:
        if self._factory is None:
            raise RuntimeError("Engine not initialized")
        return self._factory
    
    @property
    def registry(self) -> EventRegistry:
        if self._registry is None:
            raise RuntimeError("Engine not initialized")
        return self._registry
    
    @property
    def scheduler(self) -> EventScheduler:
        if self._scheduler is None:
            raise RuntimeError("Engine not initialized")
        return self._scheduler
    
    @property
    def dispatcher(self) -> EventDispatcher:
        if self._dispatcher is None:
            raise RuntimeError("Engine not initialized")
        return self._dispatcher
    
    @property
    def pipeline(self) -> EventPipeline:
        if self._pipeline is None:
            raise RuntimeError("Engine not initialized")
        return self._pipeline
    
    @property
    def metrics(self) -> MetricsCollector:
        if self._metrics is None:
            raise RuntimeError("Engine not initialized")
        return self._metrics
    
    # =========================================================================
    # Initialization
    # =========================================================================
    
    def initialize(self, config: dict | None = None) -> None:
        """
        Initialize all components.
        
        Idempotent - safe to call multiple times.
        
        Args:
            config: Optional configuration override
        """
        with self._lock:
            if self._state.initialized:
                return
            
            try:
                # Apply config override
                if config:
                    self._config = EngineConfig(**config)
                
                # Initialize metrics first (used by other components)
                if self._config.enable_metrics:
                    self._metrics = get_metrics()
                
                # Initialize components in dependency order
                self._factory = EventFactory()
                self._registry = EventRegistry()
                self._scheduler = EventScheduler()
                self._dispatcher = EventDispatcher()
                
                # Register scheduler handlers
                self._register_scheduler_handlers()
                
                # Initialize pipeline last (depends on other components)
                self._pipeline = EventPipeline(
                    stages=[],
                    config=PipelineConfig(),
                )
                
                # Create default pipeline stages
                self._create_default_pipeline()
                
                self._state = LifecycleState(initialized=True)
                self._init_error = None
                
            except Exception as e:
                self._init_error = str(e)
                self._state = LifecycleState(initialized=False, error=str(e))
                # Cleanup on failure
                self._cleanup_components()
                raise
    
    def _register_scheduler_handlers(self) -> None:
        """Register default scheduler handlers."""
        if self._scheduler:
            # Handlers will be registered by EventEngine when needed
            # This is a placeholder for extension
            pass
    
    def _create_default_pipeline(self) -> None:
        """Create default pipeline stages."""
        # Pipeline stages are created by EventEngine with proper dependencies
    
    # =========================================================================
    # Startup
    # =========================================================================
    
    def start(self) -> None:
        """
        Start the engine.
        
        Idempotent - safe to call multiple times.
        Starts scheduler and dispatcher.
        """
        with self._lock:
            if self._state.running:
                return
            
            if not self._state.initialized:
                raise RuntimeError("Engine not initialized. Call initialize() first.")
            
            try:
                # Start scheduler
                if self._scheduler:
                    # Scheduler is async - start in event loop
                    self._start_scheduler_async()
                
                # Start dispatcher (if it has async components)
                self._start_dispatcher_async()
                
                self._state = LifecycleState(initialized=True, running=True)
                
            except Exception as e:
                self._state = LifecycleState(initialized=True, running=False, error=str(e))
                raise
    
    def _start_scheduler_async(self) -> None:
        """Start scheduler in async context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Schedule the async start
        loop.create_task(self._scheduler.start())
    
    def _start_dispatcher_async(self) -> None:
        """Start dispatcher in async context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Dispatcher doesn't need async start currently
    
    # =========================================================================
    # Shutdown
    # =========================================================================
    
    async def stop(self) -> None:
        """
        Stop the engine gracefully.
        
        Idempotent - safe to call multiple times.
        Waits for active tasks, stops all components.
        """
        with self._lock:
            if not self._state.running and not self._state.shutting_down:
                return
            
            self._state = LifecycleState(
                initialized=self._state.initialized,
                running=False,
                shutting_down=True,
            )
        
        try:
            # Stop accepting new events
            # Wait for active processing to complete (with timeout)
            await self._wait_for_active_tasks(timeout=30.0)
            
            # Stop scheduler
            await self._stop_scheduler()
            
            # Stop dispatcher
            await self._stop_dispatcher()
            
            # Close async stack (cleans up background tasks)
            await self._close_async_stack()
            
            # Clear registry (optional - for cleanup)
            # self._registry.clear()  # Commented out to preserve state
            
        finally:
            with self._lock:
                self._state = LifecycleState(
                    initialized=self._state.initialized,
                    running=False,
                    shutting_down=False,
                )
    
    async def _wait_for_active_tasks(self, timeout: float = 30.0) -> None:
        """Wait for active background tasks to complete."""
        if not self._background_tasks:
            return
        
        try:
            # Wait for tasks with timeout
            done, pending = await asyncio.wait(
                self._background_tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED,
            )
            
            # Cancel any remaining
            for task in pending:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellation
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
                
        except Exception:
            # Force cancel on error
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
    
    async def _stop_scheduler(self) -> None:
        """Stop the scheduler."""
        if self._scheduler:
            await self._scheduler.stop(timeout=5.0)
    
    async def _stop_dispatcher(self) -> None:
        """Stop the dispatcher."""
        if self._dispatcher:
            self._dispatcher.unsubscribe_all()
    
    async def _close_async_stack(self) -> None:
        """Close async exit stack."""
        if self._async_stack:
            await self._async_stack.aclose()
            self._async_stack = None
    
    def _cleanup_components(self) -> None:
        """Cleanup components on error."""
        self._factory = None
        self._registry = None
        self._scheduler = None
        self._dispatcher = None
        self._pipeline = None
        self._metrics = None
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> EngineStats:
        """Get engine statistics."""
        with self._lock:
            times = self._stats["processing_times"]
            avg_time = sum(times) / len(times) if times else 0.0
            
            return EngineStats(
                processed=self._stats["processed"],
                succeeded=self._stats["succeeded"],
                failed=self._stats["failed"],
                rejected=self._stats["rejected"],
                active_events=len(self._background_tasks),
                queued_events=self._registry.count() if self._registry else 0,
                avg_processing_time_ms=avg_time,
            )
    
    def record_processed(self, success: bool, duration_ms: float) -> None:
        """Record processing statistics."""
        with self._lock:
            self._stats["processed"] += 1
            if success:
                self._stats["succeeded"] += 1
            else:
                self._stats["failed"] += 1
            
            self._stats["processing_times"].append(duration_ms)
            if len(self._stats["processing_times"]) > 1000:
                self._stats["processing_times"] = self._stats["processing_times"][-1000:]
    
    def register_background_task(self, task: asyncio.Task) -> None:
        """Register a background task for lifecycle management."""
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)