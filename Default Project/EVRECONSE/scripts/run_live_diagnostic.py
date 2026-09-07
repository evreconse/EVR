#!/usr/bin/env python3
"""
Live diagnostic script - runs the real EVRECONSE application with live logging.

This script starts the actual application with real Bybit/Telegram credentials,
uses the existing structured logger, and saves all logs to logs/live_diagnostic.log.

Usage:
    python scripts/run_live_diagnostic.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add project src to path
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

# CRITICAL: Change to project root so .env is found relative to project root
os.chdir(PROJECT_ROOT)

from application import create_application
from core import LoggingConfig, LogLevel, init_logging, shutdown_logging


async def main() -> int:
    """Run live diagnostic with real Bybit/Telegram connections."""
    
    # Ensure logs directory exists
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / "live_diagnostic.log"
    
    # Configure logging - use existing structured logger with file output
    log_config = LoggingConfig(
        level=LogLevel.DEBUG,  # Use DEBUG to capture all pipeline steps
        log_path=log_file,
        console_enabled=True,
        file_enabled=True,
        json_format=True,  # Structured JSON logs for easy parsing
        max_bytes=50_000_000,
        backup_count=5,
    )
    init_logging(log_config)
    
    print(f"[LIVE] Starting EVRECONSE live diagnostic")
    print(f"[LIVE] Log file: {log_file}")
    print(f"[LIVE] Press Ctrl+C to stop gracefully")
    print(f"[LIVE] Waiting for real Bybit WebSocket data...")
    
    # Create application with real config
    app = create_application(config_path=PROJECT_ROOT / "config.yaml")
    
    # Setup graceful shutdown
    shutdown_requested = asyncio.Event()
    
    def signal_handler():
        print("\n[LIVE] Shutdown requested...")
        shutdown_requested.set()
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            pass
    
    try:
        # Initialize application
        print("[LIVE] Initializing application...")
        await app.initialize()
        print("[LIVE] Application initialized")
        
        # Start application (connects to Bybit WebSocket, starts Telegram, etc.)
        print("[LIVE] Starting application...")
        await app.start()
        print("[LIVE] Application started - connected to Bybit WebSocket")
        print("[LIVE] Waiting for real market data...")
        
        # Setup health checks
        if app.context:
            app.setup_health_checks(app.context)
        
# Wait for shutdown signal
        await shutdown_requested.wait()
        
    except Exception as e:
        print(f"[LIVE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Graceful shutdown
        print("[LIVE] Shutting down...")
        try:
            await app.shutdown()
            print("[LIVE] Application stopped gracefully")
        except Exception as e:
            print(f"[LIVE] Shutdown error: {e}")
        finally:
            shutdown_logging()
        
        # Print summary
        print(f"[LIVE] Diagnostic complete. Logs saved to: {log_file}")
        
        # Check if pipeline executed by looking at logs
        print("[LIVE] Checking pipeline execution in logs...")
        import json
        with open(log_file, 'r') as f:
            pipeline_logs = [line for line in f if 'PIPELINE' in line or 'Strategy' in line or 'Scorer' in line or 'Notifier' in line]
            if pipeline_logs:
                print(f"[LIVE] Found {len(pipeline_logs)} pipeline log entries:")
                for log in pipeline_logs[-10:]:
                    print(f"  {log.strip()}")
            else:
                print("[LIVE] No pipeline logs found - pipeline may not be executing")
        
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))