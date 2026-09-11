"""
CMC Universe Cache - SQLite-based persistent cache with atomic swap.

Provides atomic updates, TTL management, and fallback to last good universe.
"""

import sqlite3
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager


@dataclass
class CMCUniverseSnapshot:
    """Represents a cached CMC universe snapshot."""
    universe: List[Dict[str, Any]]  # List of {"symbol": "BTC-USDT", "cmc_rank": 1, ...}
    cmc_raw_count: int
    target_count: int
    filtered_count: int
    eligible_count: int
    exact_matches: int
    base_asset_matches: int
    ambiguous_count: int
    no_match_count: int
    final_count: int
    bingx_active_contracts: int
    fetched_at: str
    version_hash: str
    validation_status: str  # "ACCEPT", "REJECT", "PENDING"
    validation_errors: List[str]


class CMCUniverseCache:
    """
    SQLite-based cache for CMC Universe snapshots with atomic swap.
    
    Provides:
    - Atomic activation (no partial states)
    - TTL-based expiry (24h TTL, 72h max stale)
    - Persistent fallback (last_good_universe.json)
    - Audit trail of all snapshots
    """
    
    DB_PATH = Path("data/cmc_universe.db")
    FALLBACK_FILE = Path("data/last_good_universe.json")
    BACKUP_FILE = Path("data/cmc_universe.db.backup")
    
    TTL_HOURS = 24
    MAX_STALE_HOURS = 72
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cmc_universe_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    universe_json TEXT NOT NULL,
                    cmc_raw_count INTEGER,
                    target_count INTEGER,
                    filtered_count INTEGER,
                    eligible_count INTEGER,
                    exact_matches INTEGER,
                    base_asset_matches INTEGER,
                    ambiguous_count INTEGER,
                    no_match_count INTEGER,
                    final_count INTEGER,
                    bingx_active_contracts INTEGER,
                    fetched_at TEXT NOT NULL,
                    version_hash TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    validation_errors TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for active universe
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_active 
                ON cmc_universe_cache(is_active)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fetched_at 
                ON cmc_universe_cache(fetched_at)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _compute_version_hash(self, universe: List[Dict[str, Any]]) -> str:
        """Compute SHA256 hash of universe for deduplication."""
        content = json.dumps(universe, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()[:16]
    
    def save_snapshot(
        self,
        universe: List[Dict[str, Any]],
        cmc_raw_count: int,
        target_count: int,
        filtered_count: int,
        eligible_count: int,
        exact_matches: int,
        base_asset_matches: int,
        ambiguous_count: int,
        no_match_count: int,
        final_count: int,
        bingx_active_contracts: int,
        fetched_at: str,
        validation_status: str,
        validation_errors: List[str] = None
    ) -> int:
        """
        Save a new universe snapshot.
        
        Returns the new snapshot ID.
        """
        universe_json = json.dumps([{
            "symbol": u.get("symbol"),
            "cmc_rank": u.get("cmc_rank"),
            "name": u.get("name"),
            "slug": u.get("slug"),
            "bingx_symbol": u.get("bingx_symbol"),
            "mapping_state": u.get("mapping_state"),
            "excluded_reason": u.get("excluded_reason"),
        } for u in universe])
        
        version_hash = self._compute_version_hash(universe)
        if not fetched_at:
            fetched_at = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cmc_universe_cache (
                    universe_json, cmc_raw_count, target_count, filtered_count,
                    eligible_count, exact_matches, base_asset_matches,
                    ambiguous_count, no_match_count, final_count,
                    bingx_active_contracts, fetched_at, version_hash,
                    validation_status, validation_errors, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                universe_json, cmc_raw_count, target_count, filtered_count,
                eligible_count, exact_matches, base_asset_matches,
                ambiguous_count, no_match_count, final_count,
                bingx_active_contracts, fetched_at, version_hash,
                validation_status, json.dumps(validation_errors or [])
            ))
            snapshot_id = cursor.lastrowid
            conn.commit()
            return snapshot_id
    
    def activate_snapshot(self, snapshot_id: int) -> bool:
        """
        Atomically activate a snapshot.
        
        Uses atomic swap: deactivate old, activate new in single transaction.
        
        Returns:
            True if activation succeeded
        """
        with self._get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                
                # Deactivate all
                conn.execute("UPDATE cmc_universe_cache SET is_active = 0")
                
                # Activate new
                cursor = conn.execute(
                    "UPDATE cmc_universe_cache SET is_active = 1 WHERE id = ?",
                    (snapshot_id,)
                )
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    return False
                
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                return False
    
    def get_active_universe(self) -> Optional[List[Dict[str, Any]]]:
        """Get the currently active universe."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT universe_json FROM cmc_universe_cache 
                WHERE is_active = 1 
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return json.loads(row["universe_json"])
            return None
    
    def get_active_snapshot_meta(self) -> Optional[Dict[str, Any]]:
        """Get metadata about active universe."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM cmc_universe_cache 
                WHERE is_active = 1 
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_snapshot_age_hours(self) -> Optional[float]:
        """Get age of active snapshot in hours."""
        meta = self.get_active_snapshot_meta()
        if not meta or not meta["fetched_at"]:
            return None
        
        fetched_at = datetime.fromisoformat(meta["fetched_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        return age
    
    def is_fresh(self) -> bool:
        """Check if active universe is fresh (< 24h)."""
        age = self.get_snapshot_age_hours()
        return age is not None and age <= 24
    
    def is_stale(self) -> bool:
        """Check if active universe is stale (24-72h)."""
        age = self.get_snapshot_age_hours()
        return age is not None and 24 < age <= 72
    
    def is_expired(self) -> bool:
        """Check if active universe is expired (>72h)."""
        age = self.get_snapshot_age_hours()
        return age is not None and age > 72
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status."""
        meta = self.get_active_snapshot_meta()
        age = self.get_snapshot_age_hours()
        
        return {
            "has_active": meta is not None,
            "snapshot_age_hours": age,
            "status": "FRESH" if self.is_fresh() else ("STALE" if self.is_stale() else "EXPIRED"),
            "last_fetch": meta["fetched_at"] if meta else None,
            "universe_size": meta["final_count"] if meta else 0,
            "validation_status": meta["validation_status"] if meta else "NONE"
        }
    
    def save_fallback(self, universe: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Save last good universe to JSON fallback file."""
        data = {
            "version": "1.0",
            "universe": [
                {"symbol": u.get("symbol"), "cmc_rank": u.get("cmc_rank")}
                for u in universe
            ],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "version_hash": hashlib.sha256(
                json.dumps([u.get("symbol") for u in universe], sort_keys=True).encode()
            ).hexdigest()[:16],
            "metadata": metadata
        }
        
        # Atomic write
        tmp_path = self.FALLBACK_FILE.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.FALLBACK_FILE)
    
    def load_fallback(self) -> Optional[Dict[str, Any]]:
        """Load fallback universe if valid."""
        if not self.FALLBACK_FILE.exists():
            return None
        
        try:
            with open(self.FALLBACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check age
            fetched_at = datetime.fromisoformat(data["fetched_at"].replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
            
            if age_hours > 72:
                return None
            
            return data
        except Exception:
            return None
    
    def cleanup_old_snapshots(self, keep: int = 10) -> int:
        """Remove old inactive snapshots."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM cmc_universe_cache 
                WHERE is_active = 0 
                AND id NOT IN (
                    SELECT id FROM cmc_universe_cache 
                    WHERE is_active = 0 
                    ORDER BY created_at DESC LIMIT ?
                )
            """, (keep,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_snapshots,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count,
                    MAX(created_at) as latest_created
                FROM cmc_universe_cache
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}


# Global cache instance
_universe_cache: Optional[CMCUniverseCache] = None


def get_universe_cache() -> CMCUniverseCache:
    """Get global universe cache instance."""
    global _universe_cache
    if _universe_cache is None:
        _universe_cache = CMCUniverseCache()
    return _universe_cache


if __name__ == "__main__":
    # Quick test
    cache = CMCUniverseCache()
    print("Cache initialized")
    print(f"Status: {cache.get_status()}")
    
    # Test fallback
    fallback = cache.load_fallback()
    if fallback:
        print(f"Fallback loaded: {len(fallback.get('universe', []))} symbols")
    else:
        print("No fallback found")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())