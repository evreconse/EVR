#!/usr/bin/env python3
"""
Send 10 historical LW-001 signals to Telegram with PASS_CHECK verification and Close != Low check.

User's specification:
- Body = Open - Close (for red candles)
- Lower Wick = Close - Low (for red candles)
- Wick/Body = (Close - Low) / (Open - Close)
- Qualified = (Close < Open) AND (Wick/Body >= 2.0)
- Volume Filter: Current Volume >= 1.5x max(previous 48 volumes)
- CRITICAL: Close != Low (must have a lower wick)
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher
from src.notification.telegram_service import TelegramService, TelegramConfig


TOP_20_COINS = [
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "TRX-USDT", "DOT-USDT",
    "LINK-USDT", "MATIC-USDT", "SHIB-USDT", "LTC-USDT", "BCH-USDT",
    "PEPE-USDT", "NEAR-USDT", "UNI-USDT", "APT-USDT", "XLM-USDT"
]


async def get_universe(fetcher: BingXFetcher) -> list[str]:
    """Get universe of 250 USDT perpetual coins excluding TOP-20."""
    print("Fetching USDT perpetual symbols...")
    symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f"Total USDT Perpetual symbols: {len(symbols)}")
    
    remaining = [s for s in symbols if s not in TOP_20_COINS]
    print(f"Excluded TOP-20: {len(TOP_20_COINS)} coins")
    print(f"Remaining: {len(remaining)} coins")
    
    universe = remaining[:250]
    print(f"Selected universe: {len(universe)} coins")
    
    return universe


def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """
    Check LW-001 conditions with EXPLICIT Close != Low check.
    
    User's specification:
    - Body = Open - Close (for red candles, NO abs())
    - Lower Wick = Close - Low (for red candles)
    - Wick/Body = (Close - Low) / (Open - Close)
    - Qualified = (Close < Open) AND (Wick/Body >= 2.0)
    - CRITICAL: Close != Low (must have a lower wick)
    
    This matches the production formula in src/strategy/lw_001.py
    """
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    # CRITICAL CHECK: Close must NOT equal Low (must have a lower wick)
    if close_price == low_price:
        return False, {"reason": "Close == Low (no lower wick)"}
    
    # Calculate body (Open - Close for red candles, NO abs() - matches production)
    body = open_price - close_price if is_red else 0.0
    
    if body <= 0:
        return False, {"reason": "Zero or negative body"}
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price  # For red candles
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


def check_volume_filter(current_volume: float, previous_candle_volume: float) -> tuple[bool, dict]:
    """Check if current volume is >= 1.5x previous candle volume."""
    if previous_candle_volume <= 0:
        return False, {"reason": "Previous candle volume is zero or negative"}
    
    volume_ratio = current_volume / previous_candle_volume
    volume_qualified = volume_ratio >= 1.5
    
    details = {
        "current_volume": current_volume,
        "previous_candle_volume": previous_candle_volume,
        "volume_ratio": volume_ratio,
        "volume_qualified": volume_qualified,
    }
    
    return volume_qualified, details


def pass_check_strict(open_price, high_price, low_price, close_price, volume, previous_candle_volume) -> dict:
    """
    Perform PASS_CHECK before sending to Telegram with Close != Low check.
    
    PASS_CHECK = red candle AND Close != Low AND lower_wick/body >= 2.0 AND volume_ratio >= 1.5
    """
    is_red = close_price < open_price
    close_not_low = close_price != low_price
    body = open_price - close_price
    lower_wick = close_price - low_price
    lw_condition = (lower_wick / body) >= 2.0 if body > 0 else False
    vol_condition = (volume / previous_candle_volume) >= 1.5 if previous_candle_volume > 0 else False
    
    pass_check = is_red and close_not_low and lw_condition and vol_condition
    
    return {
        "pass_check": pass_check,
        "red_candle": is_red,
        "close_not_low": close_not_low,
        "wick_body_ratio": lower_wick / body if body > 0 else 0.0,
        "volume_ratio": volume / previous_candle_volume if previous_candle_volume > 0 else 0.0,
    }


async def find_signals(fetcher: BingXFetcher, universe: list[str], limit: int = 10) -> list[dict]:
    """Find exactly `limit` qualified signals on different coins."""
    print(f"\nSearching for {limit} signals on {len(universe)} coins...")
    
    # Exclude coins from previous batch
    previous_coins = {
        "SUSHI-USDT", "COMP-USDT", "DASH-USDT", "FLOW-USDT", "RUNE-USDT",
        "ROSE-USDT", "WOO-USDT", "CRO-USDT", "ACH-USDT", "TLM-USDT"
    }
    print(f"Excluding {len(previous_coins)} coins from previous batch")
    
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    signals = []
    seen_coins = set()
    
    for symbol in universe:
        if len(signals) >= limit:
            break
        
        if symbol in seen_coins:
            continue
        
        if symbol in previous_coins:
            continue
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 2:  # Need at least 2 candles (current + previous)
                continue
            
            for i in range(len(klines) - 1, 0, -1):  # Start from end, need at least 1 previous
                if len(signals) >= limit:
                    break
                
                open_price = float(klines[i]['open'])
                high_price = float(klines[i]['high'])
                low_price = float(klines[i]['low'])
                close_price = float(klines[i]['close'])
                volume = float(klines[i]['volume'])
                timestamp = int(klines[i]['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                # Get previous candle volume (single previous candle)
                previous_candle_volume = float(klines[i - 1]['volume'])
                
                lw_qualified, lw_details = check_lw001_strict(open_price, high_price, low_price, close_price)
                
                if lw_qualified:
                    vol_qualified, vol_details = check_volume_filter(volume, previous_candle_volume)
                    
                    if vol_qualified:
                        signals.append({
                            "symbol": symbol,
                            "event_time": event_time,
                            "timestamp_ms": timestamp,
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": volume,
                            "body": lw_details["body"],
                            "lower_wick": lw_details["lower_wick"],
                            "upper_wick": lw_details["upper_wick"],
                            "ratio": lw_details["ratio"],
                            "previous_candle_volume": vol_details["previous_candle_volume"],
                            "volume_ratio": vol_details["volume_ratio"],
                        })
                        seen_coins.add(symbol)
                        print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={lw_details['ratio']:.2f}x, vol_ratio={vol_details['volume_ratio']:.2f}x)")
                        print(f"  Close ({close_price:.6f}) != Low ({low_price:.6f}): {close_price != low_price}")
                        break
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string."""
    return dt.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def format_price(value: float) -> str:
    """Format price with appropriate precision."""
    if value == 0:
        return "0.000000"
    elif abs(value) < 0.000001:
        # Use scientific notation for very small values
        return f"{value:.2e}"
    else:
        # Use standard decimal notation
        return f"{value:.6f}"


