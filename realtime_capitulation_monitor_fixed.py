#!/usr/bin/env python3
"""
Real-time Capitulation/Absorption Monitor (SHADOW MODE)

Monitors 15m candles in real-time and detects capitulation/absorption LONG candidates.
Uses Capitulation Detector with dynamic BingX Universe (ALL active USDT Perpetuals).
AUTO-TRADER IS DISABLED - SHADOW MODE ONLY.

FIXES APPLIED:
- Added BingX API rate limiting (450 req/10s per official 500/10s limit)
- Added retry logic for rate limit errors ("请稍后重试") with exponential backoff + jitter
- Added detailed statistics tracking for each cycle
- Added proper error classification (rate limit, offline symbol, network, other)
- Added coverage reporting (successful checks / total symbols)
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
# =================================================

# Rate limiter integration
from src.exchange.bingx_rate_limiter import BingXRateLimiter, BingXRateLimitError, BingXOfflineSymbolError, is_rate_limit_error, is_offline_symbol_error

# Persistent deduplication database
if platform.system() == "Windows":
    SENT_SIGNALS_DB = Path("C:/EVRECONSE_PROJECT/sent_signals.db")
else:
    SENT_SIGNALS_DB = Path("/home/evreconse/sent_signals.db")

# Forensic logging paths
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

def init_telegram_test_db():
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
                kwargs.get('test_type'),
                kwargs.get('signal_id'),
                kwargs.get('symbol'),
                kwargs.get('candle_timestamp'),
                kwargs.get('telegram_started_at'),
                kwargs.get('telegram_success_at'),
                kwargs.get('telegram_error'),
                kwargs.get('http_status'),
                kwargs.get('message_id'),
                int(time.time())
            ))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[TELEGRAM TEST LOG ERROR] {e}")

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
                    telegram_message_id INTEGER,
                    telegram_status TEXT DEFAULT 'pending',
                    telegram_error TEXT,
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
            cursor.execute(
                "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at, telegram_status) VALUES (?, ?, ?, ?)",
                (symbol, candle_timestamp, int(time.time()), 'pending')
            )
            conn.commit()
            print(f"[CLAIM] SUCCESS: Claimed signal for {symbol} at {candle_timestamp}")
            return True
        except sqlite3.IntegrityError:
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

# Initialize databases
init_sent_signals_db()
# init_telegram_test_db()  # DISABLED: forensic test disabled on startup

# Load sent signals into memory for fast checks
def load_sent_signals_to_memory():
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, candle_timestamp FROM sent_signals")
        return set((row[0], row[1]) for row in cursor.fetchall())
    finally:
        conn.close()

SENT_SIGNALS = load_sent_signals_to_memory()


# FIXED Capitulation/Absorption thresholds
FIXED_THRESHOLDS = {
    "drop_pct": -5.0,       # Open→Low ≤ -5.0%
    "wick_body_ratio": 1.0, # LW/Body ≥ 1.0x
    "reclaim_pct": 30.0,    # Reclaim ≥ 30%
    "volume_30_ratio": 2.0, # Volume30Ratio ≥ 2.0x
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

def check_thresholds(metrics):
    """Check if metrics pass all thresholds. Returns (passed, results_dict)."""
    results = {}
    results["drop_pct"] = metrics.open_to_low_pct <= FIXED_THRESHOLDS["drop_pct"]
    results["wick_body_ratio"] = metrics.lw_body_ratio >= FIXED_THRESHOLDS["wick_body_ratio"]
    results["reclaim_pct"] = metrics.reclaim_pct >= FIXED_THRESHOLDS["reclaim_pct"]
    results["volume_30_ratio"] = metrics.volume_30_ratio >= FIXED_THRESHOLDS["volume_30_ratio"]
    passed = all(results.values())
    return passed, results

def format_condition_line(condition_name, threshold_str, passed):
    """Format a single condition line with PASS/FAIL."""
    status = "PASS" if passed else "FAIL"
    return f"{condition_name} {threshold_str} — {status}"

def format_telegram_message(signal, results):
    """Format signal using fixed immutable template (plain text)."""
    metrics = signal['metrics']
    symbol = signal['symbol']
    timestamp = signal['timestamp']

    conditions = [
        format_condition_line("Drop", "≤ -5.0%", results["drop_pct"]),
        format_condition_line("Wick/Body", "≥ 1.0x", results["wick_body_ratio"]),
        format_condition_line("Reclaim", "≥ 30%", results["reclaim_pct"]),
        format_condition_line("Volume30Ratio", "≥ 2.0x", results["volume_30_ratio"]),
    ]

    message = f"""🟢 LONG CAPITULATION / ABSORPTION

