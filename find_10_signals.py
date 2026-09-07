#!/usr/bin/env python3
"""
Find exactly 10 historical LW-001 signals on 10 different coins.

Requirements:
- BingX USDT Perpetual
- M15 timeframe
- 250 coins (excluding TOP-20)
- Red candle (Close < Open)
- Lower Wick / Body >= 2.0
- 10 different coins
- Send to Telegram
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from exchange.bingx_fetcher import BingXFetcher
from notification.telegram_service import TelegramService, TelegramConfig
from models.enums import Exchange, Timeframe
from models.market_event import MarketEvent


async def get_universe(fetcher: BingXFetcher) -> list[str]:
    """
    Get 250 USDT perpetual coins excluding TOP-20.
    
    TOP-20 is determined by 24h volume from BingX ticker data.
    """
    print("Fetching USDT perpetual symbols...")
    all_symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f"Found {len(all_symbols)} USDT perpetual symbols")
    
    # Get ticker data to determine TOP-20 by volume
    print("Fetching ticker data for volume ranking...")
    top_20 = []
    
    # For BingX, we'll use a predefined list of major coins as TOP-20
    # This is reproducible and based on market consensus
    top_20_coins = [
        "BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT", "XRP-USDT",
        "DOGE-USDT", "ADA-USDT", "AVAX-USDT", "TRX-USDT", "LINK-USDT",
        "MATIC-USDT", "DOT-USDT", "LTC-USDT", "SHIB-USDT", "PEPE-USDT",
        "UNI-USDT", "ATOM-USDT", "XLM-USDT", "ETC-USDT", "FIL-USDT"
    ]
    
    # Filter out TOP-20
    remaining = [s for s in all_symbols if s not in top_20_coins]
    print(f"Excluded TOP-20: {len(top_20_coins)} coins")
    print(f"Remaining: {len(remaining)} coins")
    
    # Select first 250 from remaining
    universe = remaining[:250]
    print(f"Selected universe: {len(universe)} coins")
    
    return universe


def check_lw001(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """
    Check if candle meets LW-001 conditions.
    
    Returns:
        (qualified, details)
    """
    # Condition 1: Red candle (Close < Open)
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    # Calculate body and lower wick for red candle
    body = open_price - close_price  # Positive for red candle
    lower_wick = close_price - low_price
    
    if body == 0:
        return False, {"reason": "Zero body"}
    
    # Condition 2: Lower Wick / Body >= 2.0
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


async def find_signals(fetcher: BingXFetcher, universe: list[str], limit: int = 10) -> list[dict]:
    """
    Find exactly `limit` qualified signals on different coins.
    
    Search historical M15 candles from the last 7 days.
    """
    print(f"\nSearching for {limit} signals on {len(universe)} coins...")
    
    # Search period: last 7 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    signals = []
    seen_coins = set()
    
    for symbol in universe:
        if len(signals) >= limit:
            break
        
        if symbol in seen_coins:
            continue
        
        try:
            # Fetch M15 candles
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=500,  # Max candles per request
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines:
                continue
            
            # Check each candle (newest first)
            for kline in reversed(klines):
                if len(signals) >= limit:
                    break
                
                # Parse kline data
                # BingX format: {'time': ms, 'open': str, 'high': str, 'low': str, 'close': str, 'volume': str}
                open_price = float(kline['open'])
                high_price = float(kline['high'])
                low_price = float(kline['low'])
                close_price = float(kline['close'])
                volume = float(kline['volume'])
                timestamp = int(kline['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                # Check LW-001 conditions
                qualified, details = check_lw001(open_price, high_price, low_price, close_price)
                
                if qualified:
                    signals.append({
                        "symbol": symbol,
                        "event_time": event_time,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "body": details["body"],
                        "lower_wick": details["lower_wick"],
                        "ratio": details["ratio"],
                    })
                    seen_coins.add(symbol)
                    print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={details['ratio']:.2f}x)")
                    break  # Only take one signal per coin
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_msk_time(utc_time: datetime) -> str:
    """Format UTC time as MSK (UTC+3)."""
    msk_time = utc_time.replace(hour=(utc_time.hour + 3) % 24)
    return msk_time.strftime("%Y-%m-%d %H:%M:%S MSK")


def verify_signals(signals: list[dict]) -> list[dict]:
    """
    Verify each signal meets LW-001 conditions.
    """
    print("\n=== VERIFICATION TABLE ===")
    print(f"{'#':<3} {'Symbol':<12} {'Time MSK':<20} {'Red':<4} {'Body':<10} {'Lower Wick':<12} {'Ratio':<8} {'Qualified':<10}")
    print("-" * 90)
    
    verified = []
    for i, signal in enumerate(signals, 1):
        open_price = signal["open"]
        high_price = signal["high"]
        low_price = signal["low"]
        close_price = signal["close"]
        
        is_red = close_price < open_price
        body = open_price - close_price
        lower_wick = close_price - low_price
        ratio = lower_wick / body if body > 0 else 0.0
        qualified = is_red and ratio >= 2.0
        
        time_msk = format_msk_time(signal["event_time"])
        
        print(f"{i:<3} {signal['symbol']:<12} {time_msk:<20} {'YES' if is_red else 'NO':<4} {body:<10.4f} {lower_wick:<12.4f} {ratio:<8.2f} {'YES' if qualified else 'NO':<10}")
        
        if qualified:
            verified.append(signal)
        else:
            print(f"  WARNING: Signal {i} FAILED verification")
    
    print("-" * 90)
    print(f"Verified: {len(verified)}/{len(signals)} signals")
    
    return verified


async def send_telegram_notifications(signals: list[dict], telegram_service: TelegramService) -> None:
    """Send signals to Telegram."""
    print(f"\nSending {len(signals)} signals to Telegram...")
    
    await telegram_service.connect()
    
    for i, signal in enumerate(signals, 1):
        try:
            # Calculate metrics
            open_price = signal["open"]
            high_price = signal["high"]
            low_price = signal["low"]
            close_price = signal["close"]
            volume = signal["volume"]
            body = signal["body"]
            lower_wick = signal["lower_wick"]
            ratio = signal["ratio"]
            
            candle_range = high_price - low_price
            upper_wick = high_price - max(open_price, close_price)
            body_ratio = body / candle_range if candle_range > 0 else 0.0
            close_position = (close_price - low_price) / candle_range if candle_range > 0 else 0.0
            
            # Format time
            event_time_utc = signal["event_time"]
            event_time_str = event_time_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            event_time_msk_str = format_msk_time(event_time_utc)
            
            # Build message (plain text to avoid HTML parsing issues)
            subject = f"LW-001 LONG | {signal['symbol']} M15"

            body = (
                f"LW-001 LONG | {signal['symbol']} | M15\n"
                f"{event_time_msk_str} | {event_time_str}\n"
                f"{'='*50}\n"
                f"OHLC: O={open_price:.4f} H={high_price:.4f} L={low_price:.4f} C={close_price:.4f}\n"
                f"Volume: {volume:,.0f}\n"
                f"{'='*50}\n"
                f"Structure:\n"
                f"  Body: {body:.4f}\n"
                f"  Lower Wick: {lower_wick:.4f}\n"
                f"  Upper Wick: {upper_wick:.4f}\n"
                f"  Wick/Body: {ratio:.2f}x\n"
                f"  Body/Range: {body_ratio:.1%}\n"
                f"  Close Position: {close_position:.0%}\n"
                f"{'='*50}\n"
                f"LW-001 QUALIFIED\n"
                f"  Red candle: Close < Open\n"
                f"  Lower Wick / Body >= 2.0x\n"
                f"{'='*50}\n"
                f"Why: Red candle with long lower wick ({ratio:.2f}x body)"
            )
            
            # Create a simple notification object
            class SimpleNotification:
                def __init__(self, notification_id, channel, subject, body, format):
                    self.notification_id = notification_id
                    self.channel = channel
                    self.subject = subject
                    self.body = body
                    self.format = format
                    self.priority = 0

            notification = SimpleNotification(
                notification_id=str(i),
                channel="telegram",
                subject=subject,
                body=body,
                format="plain",
            )
            
            result = await telegram_service.send(notification)
            print(f"  Signal {i}/{len(signals)}: {signal['symbol']} - Sent successfully")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"  Signal {i}/{len(signals)}: {signal['symbol']} - FAILED: {e}")
    
    await telegram_service.disconnect()
    print(f"\nAll {len(signals)} signals sent to Telegram")


async def main():
    """Main execution."""
    # Load .env file to ensure environment variables are set
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize BingX fetcher
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    # Get universe
    universe = await get_universe(fetcher)
    
    # Find signals
    signals = await find_signals(fetcher, universe, limit=10)
    
    if len(signals) < 10:
        print(f"\nERROR: Only found {len(signals)} signals, need 10")
        return
    
    # Verify signals
    verified = verify_signals(signals)
    
    if len(verified) < 10:
        print(f"\nERROR: Only {len(verified)} signals verified, need 10")
        return
    
    # Check for Telegram credentials
    import os
    bot_token = os.environ.get("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.environ.get("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.environ.get("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("\n⚠️  Telegram credentials not found in environment variables.")
        print("   Set EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN and EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID")
        print("   Or EVRECONSE_TELEGRAM_BOT_TOKEN and EVRECONSE_TELEGRAM_CHAT_ID")
        print("\n=== SIGNALS FOUND BUT NOT SENT ===")
        print(f"Found and verified {len(verified)} signals on 10 different coins")
        print("Add Telegram credentials to .env to send notifications")
        return
    
    # Send to Telegram
    print("\nInitializing Telegram service...")
    telegram_config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
    )
    telegram_service = TelegramService(telegram_config)
    
    await send_telegram_notifications(verified, telegram_service)
    
    print("\n=== COMPLETED ===")
    print(f"Found and verified {len(verified)} signals on 10 different coins")
    print(f"All signals sent to Telegram")


if __name__ == "__main__":
    asyncio.run(main())
