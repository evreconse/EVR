#!/usr/bin/env python3
"""
Real-time LW-001 Monitor

Monitors 15m candles in real-time and sends signals to Telegram when conditions are met.
Uses fixed parameters from Production Spec with dynamic CMC Universe.
"""

import sys
import json
import os
import sqlite3
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import aiohttp
import time

# Load environment variables
load_dotenv()

# Persistent deduplication database
SENT_SIGNALS_DB = Path("/home/evreconse/sent_signals.db")

def init_sent_signals_db():
    """Initialize SQLite database for sent signals with unique constraint."""
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
    finally:
        conn.close()

def claim_signal(symbol, candle_timestamp):
    """
    Atomically claim a signal for sending.
    Returns True if claim succeeded (signal not sent before), False if already sent.
    """
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        cursor = conn.cursor()
        # Atomic claim with unique constraint - fails if already exists
        cursor.execute(
            "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
            (symbol, candle_timestamp, int(time.time()))
        )
        conn.commit()
        return True  # Claim successful - not sent before
    except sqlite3.IntegrityError:
        # Already exists - duplicate prevented
        return False
    finally:
        conn.close()

def is_signal_sent(symbol, candle_timestamp):
    """Check if signal was already sent (read-only check)."""
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?",
            (symbol, candle_timestamp)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()

# Initialize database
init_sent_signals_db()

# Load sent signals into memory for fast checks (optional optimization)
def load_sent_signals_to_memory():
    """Load sent signals into memory set for fast O(1) checks."""
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, candle_timestamp FROM sent_signals")
        return set((row[0], row[1]) for row in cursor.fetchall())
    finally:
        conn.close()

# Load sent signals into memory for fast checks
SENT_SIGNALS = load_sent_signals_to_memory()


# FIXED LW-001 thresholds (Production Spec)
FIXED_THRESHOLDS = {
    "range_pct": 4.5,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 55.0,  # FIXED: was 45.0, now 55.0 per Production Spec
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}


def format_timestamp_utc(timestamp_ms):
    """Convert raw candle timestamp to UTC format ONLY."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, timezone.utc)
    utc_str = dt_utc.strftime("%d.%m.%Y %H:%M UTC")
    return utc_str


def check_red_candle(open_price, close_price):
    """Check if candle is red (Close < Open)."""
    return close_price < open_price


def check_thresholds(metrics, thresholds):
    """Check if metrics pass all thresholds. Returns (passed, results_dict)."""
    results = {}
    results["range_pct"] = metrics.range_pct >= thresholds["range_pct"]
    results["body_pct"] = metrics.body_pct >= thresholds["body_pct"]
    results["lw_body_ratio"] = metrics.lower_wick_body_ratio >= thresholds["lw_body_ratio"]
    results["lw_range_pct"] = metrics.lower_wick_range_pct >= thresholds["lw_range_pct"]
    results["open_low_pct"] = metrics.open_to_low_pct <= thresholds["open_low_pct"]
    results["volume_ratio"] = metrics.volume_ratio >= thresholds["volume_ratio"]
    
    passed = all(results.values())
    return passed, results


def calculate_avg_volume_20(candles, index):
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    if start_idx >= index:
        return 1.0
    
    volumes = []
    for i in range(start_idx, index):
        vol = float(candles[i].get('volume', candles[i].get('vol', 0)))
        volumes.append(vol)
    
    if not volumes:
        return 1.0
    
    return sum(volumes) / len(volumes)


def verify_signal_comprehensive(candle_data, avg_volume_20):
    """Comprehensive verification of a signal. Returns (passed, metrics, results_dict, reason)."""
    from LW001_METRIC_SPEC import calculate_all_metrics
    
    open_price = float(candle_data['open'])
    high_price = float(candle_data['high'])
    low_price = float(candle_data['low'])
    close_price = float(candle_data['close'])
    volume = float(candle_data['volume'])
    timestamp = candle_data.get('time', candle_data.get('timestamp', 0))
    
    # 1. Check timestamp is valid
    if timestamp <= 0:
        return False, None, None, "Invalid timestamp"
    
    # 2. Check candle is red (Close < Open)
    if not check_red_candle(open_price, close_price):
        return False, None, None, "Candle is not red (Close >= Open)"
    
    # 3. Calculate metrics
    metrics = calculate_all_metrics(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        reference_average_volume=avg_volume_20
    )
    
    # 4. Check all thresholds
    passed, results = check_thresholds(metrics, FIXED_THRESHOLDS)
    
    if not passed:
        return False, metrics, results, "Metrics do not pass thresholds"
    
    return True, metrics, results, "OK"


def format_condition_line(condition_name, threshold_str, passed):
    """Format a single condition line with PASS/FAIL."""
    status = "PASS" if passed else "FAIL"
    return f"{condition_name} {threshold_str} — {status}"


def format_telegram_message(signal, results):
    """Format signal using fixed immutable template (plain text)."""
    metrics = signal['metrics']
    symbol = signal['symbol']
    timestamp = signal['timestamp']
    
    # Build conditions lines dynamically
    conditions = [
        format_condition_line("Range", "≥ 4.5%", results["range_pct"]),
        format_condition_line("Body", "≥ 0.8%", results["body_pct"]),
        format_condition_line("LW/Body", "≥ 1.3x", results["lw_body_ratio"]),
        format_condition_line("LW/Range", "≥ 55%", results["lw_range_pct"]),
        format_condition_line("Open→Low", "≤ -2.5%", results["open_low_pct"]),
        format_condition_line("Volume Ratio", "≥ 1.5x", results["volume_ratio"]),
    ]
    
    message = f"""📌 LW-001 SIGNAL