🪙 Symbol: {symbol}

⏰ Time: {format_timestamp_utc(timestamp)}

💰 OHLCV
Open: {signal['open']:.6f}
High: {signal['high']:.6f}
Low: {signal['low']:.6f}
Close: {signal['close']:.6f}
Volume: {signal['volume']:.2f}

📊 Metrics
Drop: {metrics.open_to_low_pct:.2f}%
Wick/Body: {metrics.lw_body_ratio:.2f}x
Reclaim: {metrics.reclaim_pct:.2f}%
Volume30Ratio: {metrics.volume_30_ratio:.2f}x

✅ Conditions
{chr(10).join(conditions)}

✅ VALID SIGNAL"""

    return message


# =============================================================================
# CYCLE STATISTICS TRACKING
# =============================================================================

class CycleStats:
    """Track detailed statistics for each monitoring cycle."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all counters for a new cycle."""
        self._symbols_requested = 0
        self._symbols_fetched = 0
        self._candles_checked = 0
        self._filtered_drop = 0
        self._filtered_volume = 0
        self._filtered_wick = 0
        self._filtered_reclaim = 0
        self._signals_found = 0
        self._signals_sent = 0
        self._symbols_offline = 0
        self._rate_limit_errors = 0
        self._network_errors = 0
        self._api_errors = 0
        self._exception_errors = 0
        self._already_processed = 0
        self._insufficient_history = 0
        self._insufficient_candles = 0
        self._no_completed_candle = 0
        self._not_red = 0
        self._invalid_timestamp = 0
        self._start_time = None
        self._end_time = None
    
    def start_cycle(self):
        self._start_time = time.monotonic()
    
    def end_cycle(self):
        self._end_time = time.monotonic()
    
    @property
    def duration_seconds(self) -> float:
        if self._start_time and self._end_time:
            return self._end_time - self._start_time
        return 0.0
    
    @property
    def symbols_requested(self) -> int:
        return self._symbols_requested
    
    @symbols_requested.setter
    def symbols_requested(self, value: int):
        self._symbols_requested = value
    
    @property
    def symbols_fetched(self) -> int:
        return self._symbols_fetched
    
    @symbols_fetched.setter
    def symbols_fetched(self, value: int):
        self._symbols_fetched = value
    
    @property
    def candles_checked(self) -> int:
        return self._candles_checked
    
    @candles_checked.setter
    def candles_checked(self, value: int):
        self._candles_checked = value
    
    @property
    def coverage_pct(self) -> float:
        if self._symbols_requested > 0:
            return (self._symbols_fetched / self._symbols_requested) * 100
        return 0.0
    
    def print_summary(self, cycle_num: int, universe_count: int):
        print(f"\n[STATS] CYCLE #{cycle_num} SUMMARY:")
        print(f"  UNIVERSE:              {universe_count}")
        print(f"  REQUESTED:             {self._symbols_requested}")
        print(f"  FETCHED OK:            {self._symbols_fetched} ({self.coverage_pct:.1f}% coverage)")
        print(f"  CANDLES VALIDATED:     {self._candles_checked}")
        print(f"  SIGNALS FOUND:         {self._signals_found} (this cycle)")
        print(f"  SIGNALS SENT:          {self._signals_sent}")
        print(f"  FILTERED DROP:         {self._filtered_drop}")
        print(f"  FILTERED VOLUME:       {self._filtered_volume}")
        print(f"  FILTERED WICK/BODY:    {self._filtered_wick}")
        print(f"  FILTERED RECLAIM:      {self._filtered_reclaim}")
        print(f"  ALREADY PROCESSED:     {self._already_processed}")
        print(f"  NOT RED:               {self._not_red}")
        print(f"  INSUFFICIENT HISTORY:  {self._insufficient_history}")
        print(f"  INSUFFICIENT CANDLES:  {self._insufficient_candles}")
        print(f"  NO COMPLETED CANDLE:   {self._no_completed_candle}")
        print(f"  INVALID TIMESTAMP:     {self._invalid_timestamp}")
        print(f"  SYMBOLS OFFLINE:       {self._symbols_offline}")
        print(f"  RATE LIMIT ERRORS:     {self._rate_limit_errors}")
        print(f"  NETWORK ERRORS:        {self._network_errors}")
        print(f"  API ERRORS:            {self._api_errors}")
        print(f"  EXCEPTIONS:            {self._exception_errors}")
        print(f"  DURATION:              {self.duration_seconds:.1f}s")


