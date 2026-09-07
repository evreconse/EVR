¿#!/usr/bin/env python3
"""
EVRECONSE - Main Entry Point.

Production entry point for the EVRECONSE trading bot.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from application import create_application
from core import LoggingConfig, LogLevel, init_logging, shutdown_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EVRECONSE Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Run with default config
  python -m src.main --config config.yaml  # Run with config file
  python -m src.main --log-level DEBUG   # Enable debug logging
  python -m src.main --testnet           # Run on testnet
        """,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to configuration file (YAML)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path",
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use Bybit testnet",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Initialize but don't start processing",
    )
    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Initialize logging
    log_config = LoggingConfig(
        level=LogLevel.from_string(args.log_level),
        log_path=args.log_file,
        console_enabled=True,
        file_enabled=bool(args.log_file),
        json_format=True,
    )
    init_logging(log_config)

    try:
        # Create application
        app = create_application(
            config_path=args.config,
        )

        if args.dry_run:
            # For dry-run, just initialize
            await app.initialize()
            print("Application initialized successfully (dry run)")
            print(f"State: {app.state.value}")
            print(f"Config: {app.config}")
            
            # Cleanup resources before exit
            try:
                await app.shutdown()
                print("Application shutdown complete (dry run)")
            except Exception as e:
                print(f"Shutdown warning: {e}", file=sys.stderr)
            
            return 0

        # Initialize and start application
        await app.initialize()
        await app.start()
        print("Application started successfully")
        print(f"State: {app.state.value}")

        # Setup and run health check
        if app.context:
            app.setup_health_checks(app.context)
            report = await app.health_check()
            print(f"Health: {report.overall_status.value}")
            for name, comp in report.components.items():
                print(f"  {name}: {comp.status.value} ({comp.message})")

        # Keep running until interrupted
        try:
            while app.is_running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("\nShutdown requested...")

        # Graceful shutdown
        await app.shutdown()
        print("Application stopped gracefully")
        return 0

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1
    finally:
        shutdown_logging()


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))Ý *cascade08Ýµ*cascade08µÖ *cascade08Ö÷*cascade08÷¿ *cascade082Gfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/main.py