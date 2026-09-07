#!/usr/bin/env python3
"""
Send 10 historical LW-001 signals to Telegram with PASS_CHECK verification and improved formatting.

User's specification:
- Body = Open - Close (for red candles)
- Lower Wick = Close - Low (for red candles)
- Wick/Body = (Close - Low) / (Open - Close)
- Qualified = (Close < Open) AND (Wick/Body >= 2.0)
- Volume Filter: Current Volume >= 1.5x max(previous 15 volumes)
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


def check_lw001_corrected(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """Check LW-001 conditions using USER'S SPECIFIED FORMULA."""
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    body = open_price - close_price
    
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


def check_volume_filter(current_volume: float, previous_volumes: list[float]) -> tuple[bool, dict]:
    """Check if current volume is >= 1.5x max of previous 15 volumes."""
    if len(previous_volumes) < 15:
        return False, {"reason": "Not enough previous candles (need 15)"}
    
    max_previous_volume = max(previous_volumes)
    volume_ratio = current_volume / max_previous_volume if max_previous_volume > 0 else 0.0
    volume_qualified = volume_ratio >= 1.5
    
    details = {
        "current_volume": current_volume,
        "max_previous_volume": max_previous_volume,
        "volume_ratio": volume_ratio,
        "volume_qualified": volume_qualified,
    }
    
    return volume_qualified, details


def pass_check(open_price, high_price, low_price, close_price, volume, max_prev_vol) -> dict:
    """
    Perform PASS_CHECK before sending to Telegram.
    
    PASS_CHECK = red candle AND lower_wick/body >= 2.0 AND volume_ratio >= 1.5
    """
    is_red = close_price < open_price
    body = open_price - close_price
    lower_wick = close_price - low_price
    lw_condition = (lower_wick / body) >= 2.0 if body > 0 else False
    vol_condition = (volume / max_prev_vol) >= 1.5 if max_prev_vol > 0 else False
    
    pass_check = is_red and lw_condition and vol_condition
    
    return {
        "pass_check": pass_check,
        "red_candle": is_red,
        "wick_body_ratio": lower_wick / body if body > 0 else 0.0,
        "volume_ratio": volume / max_prev_vol if max_prev_vol > 0 else 0.0,
    }


async def find_signals(fetcher: BingXFetcher, universe: list[str], limit: int = 10) -> list[dict]:
    """Find exactly `limit` qualified signals on different coins."""
    print(f"\nSearching for {limit} signals on {len(universe)} coins...")
    
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
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 16:
                continue
            
            for i in range(len(klines) - 1, 15, -1):
                if len(signals) >= limit:
                    break
                
                open_price = float(klines[i]['open'])
                high_price = float(klines[i]['high'])
                low_price = float(klines[i]['low'])
                close_price = float(klines[i]['close'])
                volume = float(klines[i]['volume'])
                timestamp = int(klines[i]['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                previous_volumes = [float(klines[j]['volume']) for j in range(i - 15, i)]
                
                lw_qualified, lw_details = check_lw001_corrected(open_price, high_price, low_price, close_price)
                
                if lw_qualified:
                    vol_qualified, vol_details = check_volume_filter(volume, previous_volumes)
                    
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
                            "max_previous_volume": vol_details["max_previous_volume"],
                            "volume_ratio": vol_details["volume_ratio"],
                        })
                        seen_coins.add(symbol)
                        print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={lw_details['ratio']:.2f}x, vol_ratio={vol_details['volume_ratio']:.2f}x)")
                        break
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_msk_time(utc_time: datetime) -> str:
    """Format UTC time as MSK (UTC+3)."""
    msk_time = utc_time.replace(hour=(utc_time.hour + 3) % 24)
    return msk_time.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(utc_time: datetime) -> str:
    """Format UTC time."""
    return utc_time.strftime("%d.%m.%Y %H:%M UTC")


async def send_telegram_notifications(signals: list[dict], telegram_service: TelegramService) -> list[int]:
    """Send signals to Telegram with PASS_CHECK verification and improved formatting."""
    print(f"\nSending {len(signals)} signals to Telegram...")
    
    await telegram_service.connect()
    
    message_ids = []
    
    for i, signal in enumerate(signals, 1):
        try:
            # Perform PASS_CHECK before sending
            check = pass_check(
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
                print(f"    Wick/Body Ratio: {check['wick_body_ratio']:.2f}x")
                print(f"    Volume Ratio: {check['volume_ratio']:.2f}x")
                continue
            
            # Format times
            event_time_utc = signal["event_time"]
            event_time_msk_str = format_msk_time(event_time_utc)
            event_time_utc_str = format_utc_time(event_time_utc)
            
            # Build message with improved formatting
            body = (
                f"🔔 SIGNAL #{i}\n\n"
                f"🪙 Coin: {signal['symbol']}\n"
                f"🕐 Time: {event_time_msk_str}\n"
                f"⏱ Timeframe: M15\n\n"
                f"🔴 **CANDLE**\n"
                f"Open: {signal['open']:.4f}\n"
                f"High: {signal['high']:.4f}\n"
                f"Low: {signal['low']:.4f}\n"
                f"Close: {signal['close']:.4f}\n\n"
                f"📏 **STRUCTURE**\n"
                f"Body: {signal['body']:.4f}\n"
                f"Lower Wick: {signal['lower_wick']:.4f}\n"
                f"Upper Wick: {signal['upper_wick']:.4f}\n"
                f"Wick / Body: {signal['ratio']:.2f}x\n\n"
                f"📊 **VOLUME**\n"
                f"Current Volume: {signal['volume']:,.0f}\n"
                f"Previous 15 Max: {signal['max_previous_volume']:,.0f}\n"
                f"Volume Ratio: {signal['volume_ratio']:.2f}x\n\n"
                f"✅ **LW-001: PASS**\n\n"
                f"Conditions:\n"
                f"🔴 Red candle: YES\n"
                f"📉 Lower Wick / Body >= 2.0x: YES\n"
                f"📊 Volume >= 1.5x previous 15 max: YES"
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
