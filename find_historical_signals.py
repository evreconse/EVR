"""
Find 10 Historical LW-001 Signals

Searches historical candle data from BingX to find candles that match LW-001 strategy criteria.
Finds ONE signal per coin (10 different coins total).
Sends found signals to Telegram.
"""
import asyncio
import sys
import os
from datetime import UTC, datetime, timedelta, timezone
from typing import List, Dict, Any

# Add src to path to import production modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import MarketEvent
from models.enums import Exchange, Timeframe
from strategy.lw001_canonical import check_lw001_signal, calculate_lw001_metrics, LW001Metrics
from exchange.bingx_fetcher import BingXFetcher

# Configuration
TIMEFRAME = "15m"
TARGET_SIGNALS = 10


def load_symbols() -> List[str]:
    """Load symbols from usdt_perpetual_symbols.py"""
    try:
        with open("usdt_perpetual_symbols.py", "r") as f:
            content = f.read()
            import re
            match = re.search(r'SYMBOLS = \[(.*?)\]', content, re.DOTALL)
            if match:
                symbols_str = match.group(1)
                symbols = [s.strip().strip('"').strip("'") for s in symbols_str.split(',') if s.strip()]
                return symbols
            else:
                raise Exception("Could not parse symbols file")
    except Exception as e:
        print(f"Could not load symbols file: {e}")
        return []