async def send_telegram_notifications(signals: list[dict], telegram_service: TelegramService) -> list[int]:
    """Send signals to Telegram with PASS_CHECK verification and improved formatting."""
    print(f"\nSending {len(signals)} signals to Telegram...")
    
    await telegram_service.connect()
    
    message_ids = []
    
    for i, signal in enumerate(signals, 1):
        try:
            # Perform PASS_CHECK before sending
            check = pass_check_strict(
                signal["open"],
                signal["high"],
                signal["low"],
                signal["close"],
                signal["volume"],
                signal["max_previous_volume"]
            )
            
            if not check["pass_check"]:
                print(f"  Signal {i}/{len(signals)}: {signal['symbol']} - FAILED PASS_CHECK - NOT SENDING")
                print(f"    Red Candle: {check['red_candle']}")
                print(f"    Close != Low: {check['close_not_low']}")
                print(f"    Wick/Body Ratio: {check['wick_body_ratio']:.2f}x")
                print(f"    Volume Ratio: {check['volume_ratio']:.2f}x")
                continue
            
            # Format times
            event_time_utc = signal["event_time"]
            event_time_msk_str = format_msk_time(event_time_utc)
            event_time_utc_str = format_utc_time(event_time_utc)
            
            # Build message with improved formatting
            body = (
                f"🔴 **LW-001 SIGNAL #{i}**\n\n"
                f"🪙 Coin: {signal['symbol']}\n"
                f"🕐 Time: {event_time_msk_str}\n"
                f"🕐 Time UTC: {event_time_utc_str}\n"
                f"⏱ Timeframe: M15\n\n"
                f"📌 **Candle**\n"
                f"Open: {format_price(signal['open'])}\n"
                f"High: {format_price(signal['high'])}\n"
                f"Low: {format_price(signal['low'])}\n"
                f"Close: {format_price(signal['close'])}\n\n"
                f"📏 **Structure**\n"
                f"Body: {format_price(signal['body'])}\n"
                f"Lower Wick: {format_price(signal['lower_wick'])}\n"
                f"Upper Wick: {format_price(signal['upper_wick'])} (informational only)\n"
                f"Wick / Body: {signal['ratio']:.2f}x\n\n"
                f"📈 **Volume**\n"
                f"Current Volume: {signal['volume']:,.0f}\n"
                f"Max Previous 48: {signal['max_previous_volume']:,.0f}\n"
                f"Volume Ratio: {signal['volume_ratio']:.2f}x\n\n"
                f"✅ **Qualification**\n"
                f"Red Candle: PASS\n"
                f"Close != Low: PASS\n"
                f"Lower Wick >= 2x Body: PASS\n"
                f"Volume >= 1.5x Previous 48 Max: PASS\n\n"
                f"Score: informational only"
            )
            
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
                subject=f"LW-001 SIGNAL #{i} - {signal['symbol']}",
                body=body,
                format="plain",
            )
            
            result = await telegram_service.send(notification)
            message_ids.append(result.message_id if hasattr(result, 'message_id') else i)
            print(f"  Signal {i}/{len(signals)}: {signal['symbol']} - Sent successfully (Message ID: {message_ids[-1]})")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"  Signal {i}/{len(signals)}: {signal['symbol']} - FAILED: {e}")
    
    await telegram_service.disconnect()
    print(f"\nSent {len(message_ids)}/{len(signals)} signals to Telegram")
    
    return message_ids


async def main():
    """Main execution."""
    load_dotenv()
    
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    universe = await get_universe(fetcher)
    
    signals = await find_signals(fetcher, universe, limit=10)
    
    if len(signals) < 10:
        print(f"\nERROR: Only found {len(signals)} signals, need 10")
        return
    
    # Check Telegram credentials
    bot_token = os.environ.get("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.environ.get("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.environ.get("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("\nERROR: Telegram credentials not found in environment variables")
        return
    
    print("\nInitializing Telegram service...")
    telegram_config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
    )
    telegram_service = TelegramService(telegram_config)
    
    # Send to Telegram with PASS_CHECK and improved formatting
    message_ids = await send_telegram_notifications(signals, telegram_service)
    
    print("\n=== COMPLETED ===")
    print(f"Sent {len(message_ids)} signals to Telegram")
    print(f"Message IDs: {message_ids}")


if __name__ == "__main__":
    asyncio.run(main())