🪙 Symbol: {symbol}

⏰ Time: {format_timestamp_utc(timestamp)}

💰 OHLCV
Open: {signal['open']:.6f}
High: {signal['high']:.6f}
Low: {signal['low']:.6f}
Close: {signal['close']:.6f}
Volume: {signal['volume']:.2f}

📊 Metrics
Range: {metrics.range_pct:.2f}%
Body: {metrics.body_pct:.2f}%
LW/Body: {metrics.lower_wick_body_ratio:.2f}x
LW/Range: {metrics.lower_wick_range_pct:.2f}%
Open→Low: {metrics.open_to_low_pct:.2f}%
Volume Ratio: {metrics.volume_ratio:.2f}x

✅ Conditions
{chr(10).join(conditions)}

✅ VALID SIGNAL"""
    
    return message


async def send_signal_to_telegram(signal, results):
    """Send a single signal to Telegram (plain text)."""
    # Support both naming conventions for compatibility
    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("ERROR: Telegram credentials not found")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = format_telegram_message(signal, results)
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        # No parse_mode = plain text
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('ok', False)
                else:
                    text = await resp.text()
                    print(f"ERROR: Telegram API returned status {resp.status}: {text}")
                    return False
    except Exception as e:
        print(f"ERROR sending to Telegram: {e}")
        return False


async def check_latest_candle(symbol, universe_provider):
    """Check the latest completed 15m candle for a symbol."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    # Fetch last 25 candles (to have 20 for volume average + 5 latest)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=6)  # 6 hours = 24 candles
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles or len(candles) < 21:
            return None
        
        # Get the most recent completed candle (second to last, as last might be incomplete)
        latest_candle = candles[-2]
        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))
        
        # Check if this candle was already processed (persistent check)
        signal_key = (symbol, timestamp)
        if signal_key in SENT_SIGNALS:
            return None
        
        # Calculate average volume from previous 20 candles
        candle_index = len(candles) - 2
        avg_volume_20 = calculate_avg_volume_20(candles, candle_index)
        
        # Verify signal
        passed, metrics, results, reason = verify_signal_comprehensive(latest_candle, avg_volume_20)
        
        if passed:
            return {
                'symbol': symbol,
                'timestamp': timestamp,
                'open': float(latest_candle['open']),
                'high': float(latest_candle['high']),
                'low': float(latest_candle['low']),
                'close': float(latest_candle['close']),
                'volume': float(latest_candle['volume']),
                'metrics': metrics,
                'results': results,
            }
        
        return None
        
    except Exception as e:
        try:
            print(f"Error checking {symbol}: {e}")
        except UnicodeEncodeError:
            print(f"Error checking {symbol}: API error (rate limit or temporary issue)")
        return None


