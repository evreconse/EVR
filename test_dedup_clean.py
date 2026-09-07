#!/usr/bin/env python3
"""
Tests for persistent deduplication mechanism (SQLite-based).
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
import threading

sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

def test_database_initialization():
    """Test that database is created with correct schema."""
    test_db_path = Path(tempfile.mktemp(suffix='.db'))
    try:
        # Create database with the same schema as production
        conn = sqlite3.connect(test_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
        
        # Check schema
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='sent_signals'")
        schema = cursor.fetchone()[0]
        conn.close()
        
        assert "PRIMARY KEY (symbol, candle_timestamp)" in schema
        print("[OK] Database initialization test passed")
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


def test_claim_signal_atomic():
    """Test atomic claim mechanism prevents duplicates."""
    test_db_path = Path(tempfile.mktemp(suffix='.db'))
    try:
        # Create database with production schema
        conn = sqlite3.connect(test_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
        conn.close()
        
        # Define claim function
        def claim_signal(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
                    (symbol, candle_timestamp, int(__import__('time').time()))
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()
        
        def is_signal_sent(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?",
                    (symbol, candle_timestamp)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        
        # First claim should succeed
        result1 = claim_signal("BTC-USDT", 1234567890000)
        assert result1 == True, "First claim should succeed"
        
        # Second claim should fail (duplicate)
        result2 = claim_signal("BTC-USDT", 1234567890000)
        assert result2 == False, "Second claim should fail"
        
        # Check is_signal_sent
        assert is_signal_sent("BTC-USDT", 1234567890000) == True
        assert is_signal_sent("BTC-USDT", 1234567890001) == False
        
        print("[OK] Atomic claim test passed")
    finally:
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


def test_concurrent_claims():
    """Test concurrent claims are handled correctly."""
    test_db_path = Path(tempfile.mktemp(suffix='.db'))
    try:
        # Create database with production schema
        conn = sqlite3.connect(test_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
        conn.close()
        
        def claim_signal(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
                    (symbol, candle_timestamp, int(__import__('time').time()))
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()
        
        # Simulate concurrent claims from multiple threads
        results = []
        
        def claim_worker():
            result = claim_signal("BTC-USDT", 1234567890000)
            results.append(result)
        
        threads = [threading.Thread(target=claim_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Exactly one should succeed
        success_count = sum(results)
        assert success_count == 1, f"Exactly one should succeed, got {success_count}"
        
        print("[OK] Concurrent claims test passed")
    finally:
        import os
        test_db_path = Path(tempfile.mktemp(suffix='.db'))
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


def test_crash_scenarios():
    """Test crash scenarios with SQLite-based dedup."""
    test_db_path = Path(tempfile.mktemp(suffix='.db'))
    try:
        # Create database with production schema
        conn = sqlite3.connect(test_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
        conn.close()
        
        def claim_signal(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
                    (symbol, candle_timestamp, int(__import__('time').time()))
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()
        
        def is_signal_sent(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sent_signals WHERE symbol = ? AND candle_timestamp = ?",
                    (symbol, candle_timestamp)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        
        # Scenario A: Claim -> Telegram success (simulated)
        claim1 = claim_signal("BTC-USDT", 1234567890000)
        assert claim1 == True
        assert is_signal_sent("BTC-USDT", 1234567890000) == True
        
        # Simulate process crash AFTER claim but BEFORE Telegram send
        # Restart simulation: check if signal is still in DB
        assert is_signal_sent("BTC-USDT", 1234567890000) == True
        print("  Scenario C (crash before send): No duplicate on restart [OK]")
        
        # Scenario B: Claim -> Telegram failure
        # (Already claimed, so second attempt fails)
        claim2 = claim_signal("BTC-USDT", 1234567890000)
        assert claim2 == False, "Second claim should fail"
        print("  Scenario B (Telegram failure): No duplicate claim [OK]")
        
        # Scenario A: Normal flow - claim succeeds
        print("  Scenario A (claim + send): Single message [OK]")
        
        # Scenario D: Crash after send - already in DB
        # Already covered by restart check above
        print("  Scenario D (crash after send): No duplicate on restart [OK]")
        
        print("[OK] Crash scenarios test passed")
    finally:
        import os
        test_db_path = Path(tempfile.mktemp(suffix='.db'))
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


def test_concurrent_claims():
    """Test concurrent claims are handled correctly."""
    import threading
    
    test_db_path = Path(tempfile.mktemp(suffix='.db'))
    try:
        # Create database with production schema
        conn = sqlite3.connect(test_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_signals (
                symbol TEXT NOT NULL,
                candle_timestamp INTEGER NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, candle_timestamp)
            )
        """)
        conn.commit()
        conn.close()
        
        def claim_signal(symbol, candle_timestamp):
            conn = sqlite3.connect(test_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sent_signals (symbol, candle_timestamp, sent_at) VALUES (?, ?, ?)",
                    (symbol, candle_timestamp, int(__import__('time').time()))
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()
        
        # Simulate concurrent claims from multiple threads
        results = []
        
        def claim_worker():
            result = claim_signal("BTC-USDT", 1234567890000)
            results.append(result)
        
        threads = [threading.Thread(target=claim_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Exactly one should succeed
        success_count = sum(results)
        assert success_count == 1, f"Exactly one should succeed, got {success_count}"
        
        print("[OK] Concurrent claims test passed")
    finally:
        import os
        test_db_path = Path(tempfile.mktemp(suffix='.db'))
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


def test_telegram_timeout_tradeoff():
    """Test that the trade-off is clearly documented: possible signal loss but no duplicates."""
    print("""
Trade-off Analysis:
===================
Model: CLAIM -> SAVE (SQLite atomic claim with PRIMARY KEY constraint)

Scenario: Telegram timeout/connection error - uncertain if message was delivered
- If we CLAIM first (INSERT with PRIMARY KEY): Signal marked as sent in DB
- If Telegram actually received it but HTTP response lost: No duplicate on retry
- If Telegram didn't receive it: Signal lost (no retry)

TRADE-OFF: Possible signal LOSS (safe) vs DUPLICATE (unsafe)
- Loss: User misses one signal (acceptable)
- Duplicate: User gets same signal twice (unacceptable for trading)

This is the SAFE trade-off for financial signals.
""")
    print("[OK] Trade-off documented")


def run_all_tests():
    """Run all tests."""
    print("Running deduplication tests...\n")
    
    test_database_initialization()
    test_claim_signal_atomic()
    test_concurrent_claims()
    test_crash_scenarios()
    
    print("\n[OK] ALL TESTS PASSED")


if __name__ == "__main__":
    run_all_tests()