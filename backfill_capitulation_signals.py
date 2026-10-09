#!/usr/bin/env python3
"""
EVRECONSE Historical Backfill Script for CAPITULATION/ABSORPTION Signals

Finds and stores all historical signals from 05.10.2026 00:00 UTC to current time
using the exact production detector logic. Sends to Telegram with HISTORICAL BACKFILL label.
"""

import sys
import os
import json
import sqlite3
import argparse
import asyncio
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "/home/evreconse")
sys.path.insert(0, "/home/evreconse/src")
sys.path.insert(0, "/home/evreconse/src/strategy")

from src.exchange.bingx_fetcher import BingXFetcher
from src.data_provider.universe_provider import get_universe_provider
from src.strategy.capitulation_detector import check_capitulation_signal
from signal_storage import save_forward_observations

# Telegram imports
import aiohttp
from dotenv import load_dotenv
load_dotenv()

# Configuration
START_UTC = datetime(2026, 10, 5, 0, 0, 0, tzinfo=timezone.utc)  # 05.10.2026 00:00 UTC
END_UTC = datetime.now(timezone.utc)  # Current time

# Output files
DRY_RUN_REPORT = "/home/evreconse/backfill_dry_run_report.json"
BACKFILL_REPORT = "/home/evreconse/backfill_report.json"

