#!/usr/bin/env python3
"""
Check for LW-001 signals on specific dates: 30 Aug, 31 Aug, 1 Sep 2026
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime, timedelta


async def check_dates():
    fetcher = BingXFetcher()

    # Get universe - filter to top 250 mid-tier (exclude top 20)
    TOP_20 = [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT', 'XRP-USDT',
        'ADA-USDT', 'DOGE-USDT', 'AVAX-USDT', 'TRX-USDT', 'DOT-USDT',
        'LINK-USDT', 'MATIC-USDT', 'SHIB-USDT', 'LTC-USDT', 'BCH-USDT',
        'PEPE-USDT', 'NEAR-USDT', 'UNI-USDT', 'APT-USDT', 'XLM-USDT'
    ]

    all_symbols = await fetcher.get_usdt_perpetual_symbols()
    universe = [s for s in all_symbols if s not in TOP_20][:250]
    print(f"Universe: {len(universe)} symbols")

    # Target dates
    target_dates = [
        datetime(2026, 8, 30, tzinfo=UTC),
        datetime(2026, 8, 31, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
    ]

    all_signals = []

    for target_date in target_dates:
        start_ms = int(target_date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        end_ms = int(target_date.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
        print(f"\n=== Checking {target_date.date()} ===")

        for symbol in universe:
            try:
                klines = await fetcher.get_klines(
                    symbol=symbol,
                    interval="15m",
                    limit=2000,
                    start_time=start_ms,
                    end_time=end_ms
                )

                if not klines or len(klines) < 21:
                    continue

                # Check each candle (need at least 20 previous for volume)
                for i in range(len(klines) - 1, 20, -1):
                    o = float(klines[i]['open'])
                    h = float(klines[i]['high'])
                    l = float(klines[i]['low'])
                    c = float(klines[i]['close'])
                    v = float(klines[i]['volume'])
                    ts = int(klines[i]['time'])
                    event_time = datetime.fromtimestamp(ts / 1000, tz=UTC)

                    prev_20 = [float(klines[j]['volume']) for j in range(i - 20, i)]

                    result = check_lw001_signal(o, h, l, c, v, prev_20)

                    if result.qualified:
                        dedup_key = f"{symbol}_{ts}"
                        all_signals.append({
                            'symbol': symbol,
                            'event_time': event_time,
                            'timestamp_ms': ts,
                            'open': o, 'high': h, 'low': l, 'close': c, 'volume': v,
                            'metrics': result.metrics,
                        })
                        print(f"  SIGNAL: {symbol} at {event_time} LW/Body={result.metrics.lw_body_ratio:.2f}x VolRatio={result.metrics.volume_ratio:.2f}x")
                        break  # One per symbol per day

            except Exception as e:
                print(f"Error {symbol}: {e}")
                continue

    print(f"\n=== TOTAL SIGNALS FOUND: {len(all_signals)} ===")
    for s in all_signals:
        m = s['metrics']
        print(f"{s['symbol']} @ {s['event_time']} LW/Body={m.lw_body_ratio:.2f}x Vol={m.volume_ratio:.2f}x")

    return all_signals


async def send_to_telegram(signals):
    """Send signals to Telegram."""
    if not signals:
        print("No signals to send")
        return

    from src.notification.telegram_service import create_telegram_service
    from src.strategy.lw001_canonical import format_lw001_telegram_message
    import os
    from uuid import uuid4

    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not configured")
        return

    telegram = create_telegram_service(bot_token=bot_token, chat_id=chat_id, parse_mode="Plain")
    await telegram.connect()

    sent = 0
    try:
        for signal in signals:
            metrics = signal["metrics"]
            event_time_str = signal["event_time"].strftime("%d.%m.%Y %H:%M UTC")

            message = format_lw001_telegram_message(
                symbol=signal["symbol"],
                event_time_utc=event_time_str,
                open_price=signal["open"],
                high_price=signal["high"],
                low_price=signal["low"],
                close_price=signal["close"],
                volume=signal["volume"],
                metrics=metrics,
            )

            class SimpleNotification:
                def __init__(self, notification_id, channel, recipient, subject, body, format, priority):
                    self._notification_id = notification_id
                    self._channel = channel
                    self._recipient = recipient
                    self._subject = subject
                    self._body = body
                    self._format = format
                    self._priority = priority

                @property
                def notification_id(self):
                    return self._notification_id

                @property
                def channel(self):
                    return self._channel

                @property
                def recipient(self):
                    return self._recipient

                @property
                def subject(self):
                    return self._subject

                @property
                def body(self):
                    return self._body

                @property
                def format(self):
                    return self._format

                @property
                def priority(self):
                    return self._priority

            notification = SimpleNotification(
                notification_id=uuid4(),
                channel="telegram",
                recipient=str(chat_id),
                subject="LW-001 Signal",
                body=message,
                format="plain",
                priority=0,
            )

            result = await telegram.send(notification)
            if result.is_success:
                print(f"Sent: {signal['symbol']} at {signal['event_time']}")
                sent += 1
            else:
                print(f"Failed: {signal['symbol']} - {result.error}")

            await asyncio.sleep(0.5)  # Rate limit

    finally:
        await telegram.disconnect()
        print(f"Done sending to Telegram. Sent {sent}/{len(signals)} signals.")


async def main():
    signals = await check_dates()

    if not signals:
        print("No signals found for these dates.")
        return

    print(f"\nFound {len(signals)} total signals. Sending to Telegram...")
    await send_to_telegram(signals)


if __name__ == "__main__":
    asyncio.run(main())