#!/usr/bin/env python3
"""
Real-time LW-001 Monitor

Monitors 15m candles in real-time and sends signals to Telegram when conditions are met.
Uses fixed parameters from Production Spec with dynamic BingX Universe (ALL active USDT Perpetuals).
"""

import sys
import json
import os
import sqlite3
import platform
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

# ===== AUTO-TRADER INTEGRATION =====
# Import auto-trader components
try:
    from src.exchange.bingx_trader import AutoTraderManager
    AUTO_TRADER_AVAILABLE = True
except ImportError:
    AUTO_TRADER_AVAILABLE = False
    print("[WARNING] Auto-trader module not available, trading disabled")
# =====================================

# Persistent deduplication database
# Use local path on Windows, production path on Linux
import platform
if platform.system() == "Windows":
    SENT_SIGNALS_DB = Path("C:/EVRECONSE_PROJECT/sent_signals.db")
else:
    SENT_SIGNALS_DB = Path("/home/evreconse/sent_signals.db")

def init_sent_signals_db():
    """Initialize SQLite database for sent signals with unique constraint."""
    try:
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
            print(f"[DB INIT] Database initialized at {SENT_SIGNALS_DB}, table created/verified")
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB INIT ERROR] Failed to initialize database: {e}")
        raise

def claim_signal(symbol, candle_timestamp):
    """
    Atomically claim a signal for sending.
    Returns True if claim succeeded (signal not sent before), False if already sent.
    """
    try:
        conn = sqlite3.connect(SENT_SIGNALS_DB)
        try:
            cursor = conn.cursor()
            # Atomic claim with unique constraint - fails if already exists
            cursor.execute(
                "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
                (symbol, candle_timestamp, int(time.time()))
            )
            conn.commit()
            print(f"[CLAIM] SUCCESS: Claimed signal for {symbol} at {candle_timestamp}")
            return True  # Claim successful - not sent before
        except sqlite3.IntegrityError:
            # Already exists - duplicate prevented
            print(f"[CLAIM] DUPLICATE: Signal already exists for {symbol} at {candle_timestamp}")
            return False
        finally:
            conn.close()
    except Exception as e:
        print(f"[CLAIM ERROR] Failed to claim signal for {symbol}: {e}")
        raise

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
    # Volume Ratio REMOVED - not part of LW-001 strategy
    
    passed = all(results.values())
    return passed, results


def verify_signal_comprehensive(candle_data, avg_volume_20):
    """Comprehensive verification of a signal (OLD - uses avg 20). Returns (passed, metrics, results_dict, reason)."""
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