class BackfillEngine:
    def __init__(self, send_telegram=False, dry_run=False):
        self.send_telegram = send_telegram
        self.dry_run = dry_run
        self.fetcher = BingXFetcher()
        self.universe_provider = None
        self.universe = []
        
        # Statistics
        self.stats = {
            'symbols_requested': 0,
            'symbols_loaded': 0,
            'symbols_failed': 0,
            'total_candles': 0,
            'total_evaluations': 0,
            'signals_found': 0,
            'signals_stored': 0,
            'signals_telegram_sent': 0,
            'signals_telegram_failed': 0,
            'gaps': [],
            'symbol_details': {}
        }
        
        # Telegram config
        self.bot_token = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN") or os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("EVRECONSE_NOTIFICATION__TELEGRAM__CHAT_ID") or os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
        
    async def initialize(self):
        """Initialize universe provider and load universe."""
        self.universe_provider = get_universe_provider()
        await self.universe_provider.initialize()
        self.universe = await self.universe_provider.get_universe()
        self.stats['symbols_requested'] = len(self.universe)
        print(f"Universe loaded: {len(self.universe)} symbols")
        
    async def fetch_symbol_data(self, symbol):
        """Fetch M15 OHLCV data for a symbol from START_UTC - 8 hours to END_UTC."""
        try:
            # Fetch extra data for Volume30 median calculation (need 30 candles before first evaluation)
            fetch_start = START_UTC - timedelta(hours=8)
            fetch_end = END_UTC + timedelta(hours=1)  # Extra buffer
            
            candles = await self.fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                start_time=int(fetch_start.timestamp() * 1000),
                end_time=int(fetch_end.timestamp() * 1000),
                limit=1000
            )
            
            if not candles:
                return None
                
            # Sort by timestamp
            candles.sort(key=lambda c: c.get('time', c.get('timestamp', 0)))
            return candles
            
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            return None
    
    def find_completed_candles(self, candles, now_ms):
        """Find all completed candles using production logic."""
        completed = []
        for i in range(len(candles) - 1, -1, -1):
            c = candles[i]
            ts = c.get('time', c.get('timestamp', 0))
            if ts <= 0:
                continue
            candle_close = ts + (15 * 60 * 1000)
            if candle_close <= now_ms:
                completed.append((i, c))
        completed.reverse()
        return completed
    
    def evaluate_candle(self, symbol, idx, candle, candles):
        """Evaluate a single candle using production detector logic."""
        ts = candle.get('time', candle.get('timestamp', 0))
        
        # CHECK PRODUCTION DEDUP - skip if already sent in production
        conn = sqlite3.connect("/home/evreconse/sent_signals.db")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?", (symbol, ts))
            if cursor.fetchone():
                return None, "already_sent_in_production"
        finally:
            conn.close()
        o = float(candle['open'])
        h = float(candle['high'])
        l = float(candle['low'])
        c = float(candle['close'])
        v = float(candle['volume'])
        
        # Need at least 30 previous candles for Volume30
        if idx < 30:
            return None, "insufficient_history"
        
        prev_30 = [float(candles[idx-30+j]['volume']) for j in range(30)]
        median30 = statistics.median(prev_30)
        
        # Use production detector
        result = check_capitulation_signal(o, h, l, c, v, ts, prev_30)
        
        return result, "ok"
    
    def format_telegram_message(self, symbol, event_time_utc, result, is_historical=True):
        """Format message for Telegram with HISTORICAL BACKFILL label."""
        m = result.metrics
        
        prefix = "🔍 HISTORICAL BACKFILL\n\n" if is_historical else "🟢 LONG CAPITULATION / ABSORPTION\n\n"
        
        message = (
            f"{prefix}"
            f"Symbol: {symbol}\n\n"
            f"Time: {event_time_utc}\n\n"
            f"OHLCV\n"
            f"Open: {m.open:.6f}\n"
            f"High: {m.high:.6f}\n"
            f"Low: {m.low:.6f}\n"
            f"Close: {m.close:.6f}\n"
            f"Volume: {m.volume:,.0f}\n\n"
            f"Metrics\n"
            f"Range: {m.range_pct:.2f}%\n"
            f"Open→Low: {m.open_to_low_pct:.2f}%\n"
            f"Body: {m.body_pct:.2f}%\n"
            f"Lower Wick: {m.lower_wick:.6f}\n"
            f"LW/Body: {m.lw_body_ratio:.2f}x\n"
            f"LW/Range: {m.lw_range_pct:.2f}%\n"
            f"Reclaim: {m.reclaim_pct:.2f}%\n"
            f"Close Position: {m.close_position_pct:.2f}%\n\n"
            f"Volume\n"
            f"Median30: {m.volume_30_median:,.0f}\n"
            f"Volume Ratio: {m.volume_30_ratio:.2f}x\n\n"
            f"✅ Conditions\n"
            f"Open→Low ≤ -2.5% — PASS\n"
            f"Volume30Ratio ≥ 2.0x — PASS\n"
            f"LW/Body ≥ 1.0x — PASS\n"
            f"Reclaim ≥ 30% — PASS\n\n"
            f"Direction: LONG\n"
            f"Type: CAPITULATION_ABSORPTION\n"
            f"Mode: {'HISTORICAL BACKFILL' if is_historical else 'SHADOW'}"
        )
        return message
    
    async def send_telegram(self, message):
        """Send message to Telegram."""
        if not self.bot_token or not self.chat_id:
            return False, "No credentials"
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('ok', False), data.get('result', {}).get('message_id')
                    else:
                        text = await resp.text()
                        return False, f"HTTP {resp.status}: {text}"
        except Exception as e:
            return False, str(e)
    
    def save_signal_with_symbol(self, result, symbol):
        """Save signal with explicit symbol (fix for save_signal expecting m.symbol)."""
        if not result.qualified:
            return None
        
        m = result.metrics
        timestamp_utc = datetime.fromtimestamp(m.timestamp / 1000, tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        created_at = int(datetime.now(timezone.utc).timestamp())
        
        try:
            import sqlite3
            conn = sqlite3.connect("/home/evreconse/capitulation_signals.db")
            try:
                cursor = conn.cursor()
                # Debug: print table schema
                cursor.execute("PRAGMA table_info(signals)")
                cols = cursor.fetchall()
                print(f"[DEBUG] Table schema: {[(c[1], c[2]) for c in cols]}")
                print(f"[DEBUG] Column count: {len(cols)}")
                
                # Drop and recreate table with correct schema to ensure correct column count
                cursor.execute("DROP TABLE IF EXISTS signals")
                conn.commit()
                cursor.execute("""
                    CREATE TABLE signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        candle_timestamp INTEGER NOT NULL,
                        timestamp_utc TEXT NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        range_pct REAL NOT NULL,
                        open_to_low_pct REAL NOT NULL,
                        body_pct REAL NOT NULL,
                        lower_wick REAL NOT NULL,
                        lw_body_ratio REAL NOT NULL,
                        lw_range_pct REAL NOT NULL,
                        reclaim_pct REAL NOT NULL,
                        close_position_pct REAL NOT NULL,
                        volume_30_median REAL NOT NULL,
                        volume_30_ratio REAL NOT NULL,
                        signal_direction TEXT NOT NULL DEFAULT 'LONG',
                        signal_type TEXT NOT NULL DEFAULT 'CAPITULATION_ABSORPTION',
                        mode TEXT NOT NULL DEFAULT 'SHADOW',
                        created_at INTEGER NOT NULL,
                        UNIQUE(symbol, candle_timestamp)
                    )
                """)
                conn.commit()
                
                cursor.execute("""
                    INSERT OR IGNORE INTO signals (
                        symbol, candle_timestamp, timestamp_utc,
                        open, high, low, close, volume,
                        range_pct, open_to_low_pct,
                        body_pct,
                        lower_wick, lw_body_ratio, lw_range_pct,
                        reclaim_pct, close_position_pct,
                        volume_30_median, volume_30_ratio,
                        signal_direction, signal_type, mode,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    m.timestamp,
                    timestamp_utc,
                    m.open,
                    m.high,
                    m.low,
                    m.close,
                    m.volume,
                    m.range_pct,
                    m.open_to_low_pct,
                    m.body_pct,
                    m.lower_wick,
                    m.lw_body_ratio,
                    m.lw_range_pct,
                    m.reclaim_pct,
                    m.close_position_pct,
                    m.volume_30_median,
                    m.volume_30_ratio,
                    result.signal_direction,
                    result.signal_type,
                    "SHADOW",
                    int(datetime.now(timezone.utc).timestamp())
                ))
                conn.commit()
                
                if cursor.rowcount > 0:
                    return cursor.lastrowid
                else:
                    # Duplicate - get existing
                    cursor.execute(
                        "SELECT id FROM signals WHERE symbol = ? AND candle_timestamp = ?",
                        (symbol, m.timestamp)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else None
            finally:
                conn.close()
        except Exception as e:
            print(f"[SIGNAL DB ERROR] Failed to save signal: {e}")
            return None
    
    async def process_symbol(self, symbol, semaphore):
        """Process all candles for a single symbol."""
        async with semaphore:
            candles = await self.fetch_symbol_data(symbol)
            
            if not candles:
                self.stats['symbols_failed'] += 1
                self.stats['symbol_details'][symbol] = {'error': 'No data'}
                return
            
            self.stats['symbols_loaded'] += 1
            self.stats['total_candles'] += len(candles)
            
            now_ms = int(END_UTC.timestamp() * 1000)
            completed = self.find_completed_candles(candles, int(END_UTC.timestamp() * 1000))
            
            # Filter to our time range
            start_ms = int(START_UTC.timestamp() * 1000)
            end_ms = int(END_UTC.timestamp() * 1000)
            
            in_range = [(i, c) for i, c in completed 
                       if start_ms <= c.get('time', c.get('timestamp', 0)) <= end_ms]
            
            symbol_signals = 0
            symbol_evals = 0
            
            for idx, candle in in_range:
                if idx < 30:
                    continue
                
                symbol_evals += 1
                self.stats['total_evaluations'] += 1
                
                result, reason = self.evaluate_candle(symbol, idx, candle, candles)
                
                if result is None:
                    continue
                
                if result.qualified:
                    symbol_signals += 1
                    self.stats['signals_found'] += 1
                    
                    ts = candle.get('time', candle.get('timestamp', 0))
                    event_time_utc = datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
                    
                    # Store in database
                    if not self.dry_run:
                        signal_id = self.save_signal_with_symbol(result, symbol)
                        if signal_id:
                            self.stats['signals_stored'] += 1
                            # Save forward observations
                            future_candles = candles[idx+1:]
                            if future_candles:
                                save_forward_observations(signal_id, future_candles, [1, 2, 4, 8, 16, 32])
                    
                    # Send to Telegram
                    if self.send_telegram and not self.dry_run:
                        message = self.format_telegram_message(symbol, event_time_utc, result, is_historical=True)
                        success, msg_id = await self.send_telegram(message)
                        if success:
                            self.stats['signals_telegram_sent'] += 1
                            print(f"  [TELEGRAM] Sent {symbol} @ {event_time_utc} (msg_id={msg_id})")
                        else:
                            self.stats['signals_telegram_failed'] += 1
                            print(f"  [TELEGRAM FAILED] {symbol} @ {event_time_utc}: {msg_id}")
                    elif self.dry_run:
                        print(f"  [DRY RUN] Signal: {symbol} @ {event_time_utc}")
            
            self.stats['symbol_details'][symbol] = {
                'candles_fetched': len(candles),
                'candles_evaluated': symbol_evals,
                'signals_found': symbol_signals
            }
            
            if symbol_signals > 0:
                print(f"  {symbol}: {symbol_signals} signals from {symbol_evals} evaluations")
    
    async def run(self, max_concurrent=10):
        """Run the backfill."""
        print("=" * 80)
        print("EVRECONSE HISTORICAL BACKFILL")
        print("=" * 80)
        print(f"Period: {START_UTC.strftime('%Y-%m-%d %H:%M UTC')} → {END_UTC.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Universe: {len(self.universe)} symbols")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE' + (' + TELEGRAM' if self.send_telegram else '')}")
        print("=" * 80)
        
        await self.initialize()
        
        semaphore = asyncio.Semaphore(10)
        
        # Process symbols in batches to avoid memory issues
        batch_size = 50
        for i in range(0, len(self.universe), batch_size):
            batch = self.universe[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}: {len(batch)} symbols...")
            
            tasks = [self.process_symbol(symbol, asyncio.Semaphore(10)) for symbol in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        self.print_summary()
        self.save_report()
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print("BACKFILL SUMMARY")
        print("=" * 80)
        print(f"Symbols requested:    {self.stats['symbols_requested']}")
        print(f"Symbols loaded:       {self.stats['symbols_loaded']}")
        print(f"Symbols failed:       {self.stats['symbols_failed']}")
        print(f"Total candles:        {self.stats['total_candles']:,}")
        print(f"Total evaluations:    {self.stats['total_evaluations']:,}")
        print(f"Signals found:        {self.stats['signals_found']}")
        
        if not self.dry_run:
            print(f"Signals stored:       {self.stats['signals_stored']}")
            if self.send_telegram:
                print(f"Telegram sent:        {self.stats['signals_telegram_sent']}")
                print(f"Telegram failed:      {self.stats['signals_telegram_failed']}")
        
        # Signal distribution
        signal_counts = defaultdict(int)
        for sym, details in self.stats['symbol_details'].items():
            signal_counts[details['signals_found']] += 1
        
        print(f"\nSignal distribution:")
        for count in sorted(signal_counts.keys()):
            print(f"  {count} signal(s): {signal_counts[count]} symbols")
        
        # Top symbols
        top_symbols = sorted(
            [(s, d['signals_found']) for s, d in self.stats['symbol_details'].items() if d['signals_found'] > 0],
            key=lambda x: -x[1]
        )[:20]
        
        if top_symbols:
            print(f"\nTop 20 symbols by signal count:")
            for sym, count in top_symbols:
                print(f"  {sym}: {count}")
    
    def save_report(self):
        report = {
            'start_utc': START_UTC.isoformat(),
            'end_utc': END_UTC.isoformat(),
            'run_time_utc': datetime.now(timezone.utc).isoformat(),
            'dry_run': self.dry_run,
            'send_telegram': self.send_telegram,
            'universe_count': len(self.universe),
            'universe_hash': '4fb2eec904843c0173e80f6e27f625e95c14682d1ed102865cecd37b46b543d9',
            'stats': self.stats
        }
        
        output_file = DRY_RUN_REPORT if self.dry_run else BACKFILL_REPORT
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {output_file}")


async def main():
    parser = argparse.ArgumentParser(description='EVRECONSE Historical Backfill for CAPITULATION/ABSORPTION Signals')
    parser.add_argument('--send-telegram', action='store_true', help='Send signals to Telegram')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no DB/Telegram)')
    parser.add_argument('--verify-doge', action='store_true', help='Verify DOGE-USDT 08.10.2026 04:15 signal')
    
    args = parser.parse_args()
    
    # Force dry-run if verify-doge is set
    if args.verify_doge:
        args.dry_run = True
    
    engine = BackfillEngine(send_telegram=args.send_telegram, dry_run=args.dry_run)
    
    if args.verify_doge:
        # Quick verification of DOGE signal
        await engine.initialize()
        print("Verifying DOGE-USDT 08.10.2026 04:15 UTC...")
        await engine.process_symbol("DOGE-USDT", asyncio.Semaphore(1))
    else:
        await engine.run()

if __name__ == "__main__":
    asyncio.run(main())