def to_msk(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to MSK (UTC+3)."""
    msk_tz = timezone(timedelta(hours=3))
    return utc_dt.astimezone(msk_tz)


async def find_historical_signals():
    """Find 10 historical candles matching LW-001 strategy - ONE per coin."""
    print("=" * 80)
    print("Finding 10 Historical LW-001 Signals (1 per coin)")
    print("=" * 80)
    print(f"Target Signals: {TARGET_SIGNALS}")
    print("=" * 80)
    print()
    
    # Load symbols
    symbols = load_symbols()
    if not symbols:
        print("No symbols loaded. Exiting.")
        return
    
    print(f"Loaded {len(symbols)} symbols")
    print()
    
    # Initialize BingX fetcher
    api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
    api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    # Search for signals
    found_signals = []
    used_symbols = set()  # Track which symbols already have a signal
    
    # Search period: 30.08.2026 to present
    end_date = datetime.now(UTC)
    start_date = datetime(2026, 8, 30, tzinfo=UTC)
    
    print(f"Searching period: {start_date} to {end_date}")
    print()
    
    for symbol in symbols:
        if len(found_signals) >= TARGET_SIGNALS:
            break
        
        if symbol in used_symbols:
            continue  # Skip if we already have a signal for this symbol
        
        print(f"Searching {symbol}...")
        
        # Convert to BingX format
        bingx_symbol = symbol.replace("USDT", "-USDT")
        
        # Fetch historical data
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(end_date.timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(bingx_symbol, TIMEFRAME, limit=10000, start_time=start_time, end_time=end_time)
        except Exception as e:
            print(f"  Error fetching data: {e}")
            continue
        
        if not klines:
            print(f"  No data")
            continue
        
        print(f"  Fetched {len(klines)} candles")
        
        # Process each candle - take FIRST qualifying candle for this symbol
        for kline_idx, kline in enumerate(klines):
            if len(found_signals) >= TARGET_SIGNALS:
                break
            
            # Handle dict format
            if isinstance(kline, dict):
                timestamp = int(kline.get("time", 0)) // 1000
                open_p = float(kline.get("open", 0))
                high_p = float(kline.get("high", 0))
                low_p = float(kline.get("low", 0))
                close_p = float(kline.get("close", 0))
                volume = float(kline.get("volume", 0))
            else:
                timestamp = int(kline[0]) // 1000
                open_p = float(kline[1])
                high_p = float(kline[2])
                low_p = float(kline[3])
                close_p = float(kline[4])
                volume = float(kline[5])
            
            dt = datetime.fromtimestamp(timestamp, tz=UTC)
            
            # Calculate previous 20 volumes (from earlier candles)
            if kline_idx >= 20:
                prev_volumes = []
                for earlier_kline in klines[:kline_idx][-20:]:
                    if isinstance(earlier_kline, dict):
                        prev_volumes.append(float(earlier_kline.get("volume", 0)))
                    else:
                        prev_volumes.append(float(earlier_kline[5]))
                previous_20_volumes = prev_volumes[-20:] if len(prev_volumes) >= 20 else []
            else:
                previous_20_volumes = []
            
            # Calculate metrics using canonical function
            metrics = calculate_lw001_metrics(
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
                current_volume=volume,
                previous_20_volumes=previous_20_volumes
            )
            
            # Use canonical check with fixed thresholds
            check_result = check_lw001_signal(
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
                current_volume=volume,
                previous_20_volumes=previous_20_volumes
            )
            
            # If candle qualifies as LW-001 signal
            if check_result.qualified:
                # Check if we already have a signal for this symbol
                if symbol in used_symbols:
                    continue  # Already have a signal for this symbol
                
                # Convert to MSK
                msk_dt = to_msk(dt)
                
                signal = {
                    "symbol": symbol,
                    "date": dt.strftime("%Y-%m-%d"),
                    "time_utc": dt.strftime("%H:%M:%S UTC"),
                    "time_msk": msk_dt.strftime("%H:%M:%S MSK"),
                    "timeframe": "M15",
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "body": metrics.body_pct,
                    "lower_wick": metrics.lw_body_ratio,
                    "upper_wick": metrics.lw_range_pct,
                    "wick_body_ratio": metrics.lw_body_ratio,
                    "body_ratio": metrics.range_pct,
                    "close_position": metrics.open_to_low_pct,
                    "score": 0.0,  # Informational only
                    "explanation": f"LW-001 qualified: all conditions passed" if check_result.qualified else f"Failed: {', '.join(check_result.failed_conditions)}"
                }
                found_signals.append(signal)
                used_symbols.add(symbol)
                print(f"  [+] SIGNAL #{len(found_signals)}: {symbol} at {msk_dt.strftime('%H:%M:%S MSK')} ({dt.strftime('%H:%M:%S UTC')}), wick/body={metrics.lw_body_ratio:.2f}x")
                print(f"  [->] Moving to next symbol (used_symbols now has {len(used_symbols)} symbols)")
                break  # Take only first signal for this symbol
        
        # CRITICAL: Check if we have enough signals after processing this symbol
        if len(found_signals) >= TARGET_SIGNALS:
            print(f"  [STOP] Reached target of {TARGET_SIGNALS} signals, stopping search")
            break
        
        print()
    
    print("=" * 80)
    print(f"Found {len(found_signals)} historical signals on {len(used_symbols)} different coins")
    print("=" * 80)
    print()
    
    # Print signals
    for i, signal in enumerate(found_signals, 1):
        print(f"Signal #{i}:")
        print(f"  Coin: {signal['symbol']}")
        print(f"  Date: {signal['date']}")
        print(f"  Time: {signal['time_msk']} ({signal['time_utc']})")
        print(f"  Timeframe: {signal['timeframe']}")
        print(f"  Open: {signal['open']:.4f}")
        print(f"  High: {signal['high']:.4f}")
        print(f"  Low: {signal['low']:.4f}")
        print(f"  Close: {signal['close']:.4f}")
        print(f"  Body: {signal['body']:.2f}%")
        print(f"  Lower Wick: {signal['lower_wick']:.2f}x")
        print(f"  Upper Wick: {signal['upper_wick']:.2f}%")
        print(f"  Wick/Body: {signal['wick_body_ratio']:.2f}x")
        print(f"  Body/Range: {signal['body_ratio']:.2f}%")
        print(f"  Close Position: {signal['close_position']:.2f}%")
        print()
    
    return found_signals


async def send_to_telegram(signals: list):
    """Send found signals to Telegram."""
    print("=" * 80)
    print("Sending signals to Telegram")
    print("=" * 80)
    print()
    
    # Telegram credentials
    bot_token = "8730872028:AAEYFDMfc-Fv9Pe0x7beZL14GP4Jb7cd2_M"
    chat_id = "8307060083"
    
    # Import Telegram service
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from notification.telegram_service import TelegramService, TelegramConfig
    from uuid import uuid4
    
    # Create custom notification class with required attributes
    class CustomNotification:
        def __init__(self, subject, body, format):
            self.notification_id = uuid4()
            self.subject = subject
            self.body = body
            self.format = format
    
    # Create Telegram service
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
        parse_mode="HTML"
    )
    service = TelegramService(config)
    
    try:
        await service.connect()
        print("Connected to Telegram")
        print()
        
        for i, signal in enumerate(signals, 1):
            # Format message
            subject = f"LW-001 Historical Signal #{i}"
            body = f"""
<b>Coin:</b> {signal['symbol']}
<b>Date:</b> {signal['date']}
<b>Time:</b> {signal['time_msk']} ({signal['time_utc']})
<b>Timeframe:</b> {signal['timeframe']}

<b>OHLC:</b>
Open: {signal['open']:.4f}
High: {signal['high']:.4f}
Low: {signal['low']:.4f}
Close: {signal['close']:.4f}

<b>Candle Structure:</b>
Body: {signal['body']:.2f}%
Lower Wick: {signal['lower_wick']:.2f}x
Upper Wick: {signal['upper_wick']:.2f}%
Wick/Body: {signal['wick_body_ratio']:.2f}x
Body/Range: {signal['body_ratio']:.2f}%

<b>Score:</b> {signal['score']:.1f} (informational only)

<b>LW-001: PASS</b>
<b>Qualification:</b> Lower Wick / Body >= 1.3x ({signal['wick_body_ratio']:.2f}x >= 1.3x)
"""
            
            notification = CustomNotification(
                subject=subject,
                body=body.strip(),
                format="html"
            )
            
            result = await service.send(notification)
            print(f"Sent signal #{i}: {result.is_success}")
        
        print()
        print(f"Successfully sent {len(signals)} signals to Telegram")
        
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
    finally:
        await service.disconnect()


async def main():
    """Main function."""
    signals = await find_historical_signals()
    
    # Verify we have exactly 10 unique symbols
    if signals:
        unique_symbols = set(s['symbol'] for s in signals)
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print(f"Total signals: {len(signals)}")
        print(f"Unique symbols: {len(unique_symbols)}")
        print(f"Symbols: {list(unique_symbols)}")
        
        if len(signals) != TARGET_SIGNALS:
            print(f"ERROR: Expected {TARGET_SIGNALS} signals, got {len(signals)}")
            return
        
        if len(unique_symbols) != TARGET_SIGNALS:
            print(f"ERROR: Expected {TARGET_SIGNALS} unique symbols, got {len(unique_symbols)}")
            return
        
        print("VERIFICATION PASSED: 10 signals on 10 unique symbols")
        print()
        
        # Send to Telegram
        print("Sending to Telegram...")
        await send_to_telegram(signals)
    
    print()
    print("=" * 80)
    print("Done")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())