def verify_signal_comprehensive_new(candle_data):
    """Comprehensive verification of a signal (NEW - Volume Ratio removed). Returns (passed, metrics, results_dict, reason)."""
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
    
    # 3. Calculate metrics (Volume Ratio removed)
    metrics = calculate_all_metrics(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        volume_3_candles_ago=0.0  # Not used, kept for compatibility
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
        # Volume Ratio REMOVED - not part of LW-001 strategy
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
# Volume Ratio REMOVED - not part of LW-001 strategy

✅ Conditions
{chr(10).join(conditions)}

✅ VALID SIGNAL"""
    
    return message


async def send_signal_to_telegram(signal, results):
    """Send a single signal to Telegram (plain text) with explicit UTF-8 encoding."""
    # Support both naming conventions for compatibility
    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    print(f"  [TELEGRAM] Preparing to send: bot_token={'SET' if bot_token else 'MISSING'}, chat_id={'SET' if chat_id else 'MISSING'}")
    
    if not bot_token or not chat_id:
        print("  [TELEGRAM ERROR] Telegram credentials not found")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = format_telegram_message(signal, results)
    
    # PRE-SEND DIAGNOSTIC: Show text representation to debug UTF-8 issues
    print(f"  [TELEGRAM PRE-SEND] text_repr={repr(message[:200])}... len={len(message)} chars")
    
    # Use explicit UTF-8 encoding with form data to ensure emojis are preserved
    payload = {
        "chat_id": chat_id,
        "text": message,
        # No parse_mode = plain text
    }
    
    try:
        print(f"  [TELEGRAM] Sending request to Telegram API...")
        import json
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(payload_bytes))
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload_bytes, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ok = data.get('ok', False)
                    if ok:
                        msg_id = data.get('result', {}).get('message_id')
                        print(f"  [TELEGRAM SUCCESS] Message sent successfully, message_id={msg_id}")
                    else:
                        print(f"  [TELEGRAM ERROR] API returned ok=false: {data}")
                    return ok
                else:
                    text = await resp.text()
                    print(f"  [TELEGRAM ERROR] API returned status {resp.status}: {text}")
                    return False
    except Exception as e:
        print(f"  [TELEGRAM ERROR] Exception: {type(e).__name__}: {e}")
        return False


def get_last_completed_candle(candles):
    """
    Identify the last completed candle from the fetched candles.
    
    BingX returns candles in chronological order (oldest first).
    The last candle may be incomplete (current period).
    We need to find the last COMPLETED candle.
    
    A candle is complete if its close time (timestamp + 15min) <= current time.
    """
    if not candles or len(candles) < 2:
        return None, None
    
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    
    # Check from the end backwards to find the last completed candle
    for i in range(len(candles) - 1, -1, -1):
        candle = candles[i]
        timestamp = candle.get('time', candle.get('timestamp', 0))
        if timestamp <= 0:
            continue
        # Candle close time = timestamp + 15 minutes (in ms)
        candle_close_time = timestamp + (15 * 60 * 1000)
        if candle_close_time <= now_ms:
            # This candle is complete
            return candle, i
    
    return None, None


async def check_latest_candle(symbol, universe_provider):
    """Check the latest completed 15m candle for a symbol."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    # Fetch last 15 candles (need at least 4 for N/N-3: N, N-1, N-2, N-3, plus extra for closed candle detection)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=4)  # 4 hours = 16 candles
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles or len(candles) < 2:  # Need at least 2 candles for closed candle logic
            return None, "insufficient_candles"
        
        # Get the last completed candle using timestamp-based logic
        latest_candle, candle_index = get_last_completed_candle(candles)
        
        if latest_candle is None:
            return None, "no_completed_candle"
            
        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))
        
        # Check if this candle was already processed (persistent check)
        signal_key = (symbol, timestamp)
        if signal_key in SENT_SIGNALS:
            return None, "already_processed"
        
        # Need at least 1 completed candle before current (not needed anymore since Volume Ratio removed)
        # but keep for safety
        if candle_index < 1:
            return None, "insufficient_history"
        
        # Verify signal (Volume Ratio removed)
        passed, metrics, results, reason = verify_signal_comprehensive_new(latest_candle)
        
        if passed:
            print(f"[SIGNAL DETECTED] {symbol} at {format_timestamp_utc(timestamp)} | O={float(latest_candle['open']):.6f} H={float(latest_candle['high']):.6f} L={float(latest_candle['low']):.6f} C={float(latest_candle['close']):.6f} V={float(latest_candle['volume']):.2f}")
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
            }, "success"
        
        return None, reason
        
    except Exception as e:
        try:
            print(f"Error checking {symbol}: {e}")
        except UnicodeEncodeError:
            print(f"Error checking {symbol}: API error (rate limit or temporary issue)")
        return None, "exception"


