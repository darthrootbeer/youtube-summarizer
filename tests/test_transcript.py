from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

from youtube_summarizer.config import Settings
from youtube_summarizer.transcript import (
    TranscriptResult,
    TranscriptUnavailableError,
    _fetch_youtube_transcript,
    get_transcript,
)


def _make_settings(tmp_path, parakeet_model="mlx-community/parakeet-tdt-0.6b-v2"):
    return Settings(
        email_from="test@example.com",
        email_to="to@example.com",
        gmail_app_password="pass",
        subject_prefix="[T] ",
        dry_run=True,
        ytdlp_cookies_from_browser=None,
        ytdlp_cookies_file=None,
        ollama_model="test-model",
        ollama_timeout=300,
        max_retries=2,
        data_dir=tmp_path,
        prompts_dir=tmp_path / "prompts",
        parakeet_model=parakeet_model,
    )


def test_get_transcript_youtube_api_success(tmp_path):
    settings = _make_settings(tmp_path)
    with patch("youtube_summarizer.transcript._fetch_youtube_transcript", return_value="Hello world transcript text."):
        result = get_transcript("vid123", "https://youtube.com/watch?v=vid123", settings)
    assert result.source == "youtube_api"
    assert result.text == "Hello world transcript text."


def test_get_transcript_falls_back_to_parakeet(tmp_path):
    settings = _make_settings(tmp_path)
    with patch("youtube_summarizer.transcript._fetch_youtube_transcript", return_value=None):
        with patch("youtube_summarizer.transcript._transcribe_with_parakeet", return_value="Parakeet transcript."):
            result = get_transcript("vid123", "https://youtube.com/watch?v=vid123", settings)
    assert result.source == "parakeet_mlx"
    assert result.text == "Parakeet transcript."


def test_get_transcript_raises_when_no_parakeet(tmp_path):
    settings = _make_settings(tmp_path, parakeet_model="")
    with patch("youtube_summarizer.transcript._fetch_youtube_transcript", return_value=None):
        with pytest.raises(TranscriptUnavailableError):
            get_transcript("vid123", "https://youtube.com/watch?v=vid123", settings)




def test_transcribe_with_parakeet_calls_subprocess(tmp_path):
    from youtube_summarizer.transcript import _transcribe_with_parakeet

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    parakeet_dir = audio_dir / "parakeet"
    parakeet_dir.mkdir(parents=True, exist_ok=True)

    # Create fake audio file that yt-dlp would create
    fake_audio = audio_dir / "vid123.m4a"
    fake_audio.write_bytes(b"fake audio")

    # Create expected parakeet output
    (parakeet_dir / "vid123.txt").write_text("Transcribed text from parakeet.")

    call_count = [0]
    def mock_run(*args, **kwargs):
        call_count[0] += 1
        cmd = args[0] if args else kwargs.get("args", [])
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("youtube_summarizer.transcript.subprocess.run", side_effect=mock_run):
        result = _transcribe_with_parakeet(
            video_id="vid123",
            video_url="https://youtube.com/watch?v=vid123",
            parakeet_model="mlx-community/parakeet-tdt-0.6b-v2",
            data_dir=tmp_path,
            ytdlp_cookies_from_browser=None,
            ytdlp_cookies_file=None,
        )
    assert result == "Transcribed text from parakeet."
    assert call_count[0] == 3  # yt-dlp, ffmpeg, parakeet-mlx
