"""SQLite checkpoint: the collector's resumable state and the raw input to the Kedro pipelines."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DDL = """
CREATE TABLE IF NOT EXISTS candidates (
    steamid TEXT PRIMARY KEY,
    playtime_forever INTEGER,
    review_filter TEXT,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending|public|private|no_stats|error
    detail TEXT,
    discovered_at INTEGER
);
CREATE TABLE IF NOT EXISTS players (
    steamid TEXT PRIMARY KEY,
    playtime_forever INTEGER,
    achievements_json TEXT NOT NULL,         -- {apiname: unlocktime} for achieved == 1
    fetched_at INTEGER
);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS seen_reviews (recommendationid TEXT PRIMARY KEY);
CREATE INDEX IF NOT EXISTS idx_cand_status ON candidates(status);
"""


class Checkpoint:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(DDL)

    def get(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT OR REPLACE INTO state VALUES (?, ?)", (key, json.dumps(value)))
        self.conn.commit()

    def bump(self, key: str, n: int = 1) -> None:
        self.put(key, self.get(key, 0) + n)

    def add_candidates(self, rows: list[tuple[str, int]], review_filter: str) -> int:
        now = int(time.time())
        cur = self.conn.executemany(
            "INSERT OR IGNORE INTO candidates (steamid, playtime_forever, review_filter, discovered_at) "
            "VALUES (?, ?, ?, ?)",
            [(sid, pt, review_filter, now) for sid, pt in rows],
        )
        self.conn.commit()
        return cur.rowcount

    def mark_reviews_seen(self, ids: list[str]) -> int:
        cur = self.conn.executemany("INSERT OR IGNORE INTO seen_reviews VALUES (?)", [(i,) for i in ids])
        self.conn.commit()
        return cur.rowcount

    def pending(self, limit: int) -> list[tuple[str, int]]:
        return self.conn.execute(
            "SELECT steamid, playtime_forever FROM candidates WHERE status='pending' LIMIT ?", (limit,)
        ).fetchall()

    def record(self, steamid: str, playtime: int, status: str, detail: str | None,
               achievements: dict[str, int] | None) -> None:
        with self.conn:
            if achievements is not None:
                self.conn.execute(
                    "INSERT OR REPLACE INTO players VALUES (?, ?, ?, ?)",
                    (steamid, playtime, json.dumps(achievements), int(time.time())),
                )
            self.conn.execute(
                "UPDATE candidates SET status=?, detail=? WHERE steamid=?", (status, detail, steamid)
            )

    def requeue(self, steamids: list[str]) -> None:
        with self.conn:
            self.conn.executemany("UPDATE candidates SET status='pending', detail=NULL WHERE steamid=?",
                                  [(s,) for s in steamids])

    def requeue_errors(self) -> int:
        with self.conn:
            return self.conn.execute(
                "UPDATE candidates SET status='pending', detail=NULL WHERE status='error'").rowcount

    def status_counts(self) -> dict[str, int]:
        return dict(self.conn.execute("SELECT status, COUNT(*) FROM candidates GROUP BY status").fetchall())

    def players(self) -> list[tuple[str, int, dict[str, int]]]:
        return [(s, p, json.loads(a)) for s, p, a in
                self.conn.execute("SELECT steamid, playtime_forever, achievements_json FROM players")]