async def monitor_symbols(universe_provider):
    """Monitor all symbols for signals."""
    print("="*100)
    print("LW-001 REAL-TIME MONITOR")
    print("="*100)
    print()
    print(f"Universe: Dynamic CMC 20-250 + BingX")
    print(f"Timeframe: 15m")
    print(f"Thresholds: Range >= 4.5%, Body >= 0.8%, LW/Body >= 1.3x, LW/Range >= 55%")
    print(f"           Open->Low <= -2.5%, Volume Ratio >= 1.5x")
    print(f"Candle direction: RED only (Close < Open)")
    print()
    print("Press Ctrl+C to stop")
    print()
    print("="*100)
    print()
    
    signals_found = 0
    signals_sent = 0
    
    try:
        while True:
            # Get fresh universe from provider
            universe = await universe_provider.get_universe()
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Checking {len(universe)} symbols...")
            
            for symbol in universe:
                signal = await check_latest_candle(symbol, universe_provider)
                
                if signal:
                    signals_found += 1
                    print(f"  SIGNAL FOUND: {signal['symbol']} at {format_timestamp_utc(signal['timestamp'])}")
                    
                    # ATOMIC CLAIM: Try to claim this signal (atomic, prevents duplicates)
                    signal_key = (signal['symbol'], signal['timestamp'])
                    if not claim_signal(signal['symbol'], signal['timestamp']):
                        print(f"  [SKIP] Already sent: {signal_key}")
                        continue
                    
                    # Add to memory set for fast subsequent checks
                    SENT_SIGNALS.add(signal_key)
                    
                    # Send to Telegram with actual PASS/FAIL results
                    success = await send_signal_to_telegram(signal, signal['results'])
                    if success:
                        signals_sent += 1
                        print(f"    [OK] Sent to Telegram")
                    else:
                        print(f"    [ERROR] Failed to send to Telegram - rolling back claim")
                        # Rollback: Remove from DB and memory since send failed
                        conn = sqlite3.connect(SENT_SIGNALS_DB)
                        try:
                            conn.execute(
                                "DELETE FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?",
                                (signal['symbol'], signal['timestamp'])
                            )
                            conn.commit()
                        finally:
                            conn.close()
                        SENT_SIGNALS.discard(signal_key)
            
            print(f"  Total signals found: {signals_found}, Sent: {signals_sent}")
            print()
            
            # Wait until next 15m candle completes
            now = datetime.now(timezone.utc)
            minutes = now.minute
            seconds = now.second
            
            # Calculate time until next 15m mark (00, 15, 30, 45)
            next_15m = ((minutes // 15) + 1) * 15
            if next_15m >= 60:
                next_15m = 0
                wait_minutes = 60 - minutes + next_15m - (seconds / 60)
            else:
                wait_minutes = next_15m - minutes - (seconds / 60)
            
            # Wait 1 minute after candle completion to ensure data is available
            wait_seconds = int(wait_minutes * 60) + 60
            
            print(f"Waiting {wait_seconds} seconds until next check...")
            print()
            await asyncio.sleep(wait_seconds)
            
    except KeyboardInterrupt:
        print()
        print("="*100)
        print("MONITOR STOPPED")
        print("="*100)
        print()
        print(f"Total signals found: {signals_found}")
        print(f"Total signals sent: {signals_sent}")
        print()


async def main():
    """Main function."""
    # Initialize universe provider
    from src.data_provider.universe_provider import get_universe_provider
    universe_provider = get_universe_provider()
    await universe_provider.initialize()
    
    await monitor_symbols(universe_provider)


if __name__ == "__main__":
    asyncio.run(main())