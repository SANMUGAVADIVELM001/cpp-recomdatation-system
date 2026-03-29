"""SQLite-backed local storage for caching API data and user progress."""

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from config import DATABASE_PATH


class Database:
    """Manages all local persistence via SQLite."""

    def __init__(self, db_path: str = DATABASE_PATH) -> None:
        self._path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cf_users (
                    handle TEXT PRIMARY KEY,
                    data   TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS lc_users (
                    username TEXT PRIMARY KEY,
                    data     TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cf_submissions (
                    handle     TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    verdict    TEXT NOT NULL,
                    timestamp  INTEGER NOT NULL,
                    language   TEXT,
                    PRIMARY KEY (handle, problem_id, timestamp)
                );

                CREATE TABLE IF NOT EXISTS lc_solved (
                    username   TEXT NOT NULL,
                    title_slug TEXT NOT NULL,
                    PRIMARY KEY (username, title_slug)
                );

                CREATE TABLE IF NOT EXISTS cf_rating_history (
                    handle       TEXT NOT NULL,
                    contest_id   INTEGER NOT NULL,
                    contest_name TEXT,
                    rank         INTEGER,
                    old_rating   INTEGER,
                    new_rating   INTEGER,
                    timestamp    INTEGER,
                    PRIMARY KEY (handle, contest_id)
                );

                CREATE TABLE IF NOT EXISTS progress_goals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform    TEXT NOT NULL,
                    username    TEXT NOT NULL,
                    goal_type   TEXT NOT NULL,
                    target      INTEGER NOT NULL,
                    start_date  TEXT NOT NULL,
                    end_date    TEXT,
                    completed   INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS daily_log (
                    platform   TEXT NOT NULL,
                    username   TEXT NOT NULL,
                    date       TEXT NOT NULL,
                    solved     INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (platform, username, date)
                );
                """
            )

    # ------------------------------------------------------------------
    # Codeforces user cache
    # ------------------------------------------------------------------

    def save_cf_user(self, handle: str, data: dict, timestamp: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cf_users VALUES (?, ?, ?)",
                (handle, json.dumps(data), timestamp),
            )

    def load_cf_user(self, handle: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data FROM cf_users WHERE handle = ?", (handle,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    # ------------------------------------------------------------------
    # LeetCode user cache
    # ------------------------------------------------------------------

    def save_lc_user(self, username: str, data: dict, timestamp: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lc_users VALUES (?, ?, ?)",
                (username, json.dumps(data), timestamp),
            )

    def load_lc_user(self, username: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data FROM lc_users WHERE username = ?", (username,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    # ------------------------------------------------------------------
    # Codeforces submissions
    # ------------------------------------------------------------------

    def save_cf_submissions(
        self, handle: str, submissions: List[Dict]
    ) -> None:
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO cf_submissions
                    (handle, problem_id, verdict, timestamp, language)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        handle,
                        s["problem_id"],
                        s["verdict"],
                        s["timestamp"],
                        s.get("language", ""),
                    )
                    for s in submissions
                ],
            )

    def get_cf_accepted_ids(self, handle: str) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT problem_id
                FROM cf_submissions
                WHERE handle = ? AND verdict = 'OK'
                """,
                (handle,),
            ).fetchall()
        return [r["problem_id"] for r in rows]

    def get_cf_submissions(self, handle: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cf_submissions WHERE handle = ? ORDER BY timestamp DESC",
                (handle,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # LeetCode solved
    # ------------------------------------------------------------------

    def save_lc_solved(self, username: str, slugs: List[str]) -> None:
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO lc_solved VALUES (?, ?)",
                [(username, s) for s in slugs],
            )

    def get_lc_solved(self, username: str) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT title_slug FROM lc_solved WHERE username = ?",
                (username,),
            ).fetchall()
        return [r["title_slug"] for r in rows]

    # ------------------------------------------------------------------
    # Codeforces rating history
    # ------------------------------------------------------------------

    def save_cf_rating_history(
        self, handle: str, history: List[Dict]
    ) -> None:
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO cf_rating_history
                    (handle, contest_id, contest_name, rank,
                     old_rating, new_rating, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        handle,
                        e["contest_id"],
                        e["contest_name"],
                        e["rank"],
                        e["old_rating"],
                        e["new_rating"],
                        e["timestamp"],
                    )
                    for e in history
                ],
            )

    def get_cf_rating_history(self, handle: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM cf_rating_history
                WHERE handle = ?
                ORDER BY timestamp ASC
                """,
                (handle,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Progress goals
    # ------------------------------------------------------------------

    def add_goal(
        self,
        platform: str,
        username: str,
        goal_type: str,
        target: int,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO progress_goals
                    (platform, username, goal_type, target, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (platform, username, goal_type, target, start_date, end_date),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def get_goals(self, platform: str, username: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM progress_goals WHERE platform = ? AND username = ?",
                (platform, username),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_goal_completed(self, goal_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE progress_goals SET completed = 1 WHERE id = ?",
                (goal_id,),
            )

    # ------------------------------------------------------------------
    # Daily log
    # ------------------------------------------------------------------

    def log_daily_solved(
        self, platform: str, username: str, date: str, count: int
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO daily_log (platform, username, date, solved)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(platform, username, date)
                DO UPDATE SET solved = excluded.solved
                """,
                (platform, username, date, count),
            )

    def get_daily_log(self, platform: str, username: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM daily_log
                WHERE platform = ? AND username = ?
                ORDER BY date ASC
                """,
                (platform, username),
            ).fetchall()
        return [dict(r) for r in rows]
