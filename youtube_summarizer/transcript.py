from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from youtube_summarizer.config import Settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    source: str    # "youtube_api" | "parakeet_mlx"


class TranscriptUnavailableError(Exception):
    pass


def get_transcript(video_id: str, video_url: str, settings: Settings) -> TranscriptResult:
    """Try YouTube API first, fall back to Parakeet MLX transcription."""
    yt = _fetch_youtube_transcript(video_id)
    if yt:
        return TranscriptResult(text=yt, source="youtube_api")

    if not settings.parakeet_model:
        raise TranscriptUnavailableError(
            f"No YouTube transcript found for {video_id} and no parakeet model configured."
        )

    text = _transcribe_with_parakeet(
        video_id=video_id,
        video_url=video_url,
        parakeet_model=settings.parakeet_model,
        data_dir=settings.data_dir,
        ytdlp_cookies_from_browser=settings.ytdlp_cookies_from_browser,
        ytdlp_cookies_file=settings.ytdlp_cookies_file,
    )
    return TranscriptResult(text=text, source="parakeet_mlx")


def _fetch_youtube_transcript(video_id: str, preferred_languages: tuple[str, ...] = ("en",)) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import NoTranscriptFound, RequestBlocked, TranscriptsDisabled

        api = YouTubeTranscriptApi()
        parts = api.fetch(video_id, languages=list(preferred_languages))
    except Exception:
        return None

    lines = []
    for p in parts:
        text = str(getattr(p, "text", "") or "").strip()
        if text:
            lines.append(text)

    transcript = "\n".join(lines).strip()
    return transcript or None


def _transcribe_with_parakeet(
    *,
    video_id: str,
    video_url: str,
    parakeet_model: str,
    data_dir: Path,
    ytdlp_cookies_from_browser: str | None,
    ytdlp_cookies_file: str | None,
) -> str:
    audio_dir = data_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_base = audio_dir / video_id

    cookies_args: list[str] = []
    if ytdlp_cookies_file:
        cookies_args = ["--cookies", ytdlp_cookies_file]
    elif ytdlp_cookies_from_browser:
        cookies_args = ["--cookies-from-browser", ytdlp_cookies_from_browser]

    # Download audio
    subprocess.run(
        [
            "yt-dlp",
            "-f", "bestaudio[abr<=96]/bestaudio",
            "--extract-audio",
            "--audio-format", "m4a",
            "--audio-quality", "5",
            *cookies_args,
            "-o", str(out_base) + ".%(ext)s",
            video_url,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    audio_path = str(out_base) + ".m4a"
    if not Path(audio_path).exists():
        raise TranscriptUnavailableError("Audio download failed (expected .m4a output).")

    # Convert to 16kHz mono WAV
    wav_path = str(out_base) + "_16k.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            wav_path,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Run Parakeet
    parakeet_out_dir = audio_dir / "parakeet"
    parakeet_out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "parakeet-mlx",
            wav_path,
            "--model", parakeet_model,
            "--output-dir", str(parakeet_out_dir),
            "--output-format", "txt",
            "--output-template", video_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )

    txt_path = parakeet_out_dir / f"{video_id}.txt"
    transcript = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""

    # Cleanup audio files
    for p in [audio_path, wav_path]:
        try:
            Path(p).unlink()
        except OSError:
            pass

    if not transcript:
        raise TranscriptUnavailableError("Parakeet returned empty transcript.")

    return transcript
