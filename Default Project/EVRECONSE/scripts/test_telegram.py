#!/usr/bin/env python3
"""
Standalone Telegram diagnostic script for EVRECONSE.

This script loads the real project configuration, creates the real TelegramService,
connects to Telegram Bot API, and sends a test message.

Usage:
    python scripts/test_telegram.py
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path

# Add project src to path
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from config import AppConfig, ConfigurationManager, MultiSourceConfigLoader
from core import LoggingConfig, LogLevel, init_logging
from notification.telegram_service import create_telegram_service


async def main() -> int:
    print("[TEST] Loading configuration...")

    try:
        # Load configuration exactly like the application does
        loader = MultiSourceConfigLoader(
            file_path=PROJECT_ROOT / "config.yaml",
            dotenv_path=PROJECT_ROOT / ".env",
            env_prefix="EVRECONSE_",
        )
        config_manager = ConfigurationManager(loader=loader)

        result = config_manager.initialize()
        if not result.success:
            print(f"[TEST] Configuration failed: {result.validation_result.errors}")
            return 1

        config: AppConfig = config_manager.get_config()
        print("[TEST] Configuration loaded.")

        # Read Telegram configuration
        tg_config = config.notification.telegram
        bot_token = tg_config.bot_token
        chat_id = tg_config.chat_id

        if not bot_token or not chat_id:
            print("[TEST] ERROR: bot_token or chat_id is empty in configuration")
            print("[TEST] Set EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN and EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID")
            return 1

        # Print masked token and chat id
        masked_token = f"{bot_token[:6]}...{bot_token[-6:]}" if len(bot_token) > 12 else "***"
        print(f"[TEST] Bot token: {masked_token}")
        print(f"[TEST] Chat ID: {chat_id}")

        # Initialize logging
        log_config = LoggingConfig(
            level=LogLevel.INFO,
            log_path=None,
            console_enabled=True,
            file_enabled=False,
            json_format=False,
        )
        init_logging(log_config)

        # Create real TelegramService from project
        print("[TEST] Creating TelegramService...")
        telegram_service = create_telegram_service(
            bot_token=bot_token,
            chat_id=chat_id,
            parse_mode=tg_config.parse_mode,
            disable_web_page_preview=tg_config.disable_web_page_preview,
            disable_notification=tg_config.disable_notification,
        )
        print("[TEST] TelegramService created.")

        # Connect to Telegram
        print("[TEST] Connecting...")
        await telegram_service.connect()
        print("[TEST] Connected.")

        # Prepare test message
        timestamp = datetime.now(UTC).isoformat()
        message = (
            "✅ EVRECONSE Telegram test\n\n"
            f"Timestamp: {timestamp}"
        )

        # Send message
        print("[TEST] Sending message...")
        from notification.notification import SimpleNotification

        test_notification = SimpleNotification(
            channel="telegram",
            recipient=str(chat_id),
            subject="Test Message",
            body=message,
            format="markdown",
            priority=0,
        )

        result = await telegram_service.send(test_notification)
        print("[TEST] Message sent.")
        print(f"[TEST] Result: success={result.is_success}, notification_id={result.notification_id}")

        # Disconnect
        print("[TEST] Disconnecting...")
        await telegram_service.disconnect()
        print("[TEST] Disconnected.")

        print("[TEST] Finished.")
        return 0

    except Exception as e:
        print(f"[TEST] EXCEPTION: {type(e).__name__}: {e}")
        print("[TEST] Full traceback:")
        traceback.print_exc()

        # Try to extract HTTP details from exception
        if hasattr(e, 'status') or hasattr(e, 'response'):
            # aiohttp ClientResponseError or similar
            if hasattr(e, 'status'):
                print(f"[TEST] HTTP Status: {e.status}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try:
                    text = await e.response.text()
                    print(f"[TEST] Response body: {text}")
                except:
                    pass

        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))