import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

from youtube_summarizer import db
from youtube_summarizer.db import SeenVideo, _migrate, get_bootstrapped_at, set_bootstrapped, has_seen
from youtube_summarizer.fetcher import VideoMeta
from youtube_summarizer.llm import LLMOutput, PromptTier
from youtube_summarizer.pipeline import ProcessedVideo, process_video, run_once
from youtube_summarizer.transcript import TranscriptResult


def _make_video(video_id="vid001", title="Test Video"):
    return VideoMeta(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        title=title,
        published_at="2099-01-01T12:00:00Z",
        channel_name="Test Channel",
    )


def _make_settings(tmp_path):
    from youtube_summarizer.config import Settings
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    (prompts_dir / "system_preamble.md").write_text("You are an analyst.")
    (prompts_dir / "opener.md").write_text("Write {sentence_count}.\nTitle: {video_title}\n{transcript_head}")
    (prompts_dir / "summary_short.md").write_text("Summarize.\nTitle: {video_title}\n{transcript}")
    (prompts_dir / "summary_medium.md").write_text("Summarize.\nTitle: {video_title}\nBullets: {bullet_count}\n{transcript}")
    (prompts_dir / "summary_long.md").write_text("Summarize.\nTitle: {video_title}\nBullets: {bullet_count}\n{transcript}")
    (prompts_dir / "outline.md").write_text("Outline {outline_points}.\nTitle: {video_title}\n{transcript}")
    return Settings(
        email_from="test@test.com",
        email_to="to@test.com",
        gmail_app_password="pass",
        subject_prefix="[T] ",
        dry_run=False,
        ytdlp_cookies_from_browser=None,
        ytdlp_cookies_file=None,
        ollama_model="test-model",
        ollama_timeout=60,
        max_retries=1,
        data_dir=tmp_path / "data",
        prompts_dir=prompts_dir,
        parakeet_model="test-parakeet",
    )


@pytest.fixture
def pipeline_env(tmp_path):
    """Set up minimal env for pipeline tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "summaries").mkdir()

    channels_dir = tmp_path / "config"
    channels_dir.mkdir()
    channels_toml = channels_dir / "channels.toml"
    channels_toml.write_text("""
[[subscriptions]]
name = "Test Channel"
url = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
""")

    env_file = tmp_path / ".env"
    env_file.write_text("YTS_DRY_RUN=1\nYTS_EMAIL_FROM=test@test.com\nYTS_EMAIL_TO=to@test.com\nYTS_GMAIL_APP_PASSWORD=pass\n")

    return tmp_path, data_dir, channels_toml


def test_run_once_bootstrap_on_first_run(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    videos = [_make_video("vid001"), _make_video("vid002")]

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com/channel/UCxxx", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=True)

    assert result == 0  # Bootstrap run returns 0
    conn = db.connect(data_dir)
    assert get_bootstrapped_at(conn) is not None
    assert has_seen(conn, "vid001") is True
    assert has_seen(conn, "vid002") is True
    conn.close()


def test_run_once_skips_seen_videos(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    db.mark_seen(conn, SeenVideo("vid001", "https://example.com", "Ch", "T", "2026-03-20T12:00:00Z"))
    conn.close()

    videos = [_make_video("vid001")]

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=True)

    assert result == 0  # Already seen, nothing processed


def test_run_once_marks_seen_before_processing(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    conn.close()

    videos = [_make_video("vid_new")]
    mark_seen_calls = []
    original_mark_seen = db.mark_seen

    def tracking_mark_seen(conn, video):
        mark_seen_calls.append(video.video_id)
        return original_mark_seen(conn, video)

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch("youtube_summarizer.pipeline.db.mark_seen", side_effect=tracking_mark_seen), \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=True)

    assert "vid_new" in mark_seen_calls


def test_run_once_handles_processing_failure(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    conn.close()

    videos = [_make_video("vid_fail")]

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch("youtube_summarizer.pipeline.process_video", side_effect=RuntimeError("boom")), \
         patch.dict(os.environ, {"YTS_DRY_RUN": "", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=False)

    # Should not crash, should mark failed
    conn = db.connect(data_dir)
    failed = db.get_failed(conn)
    assert len(failed) == 1
    assert failed[0]["video_id"] == "vid_fail"
    conn.close()


def test_run_once_respects_limit(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    conn.close()

    videos = [_make_video(f"vid{i:03d}") for i in range(10)]

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=2, dry_run=True)

    assert result == 2


def test_run_once_dry_run_no_email(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    conn.close()

    videos = [_make_video("vid_dry")]

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=videos), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch("youtube_summarizer.pipeline.send_gmail_smtp") as mock_send, \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=True)

    mock_send.assert_not_called()


def test_process_video_returns_processed_video(tmp_path):
    settings = _make_settings(tmp_path)
    (tmp_path / "data" / "summaries").mkdir(parents=True, exist_ok=True)
    video = _make_video()

    with patch("youtube_summarizer.pipeline.fetch_duration_seconds", return_value=600), \
         patch("youtube_summarizer.pipeline.get_transcript", return_value=TranscriptResult(text="Test transcript " * 50, source="youtube_api")), \
         patch("youtube_summarizer.pipeline.generate_opener", return_value=LLMOutput(text="Opener text here.", tier=PromptTier.SHORT, attempts=1, used_fallback=False)), \
         patch("youtube_summarizer.pipeline.generate_summary", return_value=LLMOutput(text="Summary body.\n\nKey Takeaways\n- One.\n- Two.", tier=PromptTier.SHORT, attempts=1, used_fallback=False)), \
         patch("youtube_summarizer.pipeline.generate_outline", return_value=None):
        result = process_video(video, "Test Channel", settings)

    assert isinstance(result, ProcessedVideo)
    assert result.subject.startswith("[T] ")
    assert "Test Channel" in result.subject


def test_run_once_skips_pre_bootstrap_videos(pipeline_env):
    tmp_path, data_dir, channels_toml = pipeline_env
    conn = db.connect(data_dir)
    set_bootstrapped(conn)
    conn.close()

    # Video published before bootstrap
    old_video = VideoMeta(
        video_id="old_vid",
        url="https://www.youtube.com/watch?v=old_vid",
        title="Old Video",
        published_at="2020-01-01T00:00:00Z",  # Way before bootstrap
        channel_name="Test Channel",
    )

    with patch("youtube_summarizer.pipeline.repo_root", return_value=tmp_path), \
         patch("youtube_summarizer.pipeline._check_ollama", return_value=True), \
         patch("youtube_summarizer.pipeline.source_url_to_rss", return_value="https://rss.example.com"), \
         patch("youtube_summarizer.pipeline.fetch_videos_from_rss", return_value=[old_video]), \
         patch("youtube_summarizer.pipeline.load_channels") as mock_lc, \
         patch("youtube_summarizer.pipeline.process_video") as mock_process, \
         patch.dict(os.environ, {"YTS_DRY_RUN": "1", "YTS_DATA_DIR": str(data_dir)}):
        from youtube_summarizer.config import Channel
        mock_lc.return_value = [Channel(name="Test", url="https://example.com", mode="summarize", source_type="subscription")]
        result = run_once(limit=10, dry_run=True)

    # Pre-bootstrap video should be skipped (marked seen but not processed)
    mock_process.assert_not_called()
    conn = db.connect(data_dir)
    assert has_seen(conn, "old_vid") is True
    conn.close()
