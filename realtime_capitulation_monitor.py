#!/usr/bin/env python3
"""
Real-time Capitulation/Absorption Monitor (SHADOW MODE)

Monitors 15m candles in real-time and detects capitulation/absorption LONG candidates.
Uses new Capitulation Detector with dynamic BingX Universe (ALL active USDT Perpetuals).
AUTO-TRADER IS DISABLED - SHADOW MODE ONLY.
"""

import sys
import os
import platform
import sqlite3
import json
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

# ===== AUTO-TRADER DISABLED FOR SHADOW MODE =====
AUTO_TRADER_AVAILABLE = False
print("[SHADOW MODE] Auto-trader DISABLED - no real trading")

# ===== FORENSIC LOGGING =====
if platform.system() == "Windows":
    FORENSIC_LOG = Path("C:/EVRECONSE_PROJECT/logs/forensic_live.log")
    FORENSIC_SNAPSHOT = Path("C:/EVRECONSE_PROJECT/logs/live_forensic_snapshot.json")
    TELEGRAM_TEST_DB = Path("C:/EVRECONSE_PROJECT/telegram_test.db")
else:
    FORENSIC_LOG = Path("/home/evreconse/logs/forensic_live.log")
    FORENSIC_SNAPSHOT = Path("/home/evreconse/logs/live_forensic_snapshot.json")
    TELEGRAM_TEST_DB = Path("/home/evreconse/telegram_test.db")

FORENSIC_LOG.parent.mkdir(parents=True, exist_ok=True)

def forensic_log(entry: dict):
    """Write forensic entry to log file."""
    entry['logged_at'] = datetime.now(timezone.utc).isoformat()
    try:
        with open(FORENSIC_LOG, 'a') as f:
            f.write(json.dumps(entry, default=str) + '\n')
    except Exception as e:
        print(f"[FORENSIC LOG ERROR] {e}")

def write_snapshot(snapshot: dict):
    """Write live forensic snapshot."""
    try:
        with open(FORENSIC_SNAPSHOT, 'w') as f:
            json.dump(snapshot, f, indent=2, default=str)
    except Exception as e:
        print(f"[SNAPSHOT ERROR] {e}")

def init_telegram_test_db():  # DISABLED: forensic test on startup
    """Initialize SQLite database for Telegram test tracking."""
    try:
        conn = sqlite3.connect(TELEGRAM_TEST_DB)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_type TEXT NOT NULL,
                    signal_id INTEGER,
                    symbol TEXT,
                    candle_timestamp INTEGER,
                    telegram_started_at INTEGER,
                    telegram_success_at INTEGER,
                    telegram_error TEXT,
                    http_status INTEGER,
                    message_id INTEGER,
                    created_at INTEGER NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[TELEGRAM TEST DB ERROR] {e}")
        raise

