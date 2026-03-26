from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

from youtube_summarizer.fetcher import (
    VideoMeta,
    fetch_duration_seconds,
    fetch_videos_from_rss,
    source_url_to_rss,
    strip_hashtags,
)


def test_source_url_to_rss_channel_id():
    url = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
    result = source_url_to_rss(url)
    assert result == "https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx"


def test_source_url_to_rss_playlist():
    url = "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxx"
    result = source_url_to_rss(url)
    assert result == "https://www.youtube.com/feeds/videos.xml?playlist_id=PLxxxxxxxxxxxxxxxxxx"


def test_source_url_to_rss_invalid():
    assert source_url_to_rss("https://example.com/not-youtube") is None


def test_fetch_videos_from_rss_parses_entries():
    mock_entry = SimpleNamespace(
        link="https://www.youtube.com/watch?v=abc123def",
        title="Test Video Title #hashtag",
        published="2025-01-15T12:00:00Z",
        yt_videoid="abc123def",
        author_detail=SimpleNamespace(name="Test Channel"),
    )
    mock_feed = SimpleNamespace(entries=[mock_entry])
    with patch("youtube_summarizer.fetcher.feedparser.parse", return_value=mock_feed):
        videos = fetch_videos_from_rss("https://example.com/rss")
    assert len(videos) == 1
    assert videos[0].video_id == "abc123def"
    assert videos[0].title == "Test Video Title"
    assert videos[0].channel_name == "Test Channel"


def test_fetch_videos_from_rss_empty():
    mock_feed = SimpleNamespace(entries=[])
    with patch("youtube_summarizer.fetcher.feedparser.parse", return_value=mock_feed):
        videos = fetch_videos_from_rss("https://example.com/rss")
    assert videos == []


def test_fetch_videos_from_rss_limit():
    entries = []
    for i in range(10):
        entries.append(SimpleNamespace(
            link=f"https://www.youtube.com/watch?v=vid{i:03d}xxx",
            title=f"Video {i}",
            published="2025-01-15T12:00:00Z",
            yt_videoid=f"vid{i:03d}xxx",
            author_detail=SimpleNamespace(name="Ch"),
        ))
    mock_feed = SimpleNamespace(entries=entries)
    with patch("youtube_summarizer.fetcher.feedparser.parse", return_value=mock_feed):
        videos = fetch_videos_from_rss("https://example.com/rss", limit=3)
    assert len(videos) == 3


def test_fetch_duration_seconds_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "300\n"
    with patch("youtube_summarizer.fetcher.subprocess.run", return_value=mock_result):
        result = fetch_duration_seconds("https://youtube.com/watch?v=test")
    assert result == 300


def test_fetch_duration_seconds_failure():
    with patch("youtube_summarizer.fetcher.subprocess.run", side_effect=Exception("fail")):
        result = fetch_duration_seconds("https://youtube.com/watch?v=test")
    assert result is None
