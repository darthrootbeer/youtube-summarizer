from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SeenVideo:
    video_id: str
    video_url: str
    channel_name: str
    video_title: str
    published_at: str


def connect(data_dir: Path) -> sqlite3.Connection:
    db_file = data_dir / "state.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_videos (
          video_id TEXT PRIMARY KEY,
          video_url TEXT NOT NULL,
          channel_name TEXT NOT NULL,
          video_title TEXT NOT NULL,
          published_at TEXT NOT NULL,
          first_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS failed_videos (
          video_id TEXT PRIMARY KEY,
          channel_name TEXT NOT NULL,
          video_title TEXT NOT NULL,
          video_url TEXT NOT NULL,
          failed_at TEXT NOT NULL DEFAULT (datetime('now')),
          error TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        """
    )
    conn.commit()

    # v1 -> v2 auto-bootstrap: if seen_videos has rows but meta has no
    # bootstrapped_at, the user upgraded from v1 and we should not
    # re-bootstrap (which would re-send emails for all existing videos).
    row = conn.execute("SELECT 1 FROM seen_videos LIMIT 1").fetchone()
    if row is not None:
        ba = conn.execute(
            "SELECT 1 FROM meta WHERE key = 'bootstrapped_at' LIMIT 1"
        ).fetchone()
        if ba is None:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)",
                ("bootstrapped_at", now),
            )
            conn.commit()


def has_seen(conn: sqlite3.Connection, video_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_videos WHERE video_id = ? LIMIT 1", (video_id,)
    ).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, video: SeenVideo) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO seen_videos
          (video_id, video_url, channel_name, video_title, published_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (video.video_id, video.video_url, video.channel_name, video.video_title, video.published_at),
    )
    conn.commit()


def mark_failed(
    conn: sqlite3.Connection,
    video_id: str,
    channel_name: str,
    video_title: str,
    video_url: str,
    error: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO failed_videos
          (video_id, channel_name, video_title, video_url, error)
        VALUES (?, ?, ?, ?, ?)
        """,
        (video_id, channel_name, video_title, video_url, error),
    )
    conn.commit()


def get_failed(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT video_id, channel_name, video_title, video_url, failed_at, error FROM failed_videos"
    ).fetchall()
    return [dict(r) for r in rows]


def clear_failed(conn: sqlite3.Connection, video_id: str) -> None:
    conn.execute("DELETE FROM failed_videos WHERE video_id = ?", (video_id,))
    conn.commit()


def get_bootstrapped_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'bootstrapped_at' LIMIT 1"
    ).fetchone()
    return row["value"] if row else None


def set_bootstrapped(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)",
        ("bootstrapped_at", now),
    )
    conn.commit()