def log_telegram_test(test_type: str, **kwargs):
    """Log Telegram test attempt."""
    try:
        conn = sqlite3.connect(TELEGRAM_TEST_DB)
        try:
            conn.execute("""
                INSERT INTO telegram_tests (
                    test_type, signal_id, symbol, candle_timestamp,
                    telegram_started_at, telegram_success_at, telegram_error,
                    http_status, message_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_type,
                kwargs.get('signal_id'),
                kwargs.get('symbol'),
                kwargs.get('candle_timestamp'),
                kwargs.get('telegram_started_at'),
                kwargs.get('telegram_success_at'),
                kwargs.get('telegram_error'),
                kwargs.get('http_status'),
                kwargs.get('message_id'),
                int(datetime.now(timezone.utc).timestamp())
            ))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[TELEGRAM TEST LOG ERROR] {e}")

# ===============================================

# Persistent deduplication database
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

# Load sent signals into memory for fast checks
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


# Import new capitulation detector (direct module import to avoid package issues)
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "strategy"))

from capitulation_detector import (
    check_capitulation_signal,
    format_capitulation_telegram_message,
    run_unit_tests,
)
from signal_storage import save_signal, save_forward_observations


def format_timestamp_utc(timestamp_ms):
    """Convert raw candle timestamp to UTC format ONLY."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, timezone.utc)
    utc_str = dt_utc.strftime("%d.%m.%Y %H:%M UTC")
    return utc_str


def get_last_completed_candle(candles):
    """
    Identify the last completed candle from the fetched candles.
    
    BingX returns candles in chronological order (oldest first).
    The last candle may be incomplete (current period).
    
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
    """Check the latest completed 15m candle for capitulation/absorption signal."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    # Fetch enough candles for closed candle detection + 30 for volume median
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=8)  # ~32 candles
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles or len(candles) < 32:  # Need 30 for median + 1 signal + 1 buffer
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
        
        # Need at least 30 candles before current for volume median
        if candle_index < 30:
            return None, "insufficient_history_for_volume_median"
        
        # Extract OHLCV
        open_price = float(latest_candle['open'])
        high_price = float(latest_candle['high'])
        low_price = float(latest_candle['low'])
        close_price = float(latest_candle['close'])
        volume = float(latest_candle['volume'])
        
        # Get previous 30 completed volumes (N-30 to N-1)
        prev_30_volumes = [float(c['volume']) for c in candles[candle_index-30:candle_index]]
        
        # Verify signal using NEW capitulation detector
        result = check_capitulation_signal(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            timestamp=timestamp,
            prev_30_volumes=prev_30_volumes,
        )
        
        if result.qualified:
            print(f"[CAPITULATION SIGNAL] {symbol} at {format_timestamp_utc(timestamp)} | "
                  f"O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f} V={volume:.2f} | "
                  f"Range={result.metrics.range_pct:.2f}% Open→Low={result.metrics.open_to_low_pct:.2f}% "
                  f"LW/Body={result.metrics.lw_body_ratio:.2f}x Reclaim={result.metrics.reclaim_pct:.2f}% "
                  f"Vol30Ratio={result.metrics.volume_30_ratio:.2f}x")
            return {
                'symbol': symbol,
                'timestamp': timestamp,
                'result': result,
                'candles': candles,
                'candle_index': candle_index,
            }, "success"
        
        return None, "criteria_not_met"
        
    except Exception as e:
        try:
            print(f"Error checking {symbol}: {e}")
        except UnicodeEncodeError:
            print(f"Error checking {symbol}: API error (rate limit or temporary issue)")
        return None, "exception"


async def send_signal_to_telegram(signal_data, test_type: str = "LIVE"):
    """Send a single capitulation signal to Telegram (plain text) with explicit UTF-8 encoding."""
    result = signal_data['result']
    symbol = signal_data['symbol']
    timestamp = signal_data['timestamp']
    m = result.metrics
    
    # Support both naming conventions for compatibility
    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    print(f"  [TELEGRAM] Preparing to send: bot_token={'SET' if bot_token else 'MISSING'}, chat_id={'SET' if chat_id else 'MISSING'}")
    
    if not bot_token or not chat_id:
        print("  [TELEGRAM ERROR] Telegram credentials not found")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    event_time_utc = format_timestamp_utc(timestamp)
    message = format_capitulation_telegram_message(symbol, event_time_utc, result)
    
    # PRE-SEND DIAGNOSTIC
    print(f"  [TELEGRAM PRE-SEND] text_repr={repr(message[:200])}... len={len(message)} chars")
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        # No parse_mode = plain text
    }
    
    telegram_started = int(datetime.now(timezone.utc).timestamp())
    
    try:
        print(f"  [TELEGRAM] Sending request to Telegram API...")
        import json
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(payload_bytes))
        }
        
        # Log telegram test start
        log_telegram_test(
            test_type="LIVE_SIGNAL",
            symbol=signal_data['symbol'],
            candle_timestamp=signal_data['timestamp'],
            telegram_started_at=telegram_started
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload_bytes, headers=headers) as resp:
                telegram_success = int(datetime.now(timezone.utc).timestamp())
                http_status = resp.status
                
                if resp.status == 200:
                    data = await resp.json()
                    ok = data.get('ok', False)
                    if ok:
                        msg_id = data.get('result', {}).get('message_id')
                        print(f"  [TELEGRAM SUCCESS] Message sent successfully, message_id={msg_id}")
                        
                        # Log success
                        log_telegram_test(
                            test_type="LIVE_SIGNAL",
                            signal_id=None,
                            symbol=signal_data['symbol'],
                            candle_timestamp=signal_data['timestamp'],
                            telegram_started_at=telegram_started,
                            telegram_success_at=telegram_success,
                            http_status=http_status,
                            message_id=msg_id
                        )
                    else:
                        print(f"  [TELEGRAM ERROR] API returned ok=false: {data}")
                        error_msg = str(data)
                        log_telegram_test(
                            test_type="LIVE_SIGNAL",
                            symbol=signal_data['symbol'],
                            candle_timestamp=signal_data['timestamp'],
                            telegram_started_at=telegram_started,
                            telegram_error=error_msg,
                            http_status=http_status
                        )
                    return ok
                else:
                    text = await resp.text()
                    print(f"  [TELEGRAM ERROR] API returned status {resp.status}: {text}")
                    log_telegram_test(
                        test_type="LIVE_SIGNAL",
                        symbol=signal_data['symbol'],
                        candle_timestamp=signal_data['timestamp'],
                        telegram_started_at=telegram_started,
                        telegram_error=f"HTTP {resp.status}: {text}",
                        http_status=resp.status
                    )
                    return False
    except Exception as e:
        telegram_error = f"{type(e).__name__}: {e}"
        print(f"  [TELEGRAM ERROR] Exception: {telegram_error}")
        log_telegram_test(
            test_type="LIVE_SIGNAL",
            symbol=signal_data['symbol'],
            candle_timestamp=signal_data['timestamp'],
            telegram_started_at=telegram_started,
            telegram_error=telegram_error,
            http_status=0
        )
        return False