async def send_signal_to_telegram(signal_data, test_type: str = "LIVE"):
    """Send a single signal to Telegram (plain text) with explicit UTF-8 encoding.
    Sends to both personal chat and channel (if configured).
    Returns: (success: bool, message_id: int or None) - success if at least one delivery succeeded"""
    # FIX: Use 'metrics' directly from signal_data, not 'result.metrics'
    metrics = signal_data['metrics']
    symbol = signal_data['symbol']
    timestamp = signal_data['timestamp']
    m = metrics  # FIX: was result.metrics, now using signal_data['metrics'] directly

    bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    
    # Get both chat IDs: personal and channel
    personal_chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    channel_chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHANNEL_ID")
    
    chat_ids = []
    if personal_chat_id:
        chat_ids.append(("personal", personal_chat_id))
    if channel_chat_id:
        chat_ids.append(("channel", channel_chat_id))
    
    if not bot_token:
        print("  [TELEGRAM ERROR] Telegram bot token not found")
        return False, None
    
    if not chat_ids:
        print("  [TELEGRAM ERROR] No chat IDs configured (neither personal nor channel)")
        return False, None

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    message_text = format_telegram_message(signal_data, signal_data.get('results', {}))

    print(f"  [TELEGRAM] Preparing to send: bot_token={'SET' if bot_token else 'MISSING'}, destinations={len(chat_ids)}")

    message_text = format_telegram_message(signal_data, signal_data.get('results', {}))

    print(f"  [TELEGRAM PRE-SEND] text_repr={repr(message_text[:200])}... len={len(message_text)} chars")

    any_success = False
    first_msg_id = None
    
    for dest_name, chat_id in chat_ids:
        print(f"  [TELEGRAM] Sending to {dest_name} (chat_id={chat_id})...")
        
        payload = {
            "chat_id": chat_id,
            "text": message_text,
        }
        
        try:
            print(f"  [TELEGRAM] Sending request to Telegram API for {dest_name}...")
            import json
            payload_bytes = json.dumps({"chat_id": chat_id, "text": message_text}, ensure_ascii=False).encode('utf-8')
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
                            if msg_id is not None:
                                print(f"  [TELEGRAM SUCCESS] Sent to {dest_name}, message_id={msg_id}")
                                if not any_success:
                                    first_msg_id = msg_id
                                any_success = True
                            else:
                                print(f"  [TELEGRAM ERROR] API returned ok=true but no message_id for {dest_name}: {data}")
                        else:
                            print(f"  [TELEGRAM ERROR] API returned ok=false for {dest_name}: {data}")
                    else:
                        text = await resp.text()
                        print(f"  [TELEGRAM ERROR] API returned status {resp.status} for {dest_name}: {text}")
        except Exception as e:
            print(f"  [TELEGRAM ERROR] Exception for {dest_name}: {type(e).__name__}: {e}")
    
    return any_success, first_msg_id


def verify_signal_comprehensive(candle_data, prev_30_volumes):
    """Comprehensive verification of a signal. Returns (passed, metrics, results_dict, reason)."""
    from src.strategy.capitulation_detector import check_capitulation_signal

    open_price = float(candle_data['open'])
    high_price = float(candle_data['high'])
    low_price = float(candle_data['low'])
    close_price = float(candle_data['close'])
    volume = float(candle_data['volume'])
    timestamp = candle_data.get('time', candle_data.get('timestamp', 0))

    if timestamp <= 0:
        return False, None, None, "Invalid timestamp"

    if not check_red_candle(open_price, close_price):
        return False, None, None, "Candle is not red (Close >= Open)"

    if len(prev_30_volumes) < 30:
        return False, None, None, "Insufficient history for Volume30"

    result = check_capitulation_signal(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        timestamp=timestamp,
        prev_30_volumes=prev_30_volumes
    )

    metrics = result.metrics
    passed, results = check_thresholds(metrics)

    if not passed:
        # Determine which specific filter failed
        if not results["drop_pct"]:
            return False, metrics, results, "DROP_FAIL"
        elif not results["volume_30_ratio"]:
            return False, metrics, results, "VOLUME_FAIL"
        elif not results["wick_body_ratio"]:
            return False, metrics, results, "WICK_BODY_FAIL"
        elif not results["reclaim_pct"]:
            return False, metrics, results, "RECLAIM_FAIL"
        else:
            return False, metrics, results, "UNKNOWN_FAIL"

    return True, metrics, results, "OK"


