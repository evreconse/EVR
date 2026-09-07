"""
Fake Telegram Service for testing.

Provides a fake TelegramService that does not make real API calls.
"""

from __future__ import annotations

from typing import Any

from notification import DeliveryResult, DeliveryStatus, Notification


class FakeTelegramService:
    """Fake Telegram service for unit tests."""

    def __init__(self) -> None:
        self.channel_name = "telegram"
        self._connected = False
        self._messages: list[dict[str, Any]] = []
        self._send_count = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def send(self, notification: Notification) -> DeliveryResult:
        self._send_count += 1
        self._messages.append(
            {
                "channel": notification.channel,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "body": notification.body,
                "format": notification.format,
                "priority": notification.priority,
            }
        )
        return DeliveryResult(
            success=True,
            channel="telegram",
            recipient=str(notification.recipient),
            status=DeliveryStatus.DELIVERED,
        )

    async def send_batch(self, notifications: list[Notification]) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for notification in notifications:
            result = await self.send(notification)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        return self._connected

    async def close(self) -> None:
        await self.disconnect()

    def get_message_count(self) -> int:
        return self._send_count

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def clear_messages(self) -> None:
        self._messages.clear()
        self._send_count = 0


def create_fake_telegram_service() -> FakeTelegramService:
    """Factory function to create a fake Telegram service."""
    return FakeTelegramService()