async def monitor_symbols(universe_provider):
    """Monitor all symbols for capitulation/absorption signals in SHADOW MODE."""
    print("="*100)
    print("CAPITULATION / ABSORPTION MONITOR — SHADOW MODE")
    print("="*100)
    print()
    print(f"Universe: ALL active USDT Perpetual contracts from BingX (NO TOP-500 limit)")
    print(f"Timeframe: 15m")
    print(f"Strategy: LONG candidates only (capitulation + absorption)")
    print(f"Thresholds (configurable):")
    print(f"  Open->Low <= -2.5%")
    print(f"  Volume30Ratio >= 2.0x")
    print(f"  LW/Body >= 1.0x")
    print(f"  Reclaim >= 30%")
    print(f"Candle direction: RED only (downside impulse indicator)")
    print(f"Only CLOSED candles used")
    print(f"Mode: SHADOW (AutoTrader OFF, Real Trading OFF, Orders = 0)")
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
    
    # Forward observation horizons
    HORIZONS = [1, 2, 4, 8, 16, 32]
    
    async def check_symbol_with_semaphore(symbol):
        """Check a single symbol with semaphore for rate limiting."""
        async with semaphore:
            return await check_latest_candle(symbol, universe_provider)
    
    try:
        while True:
            cycle_count += 1
            cycle_start = datetime.now(timezone.utc)
            # Get fresh universe from provider
            universe = await universe_provider.get_universe()
            final_universe_count = len(universe)
            
            print(f"\n{'='*100}")
            print(f"CYCLE #{cycle_count} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
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
            
            # FORENSIC TRACKING
            cycle_forensic = {
                'cycle': cycle_count,
                'cycle_start_utc': cycle_start.isoformat(),
                'universe_count': final_universe_count,
                'evaluated': 0,
                'errors': 0,
                'red': 0,
                'drop': 0,
                'wick': 0,
                'reclaim': 0,
                'volume': 0,
                'final': 0,
                'signals': []
            }
            
            # Create tasks for all symbols
            tasks = [check_symbol_with_semaphore(symbol) for symbol in universe]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, signal in zip(universe, results):
                if isinstance(signal, Exception):
                    errors += 1
                    cycle_forensic['errors'] += 1
                    skip_reasons["exception"] = skip_reasons.get("exception", 0) + 1
                    print(f"  [ERROR] {symbol}: {signal}")
                    continue
                
                signal_data, reason = signal
                
                if signal_data is None:
                    skipped += 1
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    cycle_forensic['evaluated'] += 1
                    
                    # Log forensic detail for skipped
                    forensic_log({
                        'type': 'SKIPPED',
                        'cycle': cycle_count,
                        'symbol': symbol,
                        'reason': reason,
                        'cycle_start': cycle_start.isoformat()
                    })
                    continue
                
                # Successfully got OHLCV and processed
                success += 1
                processed += 1
                cycle_forensic['evaluated'] += 1
                
                # Log raw candle data
                result = signal_data['result']
                timestamp = signal_data['timestamp']
                m = result.metrics
                forensic_log({
                    'type': 'CANDLE_EVALUATED',
                    'cycle': cycle_count,
                    'symbol': symbol,
                    'candle_timestamp': timestamp,
                    'dt': format_timestamp_utc(timestamp),
                    'open': m.open, 'high': m.high, 'low': m.low, 'close': m.close, 'volume': m.volume,
                    'open_to_low_pct': m.open_to_low_pct,
                    'lw_body_ratio': m.lw_body_ratio,
                    'reclaim_pct': m.reclaim_pct,
                    'volume_30_ratio': m.volume_30_ratio,
                    'is_red': m.is_red,
                    'cycle_start': cycle_start.isoformat()
                })
                
                # Check if signal passed all thresholds
                if signal_data:
                    signals_found += 1
                    cycle_forensic['final'] += 1
                    timestamp = signal_data['timestamp']
                    print(f"  [SIGNAL FOUND] {signal_data['symbol']} at {format_timestamp_utc(timestamp)}")
                    
                    # Log signal found
                    forensic_log({
                        'type': 'SIGNAL_FOUND',
                        'cycle': cycle_count,
                        'symbol': signal_data['symbol'],
                        'candle_timestamp': timestamp,
                        'dt': format_timestamp_utc(timestamp),
                        'metrics': {
                            'open': m.open, 'high': m.high, 'low': m.low, 'close': m.close, 'volume': m.volume,
                            'open_to_low_pct': m.open_to_low_pct,
                            'lw_body_ratio': m.lw_body_ratio,
                            'reclaim_pct': m.reclaim_pct,
                            'volume_30_ratio': m.volume_30_ratio
                        },
                        'cycle_start': cycle_start.isoformat()
                    })
                    
                    # ATOMIC CLAIM - insert into sent_signals.db
                    conn = sqlite3.connect(SENT_SIGNALS_DB)
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR IGNORE INTO sent_signals (symbol, candle_timestamp, sent_at, telegram_status) VALUES (?, ?, ?, ?)",
                                   (signal_data['symbol'], signal_data['timestamp'], int(time.time()), 'pending'))
                        conn.commit()
                        if cursor.rowcount == 0:
                            return None, "already_sent"
                    finally:
                        conn.close()
                    
                    # Legacy claim_signal for compatibility
                    signal_key = (signal_data['symbol'], signal_data['timestamp'])
                    if not claim_signal(signal_data['symbol'], signal_data['timestamp']):
                        print(f"  [SKIP] Already sent: {signal_key}")
                        skipped += 1
                        skip_reasons["already_sent"] = skip_reasons.get("already_sent", 0) + 1
                        success -= 1
                        continue
                    
                    # Add to memory set for fast subsequent checks
                    SENT_SIGNALS.add(signal_key)
                    print(f"  [MEMORY] Added to SENT_SIGNALS: {signal_key}")
                    
                    # ===== SAVE SIGNAL TO PERSISTENT STORAGE =====
                    signal_id = save_signal(result)
                    
                    # ===== SAVE FORWARD OBSERVATIONS =====
                    if signal_id:
                        future_candles = signal_data['candles'][signal_data['candle_index']+1:]
                        save_forward_observations(signal_id, future_candles, HORIZONS)
                    
                    # Send to Telegram
                    print(f"  [TELEGRAM] Attempting to send signal for {signal_data['symbol']}...")
                    success_send = await send_signal_to_telegram(signal_data)
                    if success_send:
                        signals_sent += 1
                        cycle_forensic['signals'].append({
                            'symbol': signal_data['symbol'],
                            'candle_timestamp': signal_data['timestamp'],
                            'dt': format_timestamp_utc(signal_data['timestamp']),
                            'signal_id': signal_id
                        })
                        print(f"    [OK] Sent to Telegram successfully")
                    else:
                        print(f"    [ERROR] Failed to send to Telegram - rolling back claim")
                        # Rollback
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
                else:
                    # Log stage failures
                    if not m.is_red:
                        cycle_forensic['red'] += 0
                    elif m.open_to_low_pct > -2.5:
                        cycle_forensic['drop'] += 1
                    elif m.lw_body_ratio < 1.0:
                        cycle_forensic['wick'] += 1
                    elif m.reclaim_pct < 30.0:
                        cycle_forensic['reclaim'] += 1
                    elif m.volume_30_ratio < 2.0:
                        cycle_forensic['volume'] += 1
                
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
            
            # FORENSIC CYCLE SUMMARY
            print(f"\n[FORENSIC] CYCLE #{cycle_count} FUNNEL:")
            print(f"  Evaluated:         {cycle_forensic['evaluated']}")
            print(f"  Errors:            {cycle_forensic['errors']}")
            print(f"  RED:               {cycle_forensic['red']}")
            print(f"  DROP (<=-2.5%):    {cycle_forensic['drop']}")
            print(f"  WICK (>=1.0x):     {cycle_forensic['wick']}")
            print(f"  RECLAIM (>=30%):   {cycle_forensic['reclaim']}")
            print(f"  VOLUME (>=2.0x):   {cycle_forensic['volume']}")
            print(f"  FINAL:             {cycle_forensic['final']}")
            
            # Write cycle snapshot
            cycle_forensic['cycle_end_utc'] = datetime.now(timezone.utc).isoformat()
            write_snapshot(cycle_forensic)
            
            # VERIFICATION
            total_accounted = success + errors + skipped
            if total_accounted != planned:
                print(f"  [WARNING] ACCOUNTING MISMATCH: planned={planned}, accounted={total_accounted} (diff={planned - total_accounted})")
            else:
                print(f"  [VERIFIED] planned == success + errors + skipped ({planned} == {success} + {errors} + {skipped})")
            
            print(f"{'='*100}")
            
            # Wait until next 15m boundary (00, 15, 30, 45) for cycle start alignment
            now = datetime.now(timezone.utc)
            minutes = now.minute
            seconds = now.second
            microseconds = now.microsecond
            
            # Current position in 15-min cycle (0-899 seconds)
            seconds_into_cycle = (minutes % 15) * 60 + seconds + microseconds / 1_000_000
            
            # Time until next 15-min boundary
            wait_seconds = 900 - seconds_into_cycle
            
            # Add 10 second buffer for data availability (candle closes at boundary, API needs ~10s)
            wait_seconds += 10
            
            print(f"Waiting {wait_seconds:.0f} seconds until next 15m boundary...")
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


