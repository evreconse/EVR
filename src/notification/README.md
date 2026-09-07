"""
EVRECONSE Notification Module.

Comprehensive notification delivery system with support for multiple channels,
retry policies, rate limiting, and queuing.

## Architecture

```
NotificationEngine (orchestration)
    ↓ uses
NotificationService (interface)
    ↓ implemented by
TelegramService, EmailService, SlackService, etc.
    ↓ uses
WebSocketClient / RestClient (transport)
RateLimiter (rate limiting)
RetryPolicy (retry logic)
Queue (bounded, priority, thread-safe)
Formatter / Templates (message formatting)
```

## Quick Start

```python
from src.notification import NotificationEngine, TelegramService

# Create engine
engine = NotificationEngine()

# Register services
telegram = TelegramService(bot_token="...", chat_id="...")
engine.register_service(telegram)

# Start engine
await engine.start()

# Send notification
result = await engine.send(
    channel="telegram",
    recipient="123456789",
    subject="Alert",
    body="Price alert: BTC > $50,000",
)

# Shutdown
await engine.shutdown()
```

## Components

| Component | Purpose |
|-----------|---------|
| `NotificationEngine` | Orchestration engine |
| `NotificationService` | Abstract service interface |
| `TelegramService` | Telegram Bot API implementation |
| `NotificationQueue` | Bounded priority queue |
| `RateLimiter` | Sliding window rate limiter |
| `RetryPolicy` | Exponential backoff with jitter |
| `Formatter` | MarkdownV2, HTML, Plain text |
| `TemplateEngine` | Jinja2-like templates |
| `Queue` | Bounded priority queue |

## Features

- **Multi-channel**: Telegram, Email, Slack, Discord, Webhook
- **Reliability**: Exponential backoff, jitter, dead letter queue
- **Rate Limiting**: Sliding window + token bucket
- **Queue**: Bounded, priority, thread-safe
- **Formatting**: MarkdownV2, HTML, Plain text
- **Templates**: Jinja2-like syntax
- **Metrics**: Built-in statistics

## Configuration

```python
from src.notification import NotificationEngine, TelegramService

engine = NotificationEngine()

telegram = TelegramService(
    bot_token="your_bot_token",
    chat_id="your_chat_id",
)

engine.register_service(telegram)
await engine.start()

await engine.send(
    channel="telegram",
    recipient="123456789",
    subject="Alert",
    body="Price alert triggered!",
    format="markdown",
    priority=1,  # high
)
```