async def monitor_symbols(universe_provider, auto_trader=None):
    """Monitor all symbols for signals with transparent statistics."""
    print("="*100)
    print("LW-001 REAL-TIME MONITOR")
    print("="*100)
    print()
    print(f"Universe: ALL active USDT Perpetual contracts from BingX (NO TOP-500 limit)")
    print(f"Timeframe: 15m")
    print(f"Thresholds: Range >= 4.5%, Body >= 0.8%, LW/Body >= 1.3x, LW/Range >= 55%")
    print(f"           Open->Low <= -2.5%")
    print(f"Candle direction: RED only (Close < Open)")
    print(f"Only CLOSED candles used")
    print()
    print("Press Ctrl+C to stop")
    print()
    print("="*100)
    print()
    
    signals_found = 0
    signals_sent = 0
    cycle_count = 0
    
    # Semaphore to limit concurrent API requests (avoid rate limits)
    MAX_CONCURRENT_REQUESTS = 10
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def check_symbol_with_semaphore(symbol):
        """Check a single symbol with semaphore for rate limiting."""
        async with semaphore:
            return await check_latest_candle(symbol, universe_provider)
    
    try:
        while True:
            cycle_count += 1
            # Get fresh universe from provider
            universe = await universe_provider.get_universe()
            final_universe_count = len(universe)
            
            print(f"\n{'='*100}")
            print(f"CYCLE #{cycle_count} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*100}")
            
            # UNIVERSE STATISTICS
            print(f"[UNIVERSE] FINAL_UNIVERSE count: {final_universe_count}")
            print(f"[UNIVERSE] First 5: {[s for s in universe[:5]]}")
            print(f"[UNIVERSE] Last 5:  {[s for s in universe[-5:]]}")
            
            # MONITORING STATISTICS
            planned = final_universe_count
            processed = 0
            success = 0
            errors = 0
            skipped = 0
            skip_reasons = {}
            
            # Create tasks for all symbols
            tasks = [check_symbol_with_semaphore(symbol) for symbol in universe]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, signal in zip(universe, results):
                if isinstance(signal, Exception):
                    errors += 1
                    skip_reasons["exception"] = skip_reasons.get("exception", 0) + 1
                    print(f"  [ERROR] {symbol}: {signal}")
                    continue
                
                # signal is a tuple (signal_data, reason) or (None, reason)
                signal_data, reason = signal
                
                if signal_data is None:
                    skipped += 1
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    continue
                
                # Successfully got OHLCV and processed
                success += 1
                processed += 1
                
                # Check if signal passed all thresholds
                if signal_data:
                    signals_found += 1
                    print(f"  [SIGNAL FOUND] {signal_data['symbol']} at {format_timestamp_utc(signal_data['timestamp'])}")
                    
                    # ATOMIC CLAIM: Try to claim this signal (atomic, prevents duplicates)
                    signal_key = (signal_data['symbol'], signal_data['timestamp'])
                    if not claim_signal(signal_data['symbol'], signal_data['timestamp']):
                        print(f"  [SKIP] Already sent: {signal_key}")
                        skipped += 1
                        skip_reasons["already_sent"] = skip_reasons.get("already_sent", 0) + 1
                        # Don't double count - we already counted as success
                        success -= 1
                        continue
                    
                    # Add to memory set for fast subsequent checks
                    SENT_SIGNALS.add(signal_key)
                    print(f"  [MEMORY] Added to SENT_SIGNALS: {signal_key}")
                    
                    # ===== AUTO-TRADING INTEGRATION =====
                    # Execute auto-trade on VST (demo) - non-blocking
                    if auto_trader:
                        print(f"  [AUTO-TRADE] Executing auto-trade for {signal_data['symbol']}...")
                        asyncio.create_task(auto_trader.process_signal(signal_data))
                    # =======================================
                    
                    # Send to Telegram with actual PASS/FAIL results
                    print(f"  [TELEGRAM] Attempting to send signal for {signal_data['symbol']}...")
                    success_send = await send_signal_to_telegram(signal_data, signal_data['results'])
                    if success_send:
                        signals_sent += 1
                        print(f"    [OK] Sent to Telegram successfully")
                    else:
                        print(f"    [ERROR] Failed to send to Telegram - rolling back claim")
                        # Rollback: Remove from DB and memory since send failed
                        conn = sqlite3.connect(SENT_SIGNALS_DB)
                        try:
                            conn.execute(
                                "DELETE FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?",
                                (signal_data['symbol'], signal_data['timestamp'])
                            )
                            conn.commit()
                            print(f"    [ROLLBACK] Removed from database: {signal_key}")
                        finally:
                            conn.close()
                        SENT_SIGNALS.discard(signal_key)
                        print(f"    [ROLLBACK] Removed from memory: {signal_key}")
            
            # STATISTICS SUMMARY
            print(f"\n[STATS] CYCLE #{cycle_count} SUMMARY:")
            print(f"  FINAL_UNIVERSE:    {final_universe_count}")
            print(f"  Planned (total):   {planned}")
            print(f"  Processed (OK):    {success}")
            print(f"  Errors (API):      {errors}")
            print(f"  Skipped:           {skipped}")
            for reason, count in skip_reasons.items():
                print(f"    - {reason}: {count}")
            print(f"  Signals Found:     {signals_found} (cumulative)")
            print(f"  Signals Sent:      {signals_sent} (cumulative)")
            
            # VERIFICATION: planned == success + errors + skipped
            total_accounted = success + errors + skipped
            if total_accounted != planned:
                print(f"  [WARNING] ACCOUNTING MISMATCH: planned={planned}, accounted={total_accounted} (diff={planned - total_accounted})")
            else:
                print(f"  [VERIFIED] planned == success + errors + skipped ({planned} == {success} + {errors} + {skipped})")
            
            print(f"{'='*100}")
            
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
    # ===== AUTO-TRADER INITIALIZATION =====
    auto_trader = None
    if AUTO_TRADER_AVAILABLE:
        from src.exchange.bingx_trader import AutoTraderManager
        auto_trader = AutoTraderManager()
        print("[ROBOT] Initializing auto-trader in DEMO mode (VST)...")
        await auto_trader.start(is_demo=True)
        print("[OK] Auto-trader started in DEMO mode (VST)")
    else:
        print("[WARNING] Auto-trader not available, trading disabled")
    # =======================================
    
    # Initialize universe provider
    from src.data_provider.universe_provider import get_universe_provider
    universe_provider = get_universe_provider()
    await universe_provider.initialize()
    
    try:
        await monitor_symbols(universe_provider, auto_trader)
    finally:
        # Cleanup auto-trader on exit
        if auto_trader:
            print("[STOP] Stopping auto-trader...")
            await auto_trader.stop()
            print("[OK] Auto-trader stopped")


if __name__ == "__main__":
    asyncio.run(main())