def get_last_completed_candle(candles):
    """Identify the last completed candle from the fetched candles."""
    if not candles or len(candles) < 2:
        return None, None

    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)

    for i in range(len(candles) - 1, -1, -1):
        candle = candles[i]
        timestamp = candle.get('time', candle.get('timestamp', 0))
        if timestamp <= 0:
            continue
        candle_close_time = timestamp + (15 * 60 * 1000)
        if candle_close_time <= now_ms:
            return candle, i

    return None, None


async def check_latest_candle_with_stats(symbol, stats, fetcher=None):
    """Check the latest completed 15m candle for a symbol with detailed statistics."""
    from src.exchange.bingx_fetcher import BingXFetcher
    
    if fetcher is None:
        fetcher = BingXFetcher()
    
    stats._symbols_requested += 1
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=4)

    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )

        if not candles or len(candles) < 2:
            stats._insufficient_candles += 1
            return None, "insufficient_candles"

        latest_candle, candle_index = get_last_completed_candle(candles)

        if latest_candle is None:
            stats._no_completed_candle += 1
            return None, "no_completed_candle"

        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))

        if timestamp <= 0:
            stats._invalid_timestamp += 1
            return None, "Invalid timestamp"

        # Check if already processed (persistent check)
        signal_key = (symbol, timestamp)
        if signal_key in SENT_SIGNALS:
            stats._already_processed += 1
            return None, "already_processed"

        if candle_index < 31:
            stats._insufficient_history += 1
            return None, "insufficient_history"

        stats._symbols_fetched += 1
        stats._candles_checked += 1

        prev_30_volumes = [float(candles[candle_index - 30 + j]['volume']) for j in range(30)]

        passed, metrics, results, reason = verify_signal_comprehensive(latest_candle, prev_30_volumes)

        if not passed:
            # Track which filter failed using the specific failure code
            if reason == "DROP_FAIL":
                stats._filtered_drop += 1
            elif reason == "VOLUME_FAIL":
                stats._filtered_volume += 1
            elif reason == "WICK_BODY_FAIL":
                stats._filtered_wick += 1
            elif reason == "RECLAIM_FAIL":
                stats._filtered_reclaim += 1
            elif reason == "NOT_RED":
                stats._not_red += 1
            elif reason == "INSUFFICIENT_HISTORY":
                stats._insufficient_history += 1
            elif reason == "INSUFFICIENT_CANDLES":
                stats._insufficient_candles += 1
            elif reason == "NO_COMPLETED_CANDLE":
                stats._no_completed_candle += 1
            elif reason == "INVALID_TIMESTAMP":
                stats._invalid_timestamp += 1
            elif reason == "ALREADY_PROCESSED":
                stats._already_processed += 1
            else:
                stats._exception_errors += 1
            return None, reason

        # Signal passed all filters
        stats._signals_found += 1
        
        print(f"[SIGNAL DETECTED] {symbol} at {format_timestamp_utc(timestamp)} | "
              f"O={float(latest_candle['open']):.6f} H={float(latest_candle['high']):.6f} L={float(latest_candle['low']):.6f} C={float(latest_candle['close']):.6f} V={float(latest_candle['volume']):.2f} | "
              f"Range={metrics.range_pct:.2f}% Open→Low={metrics.open_to_low_pct:.2f}% "
              f"LW/Body={metrics.lw_body_ratio:.2f}x Reclaim={metrics.reclaim_pct:.2f}% "
              f"Vol30Ratio={metrics.volume_30_ratio:.2f}x")
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

    except Exception as e:
        error_msg = str(e).lower()
        if "请稍后重试" in error_msg or "rate limit" in error_msg or "please try again" in error_msg or "100401" in error_msg or "429" in error_msg:
            stats._rate_limit_errors += 1
            return None, "rate_limit"
        elif "offline currently" in error_msg or "is offline" in error_msg or "100402" in error_msg or "100410" in error_msg:
            stats._symbols_offline += 1
            return None, "offline"
        elif isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError)):
            stats._network_errors += 1
            return None, "network_error"
        else:
            stats._exception_errors += 1
            try:
                print(f"Error checking {symbol}: {e}")
            except UnicodeEncodeError:
                print(f"Error checking {symbol}: API error (rate limit or temporary issue)")
        return None, "exception"


