import sqlite3
from datetime import datetime, timezone

import pytest

from youtube_summarizer.db import (
    SeenVideo,
    _migrate,
    clear_failed,
    connect,
    get_bootstrapped_at,
    get_failed,
    has_seen,
    mark_failed,
    mark_seen,
    set_bootstrapped,
)


def test_connect_creates_tables(tmp_path):
    conn = connect(tmp_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "seen_videos" in tables
    assert "failed_videos" in tables
    assert "meta" in tables
    conn.close()


def test_has_seen_false_initially(in_memory_db):
    assert has_seen(in_memory_db, "abc123") is False


def test_mark_seen_and_has_seen(in_memory_db):
    v = SeenVideo(video_id="abc123", video_url="https://youtube.com/watch?v=abc123",
                  channel_name="Test", video_title="Test Title", published_at="2025-01-01T00:00:00Z")
    mark_seen(in_memory_db, v)
    assert has_seen(in_memory_db, "abc123") is True


def test_mark_seen_idempotent(in_memory_db):
    v = SeenVideo(video_id="abc123", video_url="https://youtube.com/watch?v=abc123",
                  channel_name="Test", video_title="Test Title", published_at="2025-01-01T00:00:00Z")
    mark_seen(in_memory_db, v)
    mark_seen(in_memory_db, v)  # Should not raise
    assert has_seen(in_memory_db, "abc123") is True


def test_mark_failed(in_memory_db):
    mark_failed(in_memory_db, "vid1", "Channel", "Title", "https://example.com", "timeout error")
    failed = get_failed(in_memory_db)
    assert len(failed) == 1
    assert failed[0]["video_id"] == "vid1"
    assert failed[0]["error"] == "timeout error"


def test_get_failed_empty(in_memory_db):
    assert get_failed(in_memory_db) == []


def test_clear_failed(in_memory_db):
    mark_failed(in_memory_db, "vid1", "Channel", "Title", "https://example.com", "error")
    clear_failed(in_memory_db, "vid1")
    assert get_failed(in_memory_db) == []


def test_mark_failed_replaces(in_memory_db):
    mark_failed(in_memory_db, "vid1", "Channel", "Title", "https://example.com", "error1")
    mark_failed(in_memory_db, "vid1", "Channel", "Title", "https://example.com", "error2")
    failed = get_failed(in_memory_db)
    assert len(failed) == 1
    assert failed[0]["error"] == "error2"


def test_bootstrapped_at_none_initially(in_memory_db):
    assert get_bootstrapped_at(in_memory_db) is None


def test_set_bootstrapped(in_memory_db):
    set_bootstrapped(in_memory_db)
    assert get_bootstrapped_at(in_memory_db) is not None


def test_set_bootstrapped_idempotent(in_memory_db):
    set_bootstrapped(in_memory_db)
    first = get_bootstrapped_at(in_memory_db)
    set_bootstrapped(in_memory_db)
    second = get_bootstrapped_at(in_memory_db)
    assert first == second


def test_v1_to_v2_auto_bootstrap():
    """If seen_videos has rows but meta has no bootstrapped_at, migration auto-inserts it."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create only the v1 table
    conn.execute("""
        CREATE TABLE seen_videos (
          video_id TEXT PRIMARY KEY,
          video_url TEXT NOT NULL,
          channel_name TEXT NOT NULL,
          video_title TEXT NOT NULL,
          published_at TEXT NOT NULL,
          first_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.execute(
        "INSERT INTO seen_videos (video_id, video_url, channel_name, video_title, published_at) VALUES (?, ?, ?, ?, ?)",
        ("vid1", "https://example.com", "Ch", "Title", "2025-01-01"),
    )
    conn.commit()

    # Now run migration — should auto-create bootstrapped_at
    _migrate(conn)
    row = conn.execute("SELECT value FROM meta WHERE key = 'bootstrapped_at'").fetchone()
    assert row is not None
    conn.close()
