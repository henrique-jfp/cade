import json
import sqlite3
from datetime import datetime, timedelta, timezone


class CacheRepository:
    def __init__(self, db_path: str, ttl_minutes: int = 30):
        self.db_path = db_path
        self.ttl_minutes = ttl_minutes
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rd_cache (
                    infohash TEXT PRIMARY KEY,
                    is_cached INTEGER NOT NULL,
                    payload TEXT,
                    checked_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_many(self, hashes: list[str]) -> dict[str, dict]:
        if not hashes:
            return {}
        placeholders = ",".join(["?"] * len(hashes))
        with self._connect() as conn:
            cur = conn.execute(
                f"SELECT infohash, is_cached, payload, checked_at FROM rd_cache WHERE infohash IN ({placeholders})",
                hashes,
            )
            rows = cur.fetchall()

        now = datetime.now(timezone.utc)
        output: dict[str, dict] = {}
        for infohash, is_cached, payload, checked_at in rows:
            try:
                checked_dt = datetime.fromisoformat(checked_at)
            except ValueError:
                continue

            if now - checked_dt > timedelta(minutes=self.ttl_minutes):
                continue

            output[infohash] = {
                "is_cached": bool(is_cached),
                "payload": json.loads(payload) if payload else {},
                "checked_at": checked_at,
            }
        return output

    def upsert_many(self, values: dict[str, dict]):
        if not values:
            return

        checked_at = datetime.now(timezone.utc).isoformat()
        rows = []
        for infohash, data in values.items():
            rows.append(
                (
                    infohash,
                    1 if data.get("is_cached") else 0,
                    json.dumps(data.get("payload", {})),
                    checked_at,
                )
            )

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO rd_cache (infohash, is_cached, payload, checked_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(infohash) DO UPDATE SET
                  is_cached=excluded.is_cached,
                  payload=excluded.payload,
                  checked_at=excluded.checked_at
                """,
                rows,
            )
            conn.commit()