async def send_diagnostic_telegram_test():
    """Send a diagnostic test message through the production Telegram pipeline."""
    print("\n" + "="*80)
    print("DIAGNOSTIC TELEGRAM TEST")
    print("="*80)
    
    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("  [TELEGRAM TEST] Credentials not found")
        return False
    
    # Create a test signal using a known historical signal format
    test_message = (
        "🔬 FORENSIC TELEGRAM TEST\n\n"
        "This is a diagnostic test of the production Telegram pipeline.\n"
        "It does NOT represent a real trading signal.\n\n"
        f"Test time: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}\n"
        f"Test type: FORENSIC_TELEGRAM_TEST\n"
        f"Mode: SHADOW\n"
    )
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": test_message}
    
    telegram_started = int(datetime.now(timezone.utc).timestamp())
    log_telegram_test(
        test_type="DIAGNOSTIC_TEST",
        telegram_started_at=telegram_started
    )
    
    try:
        print(f"  [DIAGNOSTIC TEST] Sending test message to Telegram...")
        import json
        payload_bytes = json.dumps({"chat_id": chat_id, "text": test_message}, ensure_ascii=False).encode('utf-8')
        headers = {"Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(payload_bytes))}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload_bytes, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ok = data.get('ok', False)
                    if ok:
                        msg_id = data.get('result', {}).get('message_id')
                        print(f"  [DIAGNOSTIC TEST SUCCESS] message_id={msg_id}")
                        log_telegram_test(
                            test_type="DIAGNOSTIC_TEST",
                            telegram_started_at=int(datetime.now(timezone.utc).timestamp()),
                            telegram_success_at=int(datetime.now(timezone.utc).timestamp()),
                            http_status=200,
                            message_id=msg_id
                        )
                        return True
                    else:
                        print(f"  [DIAGNOSTIC TEST ERROR] API returned ok=false: {data}")
                        log_telegram_test(
                            test_type="DIAGNOSTIC_TEST",
                            telegram_started_at=int(datetime.now(timezone.utc).timestamp()),
                            telegram_error=str(data),
                            http_status=200
                        )
                        return False
                else:
                    text = await resp.text()
                    print(f"  [DIAGNOSTIC TEST ERROR] HTTP {resp.status}: {text}")
                    log_telegram_test(
                        test_type="DIAGNOSTIC_TEST",
                        telegram_started_at=int(datetime.now(timezone.utc).timestamp()),
                        telegram_error=f"HTTP {resp.status}: {text}",
                        http_status=resp.status
                    )
                    return False
    except Exception as e:
        print(f"  [DIAGNOSTIC TEST ERROR] Exception: {type(e).__name__}: {e}")
        log_telegram_test(
            test_type="DIAGNOSTIC_TEST",
            telegram_started_at=int(datetime.now(timezone.utc).timestamp()),
            telegram_error=f"{type(e).__name__}: {e}",
            http_status=0
        )
        return False


async def send_historical_signal_test():
    """Send a real historical signal through the production Telegram pipeline for verification."""
    print("\n" + "="*80)
    print("HISTORICAL SIGNAL TELEGRAM TEST")
    print("="*80)
    
    # Use one of the known historical signals from replay
    # DOGE-USDT @ 2026-10-08 04:15 UTC was a strong signal
    test_symbol = "DOGE-USDT"
    test_timestamp = 1791432900000  # 2026-10-08 04:15 UTC
    
    print(f"  [HISTORICAL TEST] Fetching real data for {test_symbol} @ {datetime.fromtimestamp(test_timestamp/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.capitulation_detector import check_capitulation_signal
    
    fetcher = BingXFetcher()
    end_time = datetime.fromtimestamp(test_timestamp/1000, tz=timezone.utc) + timedelta(hours=1)
    start_time = end_time - timedelta(hours=8)
    
    try:
        candles = await fetcher.get_klines(
            symbol=test_symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        target_candle = None
        target_idx = -1
        for i, c in enumerate(candles):
            ts = c.get('time', c.get('timestamp', 0))
            if ts == test_timestamp:
                target_candle = c
                target_idx = i
                break
        
        if target_candle is None or target_idx < 30:
            print(f"  [HISTORICAL TEST] Target candle not found or insufficient history")
            return False
        
        o = float(target_candle['open'])
        h = float(target_candle['high'])
        l = float(target_candle['low'])
        c_price = float(target_candle['close'])
        v = float(target_candle['volume'])
        
        prev_30 = [float(candles[target_idx-30+j]['volume']) for j in range(30)]
        result = check_capitulation_signal(o, h, l, c_price, v, test_timestamp, prev_30)
        
        print(f"  [HISTORICAL TEST] Qualified: {result.qualified}")
        if result.qualified:
            # Create signal_data format for send_signal_to_telegram
            signal_data = {
                'symbol': test_symbol,
                'timestamp': test_timestamp,
                'result': result,
                'candles': candles,
                'candle_index': target_idx
            }
            
            print(f"  [HISTORICAL TEST] Sending real historical signal through production pipeline...")
            success = await send_signal_to_telegram(signal_data)
            if success:
                print(f"  [HISTORICAL TEST SUCCESS] Real historical signal sent to Telegram")
                return True
            else:
                print(f"  [HISTORICAL TEST FAILED] Telegram send failed")
                return False
        else:
            print(f"  [HISTORICAL TEST] Signal not qualified (unexpected)")
            return False
            
    except Exception as e:
        print(f"  [HISTORICAL TEST ERROR] Exception: {type(e).__name__}: {e}")
        return False


async def main():
    """Main function - SHADOW MODE."""
    print("[SHADOW MODE] Starting Capitulation/Absorption Monitor")
    print("[SHADOW MODE] AutoTrader = OFF")
    print("[SHADOW MODE] Real Trading = OFF")
    print("[SHADOW MODE] Orders = 0")
    print()
    
    # Initialize databases
    init_sent_signals_db()
    # init_telegram_test_db()  # DISABLED: forensic test on startup
    
    # Run diagnostic Telegram test first  # DISABLED
    print("\n" + "="*80)
    print("RUNNING DIAGNOSTIC TELEGRAM TESTS")
    print("="*80)
    
    diagnostic_ok = await send_diagnostic_telegram_test()
    historical_ok = await send_historical_signal_test()
    
    print(f"\n[DIAGNOSTIC RESULTS]")
    print(f"  Diagnostic test: {'PASS' if diagnostic_ok else 'FAIL'}")
    print(f"  Historical test: {'PASS' if historical_ok else 'FAIL'}")
    
    if not diagnostic_ok:
        print("  [WARNING] Diagnostic Telegram test failed - check credentials/API")
    
    # Initialize universe provider
    from src.data_provider.universe_provider import get_universe_provider
    universe_provider = get_universe_provider()
    await universe_provider.initialize()
    
    try:
        await monitor_symbols(universe_provider)
    finally:
        print("[SHADOW MODE] Clean shutdown")


if __name__ == "__main__":
    asyncio.run(main())