def get_last_completed_candle(candles):
    """Identify the last completed candle from the fetched candles."""
    if not candles or len(candles) < 2:
        return None, None

    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)

    for i in range(len(candles) - 1, -1, -1):
        candle = candles[i]
        timestamp = candle.get('time', candle.get('timestamp', 0))
        if timestamp <= 0:
            continue
        candle_close_time = timestamp + (15 * 60 * 1000)
        if candle_close_time <= now_ms:
            return candle, i

    return None, None


async def check_latest_candle(symbol, universe_provider):
    """Check the latest completed 15m candle for a symbol (legacy function kept for compatibility)."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=4)

    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )

        if not candles or len(candles) < 2:
            return None, "insufficient_candles"

        latest_candle, candle_index = get_last_completed_candle(candles)

        if latest_candle is None:
            return None, "no_completed_candle"

        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))

        # Check if already processed (persistent check)
        signal_key = (symbol, timestamp)
        if signal_key in SENT_SIGNALS:
            return None, "already_processed"

        if candle_index < 31:
            return None, "insufficient_history"

        prev_30_volumes = [float(candles[candle_index - 30 + j]['volume']) for j in range(30)]

        passed, metrics, results, reason = verify_signal_comprehensive(latest_candle, prev_30_volumes)

        if passed:
            print(f"[SIGNAL DETECTED] {symbol} at {format_timestamp_utc(timestamp)} | "
                  f"O={float(latest_candle['open']):.6f} H={float(latest_candle['high']):.6f} L={float(latest_candle['low']):.6f} C={float(latest_candle['close']):.6f} V={float(latest_candle['volume']):.2f} | "
                  f"Range={metrics.range_pct:.2f}% Open→Low={metrics.open_to_low_pct:.2f}% "
                  f"LW/Body={metrics.lw_body_ratio:.2f}x Reclaim={metrics.reclaim_pct:.2f}% "
                  f"Vol30Ratio={metrics.volume_30_ratio:.2f}x")
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


async def retry_pending_signals():
    """Retry sending pending signals from database on startup."""
    conn = sqlite3.connect(SENT_SIGNALS_DB)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT symbol, candle_timestamp FROM sent_signals WHERE telegram_status = 'pending'"
        )
        pending = cursor.fetchall()

        if pending:
            print(f"[STARTUP RETRY] Found {len(pending)} pending signals, attempting retry...")
            for symbol, ts in pending:
                print(f"[RETRY] Would retry {symbol} @ {ts} - manual intervention needed")
    finally:
        conn.close()


async def monitor_symbols(universe_provider):
    """Monitor all symbols for signals with transparent statistics."""
    print("="*100)
    print("CAPITULATION / ABSORPTION MONITOR — SHADOW MODE (RATE LIMITED)")
    print("="*100)
    print()
    print(f"Universe: ALL active USDT Perpetual contracts from BingX (NO TOP-500 limit)")
    print(f"Timeframe: 15m")
    print(f"Thresholds: Drop ≤ -5.0%, Wick/Body ≥ 1.0x, Reclaim ≥ 30%, Volume30Ratio ≥ 2.0x")
    print(f"Candle direction: RED only (Close < Open)")
    print(f"Only CLOSED candles used")
    print(f"Rate limit: 450 req/10s (official 500/10s with margin)")
    print()
    print("Press Ctrl+C to stop")
    print()
    print("="*100)
    print()

    signals_found_total = 0
    signals_sent_total = 0
    cycle_count = 0

    MAX_CONCURRENT_REQUESTS = 10
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Create shared fetcher for rate limiting
    from src.exchange.bingx_fetcher import BingXFetcher
    shared_fetcher = BingXFetcher()

    async def check_symbol_with_semaphore(symbol, stats):
        async with semaphore:
            return await check_latest_candle_with_stats(symbol, stats, shared_fetcher)

    # Retry pending signals on startup
    await retry_pending_signals()

    try:
        while True:
            cycle_count += 1
            universe = await universe_provider.get_universe()
            final_universe_count = len(universe)

            stats = CycleStats()
            stats.start_cycle()

            print(f"\n{'='*100}")
            print(f"CYCLE #{cycle_count} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*100}")

            print(f"[UNIVERSE] FINAL_UNIVERSE count: {final_universe_count}")
            print(f"[UNIVERSE] First 5: {[s for s in universe[:5]]}")
            print(f"[UNIVERSE] Last 5:  {[s for s in universe[-5:]]}")

            tasks = [check_symbol_with_semaphore(symbol, stats) for symbol in universe]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            signals_found_this_cycle = 0
            signals_sent_this_cycle = 0

            for symbol, signal in zip(universe, results):
                if isinstance(signal, Exception):
                    stats._exception_errors += 1
                    print(f"  [ERROR] {symbol}: {signal}")
                    continue

                signal_data, reason = signal

                if signal_data is None:
                    # Skip reason already counted in stats
                    continue

                # Signal passed all filters
                signals_found_total += 1
                signals_found_this_cycle += 1
                stats._signals_found += 1
                
                print(f"  [SIGNAL FOUND] {signal_data['symbol']} at {format_timestamp_utc(signal_data['timestamp'])}")

                # ATOMIC CLAIM
                signal_key = (signal_data['symbol'], signal_data['timestamp'])
                if not claim_signal(signal_data['symbol'], signal_data['timestamp']):
                    print(f"  [SKIP] Already sent: {signal_key}")
                    stats._already_processed += 1
                    stats._signals_found -= 1
                    signals_found_total -= 1
                    continue

                SENT_SIGNALS.add(signal_key)
                print(f"  [MEMORY] Added to SENT_SIGNALS: {signal_key}")

                # Send to Telegram
                print(f"  [TELEGRAM] Attempting to send signal for {signal_data['symbol']}...")
                success_send, msg_id = await send_signal_to_telegram(signal_data)
                if success_send:
                    signals_sent_total += 1
                    signals_sent_this_cycle += 1
                    stats._signals_sent += 1
                    print(f"    [OK] Sent to Telegram successfully, message_id={msg_id}")
                    # Update telegram_status to sent
                    conn = sqlite3.connect(SENT_SIGNALS_DB)
                    try:
                        conn.execute(
                            "UPDATE sent_signals SET telegram_status = 'sent', telegram_message_id = ? WHERE symbol = ? AND candle_timestamp = ?",
                            (msg_id, signal_data['symbol'], signal_data['timestamp'])
                        )
                        conn.commit()
                    finally:
                        conn.close()
                else:
                    print(f"    [ERROR] Failed to send to Telegram")
                    # Update telegram_status to failed
                    conn = sqlite3.connect(SENT_SIGNALS_DB)
                    try:
                        conn.execute(
                            "UPDATE sent_signals SET telegram_status = 'failed', telegram_error = 'Telegram send failed' WHERE symbol = ? AND candle_timestamp = ?",
                            (signal_data['symbol'], signal_data['timestamp'])
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    # Rollback claim
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

            stats.end_cycle()
            stats._signals_found = signals_found_this_cycle
            stats._signals_sent = signals_sent_this_cycle
            stats.print_summary(cycle_count, final_universe_count)

            # Print fetcher stats
            fetcher_stats = shared_fetcher.get_stats()
            print(f"  FETCHER: requests_ok={fetcher_stats.get('requests_success', 0)}, rate_limits={fetcher_stats.get('rate_limit_hits', 0)}, retries={fetcher_stats.get('rate_limit_retries', 0)}")

            print(f"{'='*100}")

            # Wait until next 15m candle completes
            now = datetime.now(timezone.utc)
            minutes = now.minute
            seconds = now.second

            next_15m = ((minutes // 15) + 1) * 15
            if next_15m >= 60:
                next_15m = 0
                wait_minutes = 60 - minutes + next_15m - (seconds / 60)
            else:
                wait_minutes = next_15m - minutes - (seconds / 60)

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
        print(f"Total signals found: {signals_found_total}")
        print(f"Total signals sent: {signals_sent_total}")
        print()


async def main():
    from src.data_provider.universe_provider import get_universe_provider
    universe_provider = get_universe_provider()
    await universe_provider.initialize()

    try:
        await monitor_symbols(universe_provider)
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(main())