#!/usr/bin/env python3
"""
Find all LW-001 signals from the last 5 days and send to Telegram.
"""

import asyncio
import sys
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

# Add project paths
sys.path.insert(0, "src")
sys.path.insert(0, ".")

load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal, format_lw001_telegram_message
from src.notification.telegram_service import create_telegram_service, TelegramConfig


# Load CoinMarketCap mid-tier symbols
def load_cmc_symbols(filepath="coinmarketcap_mid_tier_symbols.txt"):
    """Load symbols from CoinMarketCap file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


async def find_signals_last_5days(fetcher: BingXFetcher, universe: list[str], days: int = 5) -> list[dict]:
    """
    Find all LW-001 qualified signals in the last N days.
    
    Args:
        fetcher: BingX fetcher instance
        universe: List of symbols to search
        days: Number of days to look back
        
    Returns:
        List of qualified signal dictionaries
    """
    print(f"\nSearching for signals in the last {days} days on {len(universe)} coins...")
    
    # Search period: last N days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=days)).timestamp() * 1000)
    
    signals = []
    seen_signals = set()  # For deduplication: symbol + timestamp
    
    for idx, symbol in enumerate(universe):
        if idx % 50 == 0:
            print(f"Progress: {idx}/{len(universe)} symbols processed...")
        
        try:
            # Fetch M15 candles for the period
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=2000,  # Max candles for the period
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 21:
                continue
            
            # Check each candle (newest first, need at least 20 previous for volume)
            for i in range(len(klines) - 1, 20, -1):
                # Parse kline data
                open_price = float(klines[i]['open'])
                high_price = float(klines[i]['high'])
                low_price = float(klines[i]['low'])
                close_price = float(klines[i]['close'])
                volume = float(klines[i]['volume'])
                timestamp = int(klines[i]['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                # Get previous 20 volumes for volume ratio
                previous_20_volumes = [float(klines[j]['volume']) for j in range(i - 20, i)]
                
                # Check LW-001 conditions with CANONICAL check
                result = check_lw001_signal(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    current_volume=volume,
                    previous_20_volumes=previous_20_volumes
                )
                
                if result.qualified:
                    # Deduplication key: symbol + timestamp
                    dedup_key = f"{symbol}_{timestamp}"
                    if dedup_key in seen_signals:
                        continue
                    seen_signals.add(dedup_key)
                    
                    signals.append({
                        "symbol": symbol,
                        "event_time": event_time,
                        "timestamp_ms": timestamp,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "metrics": result.metrics,
                        "failed_conditions": result.failed_conditions,
                    })
                    print(f"Signal found: {symbol} at {event_time.strftime('%Y-%m-%d %H:%M UTC')} (LW/Body={result.metrics.lw_body_ratio:.2f}x, VolRatio={result.metrics.volume_ratio:.2f}x)")
                    break  # Only one signal per candle per symbol
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nTotal signals found: {len(signals)}")
    return signals


def format_utc_time(utc_time: datetime) -> str:
    """Format UTC time for display."""
    return utc_time.strftime("%d.%m.%Y %H:%M UTC")


async def send_signals_to_telegram(signals: list[dict]):
    """Send all signals to Telegram."""
    if not signals:
        print("No signals to send.")
        return
    
    # Create Telegram service
    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID")
    
    if not bot_token or not chat_id:
        print("ERROR: Telegram credentials not configured!")
        return
    
    telegram_service = create_telegram_service(
        bot_token=bot_token,
        chat_id=chat_id,
        parse_mode="Plain",
    )
    
    await telegram_service.connect()
    
    print(f"\nSending {len(signals)} signals to Telegram...")
    
    sent_count = 0
    for signal in signals:
        metrics = signal["metrics"]
        event_time_str = format_utc_time(signal["event_time"])
        
        # Format message using canonical formatter
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
        
        try:
            # Create a simple notification object that matches the Notification interface
            from uuid import uuid4
            
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
            
            result = await telegram_service.send(notification)
            
            if result.is_success:
                sent_count += 1
                print(f"Sent: {signal['symbol']} at {format_utc_time(signal['event_time'])}")
            else:
                print(f"Failed: {signal['symbol']} - {result.error}")
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Error sending {signal['symbol']}: {e}")
    
    await telegram_service.disconnect()
    print(f"\nSuccessfully sent {sent_count}/{len(signals)} signals to Telegram.")


async def main():
    """Main execution."""
    load_dotenv()
    
    print("=" * 80)
    print("LW-001 SIGNAL SEARCH - LAST 5 DAYS")
    print("=" * 80)
    
    # Load CoinMarketCap mid-tier symbols
    print("Loading CoinMarketCap mid-tier symbols...")
    cmc_symbols = load_cmc_symbols("coinmarketcap_mid_tier_symbols.txt")
    
    if not cmc_symbols:
        print("ERROR: No CoinMarketCap symbols found. Run fetch_coinmarketcap_symbols.py first.")
        return
    
    print(f"Loaded {len(cmc_symbols)} CoinMarketCap mid-tier symbols")
    
    # Initialize BingX fetcher
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    # Get BingX available symbols and filter
    print("Fetching available BingX USDT perpetual symbols...")
    bingx_symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f"BingX has {len(bingx_symbols)} USDT perpetual symbols")
    
    # Filter CMC symbols to only those available on BingX
    bingx_set = set(bingx_symbols)
    universe = [s for s in cmc_symbols if s in bingx_set]
    print(f"Filtered universe: {len(universe)} symbols available on BingX")
    
    if not universe:
        print("ERROR: No matching symbols between CMC and BingX!")
        return
    
    # Find signals in last 5 days
    signals = await find_signals_last_5days(fetcher, universe, days=5)
    
    if not signals:
        print("No signals found in the last 5 days.")
        return
    
    # Sort by time (newest first)
    signals.sort(key=lambda x: x["timestamp_ms"], reverse=True)
    
    print(f"\nTotal unique signals found: {len(signals)}")
    
    # Show summary
    print("\n--- SIGNAL SUMMARY ---")
    for i, signal in enumerate(signals, 1):
        m = signal["metrics"]
        time_str = format_utc_time(signal["event_time"])
        print(f"{i}. {signal['symbol']} @ {time_str} | "
              f"LW/Body={m.lw_body_ratio:.2f}x | "
              f"VolRatio={m.volume_ratio:.2f}x | "
              f"Range={m.range_pct:.1f}% | "
              f"Body={m.body_pct:.1f}% | "
              f"LW/Range={m.lw_range_pct:.1f}% | "
              f"Open->Low={m.open_to_low_pct:.1f}%")
    
    # Send to Telegram
    print("\n--- SENDING TO TELEGRAM ---")
    await send_signals_to_telegram(signals)
    
    print("\n=== COMPLETED ===")


if __name__ == "__main__":
    asyncio.run(main())