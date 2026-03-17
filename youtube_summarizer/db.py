from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeenVideo:
    video_id: str
    video_url: str
    channel_name: str
    video_title: str
    published_at: str


def db_path(repo_root: Path) -> Path:
    return repo_root / "data" / "state.db"


def connect(repo_root: Path) -> sqlite3.Connection:
    path = db_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
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
    conn.commit()


def has_seen(conn: sqlite3.Connection, video_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM seen_videos WHERE video_id = ? LIMIT 1", (video_id,)).fetchone()
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

