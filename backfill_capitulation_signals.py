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
from strategy.capitulation_detector import check_capitulation_signal

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

        # Use the same server-synchronized detector as the live monitor
        result = check_capitulation_signal(o, h, l, c, v, ts, prev_30)
        if not result.qualified:
            return None, "; ".join(result.failed_conditions)

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
            f"Open→Low ≤ -5.0% — PASS\n"
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
                        error_text = await resp.text()
                        return False, f"HTTP {resp.status}: {error_text}"
        except Exception as e:
            return False, f"Exception: {e}"

    async def run_backfill(self):
        """Run the complete backfill process."""
        print("=" * 80)
        print(f"EVRECONSE BACKFILL ENGINE")
        print(f"Period: {START_UTC} to {END_UTC}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Telegram: {'ENABLED' if self.send_telegram else 'DISABLED'}")
        print("=" * 80)

        await self.initialize()

        signals = []

        semaphore = asyncio.Semaphore(5)

        async def process_symbol(symbol):
            async with semaphore:
                candles = await self.fetch_symbol_data(symbol)
                if not candles:
                    return []

                now_ms = int(END_UTC.timestamp() * 1000)
                completed = self.find_completed_candles(candles, now_ms)

                symbol_signals = []
                for idx, candle in completed:
                    self.stats['total_evaluations'] += 1
                    result, reason = self.evaluate_candle(symbol, idx, candle, candles)
                    if result:
                        ts = candle.get('time', candle.get('timestamp', 0))
                        event_time_utc = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

                        m = result.metrics
                        signal = {
                            'symbol': symbol,
                            'timestamp': ts,
                            'event_time_utc': event_time_utc,
                            'metrics': {
                                'open': float(m.open),
                                'high': float(m.high),
                                'low': float(m.low),
                                'close': float(m.close),
                                'volume': float(m.volume),
                                'open_to_low_pct': m.open_to_low_pct,
                                'lw_body_ratio': m.lw_body_ratio,
                                'reclaim_pct': m.reclaim_pct,
                                'volume_30_ratio': m.volume_30_ratio,
                            },
                        }
                        signals.append(signal)
                        self.stats['signals_found'] += 1

                        if self.send_telegram and not self.dry_run:
                            message = self.format_telegram_message(symbol, event_time_utc, result)
                            success, msg_id = await self.send_telegram(message)
                            if success:
                                self.stats['signals_telegram_sent'] += 1
                            else:
                                self.stats['signals_telegram_failed'] += 1

        await asyncio.gather(*[process_symbol(s) for s in self.universe])

        # Save report
        report = {
            'period': {'start': START_UTC.isoformat(), 'end': END_UTC.isoformat()},
            'stats': self.stats,
            'dry_run': self.dry_run,
            'telegram_enabled': self.send_telegram,
        }

        with open(BACKFILL_REPORT, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n{'='*80}")
        print(f"BACKFILL COMPLETE")
        print(f"Signals found: {self.stats['signals_found']}")
        print(f"Signals sent: {self.stats['signals_telegram_sent']}")
        print(f"Signals failed: {self.stats['signals_telegram_failed']}")
        print(f"Report saved to: {BACKFILL_REPORT}")
        print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="EVRECONSE Historical Backfill for CAPITULATION/ABSORPTION")
    parser.add_argument('--send-telegram', action='store_true', help='Send signals to Telegram')
    parser.add_argument('--dry-run', action='store_true', help='Run without sending to Telegram')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    args = parser.parse_args()

    global START_UTC, END_UTC
    if args.start:
        START_UTC = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    if args.end:
        END_UTC = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    engine = BackfillEngine(send_telegram=args.send_telegram, dry_run=args.dry_run)
    await engine.run_backfill()


if __name__ == "__main__":
    asyncio.run(main())
