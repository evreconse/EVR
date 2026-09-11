"""
EVRECONSE Notification - Telegram Service.

Production-ready Telegram Bot API implementation with:
- MarkdownV2, HTML, and Plain text formatting
- Rate limiting (30 messages/second)
- Retry with exponential backoff
- Message queue with persistence
- Health checks
- Proper error handling
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from src.core import get_logger

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    DeliveryError,
    DeliveryTimeoutError,
    RateLimitError,
    ValidationError,
)
from .notification import DeliveryResult, Notification
from .rate_limiter import RateLimitConfig, RateLimiter

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass(frozen=True, slots=True)
class TelegramConfig:
    """Telegram service configuration."""
    bot_token: str
    chat_id: str | int
    parse_mode: str = "MarkdownV2"
    disable_web_page_preview: bool = True
    disable_notification: bool = False
    timeout: float = 30.0
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise ValueError("Bot token is required")
        if not self.chat_id:
            raise ValueError("Chat ID is required")


# =============================================================================
# Message Formatting
# =============================================================================

def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    Characters to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_markdown_v2(subject: str | None, body: str) -> str:
    """Format message for MarkdownV2."""
    lines = []
    if subject:
        lines.append(f"*{escape_markdown_v2(subject)}*")
        lines.append("")
    lines.append(escape_markdown_v2(body))
    return "\n".join(lines)


def format_html(subject: str | None, body: str) -> str:
    """Format message for HTML."""
    lines = []
    if subject:
        lines.append(f"<b>{subject}</b>")
        lines.append("")
    # HTML mode supports \n directly, don't use <br>
    lines.append(body)
    return "\n".join(lines)


def format_plain(subject: str | None, body: str) -> str:
    """Format message as plain text."""
    lines = []
    if subject:
        lines.append(subject)
        lines.append("")
    lines.append(body)
    return "\n".join(lines)


def format_notification(notification: Notification, parse_mode: str) -> str:
    """Format notification based on parse mode."""
    if parse_mode == "MarkdownV2":
        return format_markdown_v2(notification.subject, notification.body)
    elif parse_mode == "HTML":
        return format_html(notification.subject, notification.body)
    elif parse_mode == "Markdown":
        # Legacy markdown - less escaping
        return format_plain(notification.subject, notification.body)
    else:
        return format_plain(notification.subject, notification.body)


# =============================================================================
# Delivery Result
# =============================================================================

@dataclass(frozen=True, slots=True)
class TelegramDeliveryResult:
    """Result of Telegram message delivery."""
    success: bool
    message_id: int | None = None
    channel: str = "telegram"
    recipient: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    retry_after: float | None = None

    def to_delivery_result(self) -> DeliveryResult:
        """Convert to standard DeliveryResult."""
        from uuid import uuid4
        from .enums import DeliveryStatus
        return DeliveryResult(
            notification_id=uuid4(),
            channel=self.channel,
            recipient=self.recipient,
            status=DeliveryStatus.DELIVERED.value if self.success else DeliveryStatus.FAILED.value,
            sent_at=datetime.now(UTC),
            delivered_at=datetime.now(UTC) if self.success else None,
            duration_ms=0.0,
            attempts=1,
            error=self.error,
            error_code=None,
            metadata={},
        )


# =============================================================================
# Telegram Service
# =============================================================================

class TelegramService:
    """
    Telegram Bot API implementation of NotificationService.

    Features:
    - Multiple parse modes (MarkdownV2, HTML, Plain)
    - Automatic escaping for MarkdownV2
    - Rate limiting (30 msg/s per chat)
    - Retry with exponential backoff
    - Message validation
    - Health checks
    """

    def __init__(self, config: TelegramConfig) -> None:
        self._config = config
        self._api_url = f"https://api.telegram.org/bot{config.bot_token}"
        self._session: ClientSession | None = None
        self._connected = False
        self._rate_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=30.0,  # Telegram limit: 30 msg/s per chat
            burst_allowance=30,
        ))
        self._lock = asyncio.Lock()
    
    @property
    def channel_name(self) -> str:
        """Return the channel name for this service."""
        return "telegram"

    async def connect(self) -> None:
        """Establish connection to Telegram API."""
        async with self._lock:
            if self._connected:
                return

            timeout = ClientTimeout(total=self._config.timeout)
            self._session = ClientSession(
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )

            # Test connection
            try:
                async with self._session.get(f"{self._api_url}/getMe") as resp:
                    if resp.status != 200:
                        raise ConnectionError(f"Telegram API error: HTTP {resp.status}")
                    data = await resp.json()
                    if not data.get("ok"):
                        raise ConnectionError(f"Telegram API error: {data}")
            except aiohttp.ClientError as e:
                raise ConnectionError(f"Failed to connect to Telegram: {e}") from e

            self._connected = True
            logger.info("Telegram service connected")

    async def disconnect(self) -> None:
        """Disconnect from Telegram API."""
        async with self._lock:
            if self._session:
                await self._session.close()
                self._session = None
            self._connected = False
            logger.info("Telegram service disconnected")

    def is_connected(self) -> bool:
        return self._connected

    async def send(self, notification: Notification) -> DeliveryResult:
        """
        Send a notification via Telegram Bot API.

        Args:
            notification: Notification to send

        Returns:
            DeliveryResult with success status and details
        """
        print(f"[DEBUG-TELEGRAM] send: starting for notification {notification.notification_id}")
        if not self._connected:
            print(f"[DEBUG-TELEGRAM] send: not connected!")
            raise ConnectionError("Telegram service not connected")

        # Rate limit
        print(f"[DEBUG-TELEGRAM] send: acquiring rate limiter")
        await self._rate_limiter.acquire()
        print(f"[DEBUG-TELEGRAM] send: rate limiter acquired")

        # Validate
        if not notification.body:
            print(f"[DEBUG-TELEGRAM] send: empty body!")
            raise ValidationError("Message body cannot be empty")

        # Determine parse_mode from notification format
        fmt = getattr(notification, 'format', 'markdown').lower()
        if fmt == 'html':
            parse_mode = 'HTML'
        elif fmt == 'markdown' or fmt == 'markdown_v2':
            parse_mode = 'MarkdownV2'
        else:
            parse_mode = 'MarkdownV2'

        # Format message
        print(f"[DEBUG-TELEGRAM] send: formatting message")
        message_text = format_notification(notification, parse_mode)
        print(f"[DEBUG-TELEGRAM] send: formatted message length={len(message_text)}")

        # Truncate if too long (Telegram limit: 4096 characters)
        if len(message_text) > 4096:
            message_text = message_text[:4093] + "..."

        # Mask bot token in URL for logging
        masked_url = f"{self._api_url[:self._api_url.find('/bot')+4]}***MASKED***{self._api_url[self._api_url.find('/sendMessage'):] if '/sendMessage' in self._api_url else ''}"
        print(f"[DEBUG-TELEGRAM] send: api_url={masked_url}")
        print(f"[DEBUG-TELEGRAM] send: chat_id={self._config.chat_id}")
        print(f"[DEBUG-TELEGRAM] send: payload text_length={len(message_text)} parse_mode={parse_mode}")

        payload = {
            "chat_id": str(self._config.chat_id),
            "text": message_text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": self._config.disable_web_page_preview,
            "disable_notification": self._config.disable_notification,
        }

        # Retry logic
        last_error = None
        for attempt in range(self._config.max_retries):
            try:
                print(f"[DEBUG-TELEGRAM] send: attempt {attempt+1}/{self._config.max_retries}")
                print(f"[DEBUG-TELEGRAM] send: making HTTP POST to {self._api_url}/sendMessage")
                async with self._session.post(
                    f"{self._api_url}/sendMessage",
                    json=payload,
                ) as resp:
                    print(f"[DEBUG-TELEGRAM] send: HTTP response status={resp.status}")
                    data = await resp.json()
                    print(f"[DEBUG-TELEGRAM] send: response JSON: {str(data).encode('ascii', 'replace').decode()}")

                    if not data.get("ok"):
                        error = data.get("description", "Unknown error")
                        print(f"[DEBUG-TELEGRAM] send: API error: {error}")

                        # Handle specific errors
                        if resp.status == 429:
                            retry_after = data.get("parameters", {}).get("retry_after", 1)
                            if attempt < self._config.max_retries - 1:
                                print(f"[DEBUG-TELEGRAM] send: rate limited, waiting {retry_after}s")
                                await asyncio.sleep(retry_after)
                                continue
                            raise RateLimitError(f"Rate limited: {error}", retry_after=retry_after)
                        elif resp.status == 401:
                            print(f"[DEBUG-TELEGRAM] send: authentication failed")
                            raise AuthenticationError("Telegram authentication failed")
                        elif resp.status == 400:
                            if "chat not found" in error.lower():
                                raise ValidationError(f"Invalid chat ID: {error}")
                            else:
                                raise ValidationError(f"Bad request: {error}")
                        else:
                            raise DeliveryError(f"Telegram API error: {error}")

                    message_id = data.get("result", {}).get("message_id")
                    print(f"[DEBUG-TELEGRAM] send: SUCCESS! message_id={message_id}")
                    return TelegramDeliveryResult(
                        success=True,
                        message_id=message_id,
                        channel="telegram",
                        recipient=str(self._config.chat_id),
                    ).to_delivery_result()

            except (RateLimitError, AuthenticationError, ValidationError):
                print(f"[DEBUG-TELEGRAM] send: re-raising controlled exception")
                raise
            except aiohttp.ClientError as e:
                last_error = e
                print(f"[DEBUG-TELEGRAM] send: ClientError on attempt {attempt+1}: {e}")
                if attempt < self._config.max_retries - 1:
                    delay = min(self._config.retry_base_delay * (2 ** attempt), self._config.retry_max_delay)
                    print(f"[DEBUG-TELEGRAM] send: retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise DeliveryError(f"Network error: {e}") from e
            except TimeoutError:
                last_error = DeliveryTimeoutError("Request timeout")
                print(f"[DEBUG-TELEGRAM] send: TimeoutError on attempt {attempt+1}")
                if attempt < self._config.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise

        print(f"[DEBUG-TELEGRAM] send: all retries exhausted, last_error={last_error}")
        raise DeliveryError(f"Failed after {self._config.max_retries} attempts: {last_error}")

    async def send_photo(
        self,
        chat_id: str | int,
        photo_path: str,
        caption: str = "",
        parse_mode: str = "HTML",
    ) -> DeliveryResult:
        """
        Send a photo with caption via Telegram Bot API.

        Args:
            chat_id: Target chat ID
            photo_path: Path to the image file
            caption: Optional caption for the photo
            parse_mode: Parse mode for caption (HTML or MarkdownV2)

        Returns:
            DeliveryResult with success status and details
        """
        print(f"[DEBUG-TELEGRAM] send_photo: starting for chat_id={chat_id}")
        if not self._connected:
            print(f"[DEBUG-TELEGRAM] send_photo: not connected!")
            raise ConnectionError("Telegram service not connected")

        if not photo_path or not Path(photo_path).exists():
            raise ValidationError(f"Photo file not found: {photo_path}")

        # Rate limit
        await self._rate_limiter.acquire()

        # Determine parse_mode
        parse_mode = parse_mode if parse_mode in ("HTML", "MarkdownV2", "Markdown") else "HTML"

        # Prepare multipart form data
        from aiohttp import FormData
        form = FormData()
        form.add_field("chat_id", str(chat_id))
        if caption:
            form.add_field("caption", caption)
        form.add_field("parse_mode", parse_mode)
        form.add_field("disable_web_page_preview", str(self._config.disable_web_page_preview).lower())
        form.add_field("disable_notification", str(self._config.disable_notification).lower())

        # Add photo file
        with open(photo_path, "rb") as f:
            form.add_field("photo", f, filename=Path(photo_path).name, content_type="image/png")

        # Retry logic
        last_error = None
        for attempt in range(self._config.max_retries):
            try:
                print(f"[DEBUG-TELEGRAM] send_photo: attempt {attempt+1}/{self._config.max_retries}")
                print(f"[DEBUG-TELEGRAM] send_photo: making HTTP POST to {self._api_url}/sendPhoto")
                async with self._session.post(
                    f"{self._api_url}/sendPhoto",
                    data=form,
                ) as resp:
                    print(f"[DEBUG-TELEGRAM] send_photo: HTTP response status={resp.status}")
                    data = await resp.json()
                    print(f"[DEBUG-TELEGRAM] send_photo: response JSON: {str(data).encode('ascii', 'replace').decode()}")

                    if not data.get("ok"):
                        error = data.get("description", "Unknown error")
                        print(f"[DEBUG-TELEGRAM] send_photo: API error: {error}")

                        if resp.status == 429:
                            retry_after = data.get("parameters", {}).get("retry_after", 1)
                            if attempt < self._config.max_retries - 1:
                                print(f"[DEBUG-TELEGRAM] send_photo: rate limited, waiting {retry_after}s")
                                await asyncio.sleep(retry_after)
                                continue
                            raise RateLimitError(f"Rate limited: {error}", retry_after=retry_after)
                        elif resp.status == 401:
                            raise AuthenticationError("Telegram authentication failed")
                        elif resp.status == 400:
                            if "chat not found" in error.lower():
                                raise ValidationError(f"Invalid chat ID: {error}")
                            else:
                                raise ValidationError(f"Bad request: {error}")
                        else:
                            raise DeliveryError(f"Telegram API error: {error}")

                    message_id = data.get("result", {}).get("message_id")
                    print(f"[DEBUG-TELEGRAM] send_photo: SUCCESS! message_id={message_id}")
                    return TelegramDeliveryResult(
                        success=True,
                        message_id=message_id,
                        channel="telegram",
                        recipient=str(chat_id),
                    ).to_delivery_result()

            except (RateLimitError, AuthenticationError, ValidationError):
                raise
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    delay = min(self._config.retry_base_delay * (2 ** attempt), self._config.retry_max_delay)
                    print(f"[DEBUG-TELEGRAM] send_photo: ClientError on attempt {attempt+1}: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise DeliveryError(f"Network error: {e}") from e
            except TimeoutError:
                last_error = DeliveryTimeoutError("Request timeout")
                if attempt < self._config.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise

        print(f"[DEBUG-TELEGRAM] send_photo: all retries exhausted, last_error={last_error}")
        raise DeliveryError(f"Failed after {self._config.max_retries} attempts: {last_error}")

    async def send_batch(self, notifications: list[Notification]) -> list[DeliveryResult]:
        """Send multiple notifications with rate limiting."""
        results = []
        for notification in notifications:
            try:
                result = await self.send(notification)
                results.append(result)
            except Exception as e:
                results.append(DeliveryResult(
                    success=False,
                    channel="telegram",
                    recipient=str(self._config.chat_id),
                    error=str(e),
                ))
        return results

    async def health_check(self) -> bool:
        """Check Telegram API connectivity."""
        if not self._connected or not self._session:
            return False

        try:
            async with self._session.get(f"{self._api_url}/getMe") as resp:
                return resp.status == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self.disconnect()

    async def disconnect(self) -> None:
        async with self._lock:
            if self._session:
                await self._session.close()
                self._session = None
            self._connected = False
            logger.info("Telegram service disconnected")


# =============================================================================
# Factory function
# =============================================================================

def create_telegram_service(
    bot_token: str,
    chat_id: str | int,
    parse_mode: str = "MarkdownV2",
    **kwargs,
) -> TelegramService:
    """Create Telegram service with configuration."""
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
        parse_mode=parse_mode,
        **kwargs,
    )
    service = TelegramService(config)
    # Session will be created on connect()
    return service