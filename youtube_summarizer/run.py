from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from youtube_summarizer import db
from youtube_summarizer.config import load_channels, load_settings, repo_root
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.summarizer import summarize_fallback, summarize_with_ollama
from youtube_summarizer.youtube import fetch_latest_videos_from_rss, fetch_youtube_transcript, source_url_to_rss


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    source: str  # "youtube" | "macwhisper"


def run_once(limit: int = 10) -> None:
    _load_dotenv_if_present(repo_root() / ".env")

    settings = load_settings()
    channels = load_channels()
    if not channels:
        raise RuntimeError("No channels configured. Add entries to config/channels.toml.")

    root = repo_root()
    env = Environment(
        loader=FileSystemLoader(str(root / "youtube_summarizer" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("email.html.j2")

    with db.connect(root) as conn:
        remaining = max(1, limit)

        for ch in channels:
            if remaining <= 0:
                break

            rss = source_url_to_rss(ch.url)
            if not rss:
                # Skip quietly; config format is designed to avoid API keys.
                continue

            videos = fetch_latest_videos_from_rss(rss, limit=min(10, remaining))
            for v in videos:
                if remaining <= 0:
                    break
                if db.has_seen(conn, v.video_id):
                    continue

                transcript = _get_transcript(v.video_id, v.url, settings.macwhisper_cmd, root)
                summary = _summarize(transcript.text, settings.ollama_model)

                subject = f"{settings.subject_prefix}{ch.name} — {v.title}"
                html = template.render(
                    subject=subject,
                    channel_name=ch.name,
                    video_title=v.title,
                    video_url=v.url,
                    summary=summary,
                    transcript_source=transcript.source,
                    published_at=v.published_at,
                )

                text = f"{ch.name}\n{v.title}\n{v.url}\n\nSummary:\n{summary}\n\nTranscript source: {transcript.source}\n"

                send_gmail_smtp(
                    email_from=settings.email_from,
                    email_to=settings.email_to,
                    gmail_app_password=settings.gmail_app_password,
                    content=EmailContent(subject=subject, text=text, html=html),
                )

                db.mark_seen(
                    conn,
                    db.SeenVideo(
                        video_id=v.video_id,
                        video_url=v.url,
                        channel_name=ch.name,
                        video_title=v.title,
                        published_at=v.published_at,
                    ),
                )
                remaining -= 1


def _summarize(transcript: str, ollama_model: str | None) -> str:
    if ollama_model:
        try:
            out = summarize_with_ollama(transcript=transcript, model=ollama_model)
            if out:
                return out
        except Exception:
            # If Ollama is temporarily unavailable, we still send *something*.
            pass
    return summarize_fallback(transcript)


def _get_transcript(video_id: str, video_url: str, macwhisper_cmd: str | None, root: Path) -> TranscriptResult:
    yt = fetch_youtube_transcript(video_id)
    if yt:
        return TranscriptResult(text=yt, source="youtube")

    if not macwhisper_cmd:
        raise RuntimeError(
            "No YouTube transcript found, and MacWhisper CLI is not configured. "
            "Set YTS_MACWHISPER_CMD in .env once we confirm your MacWhisper CLI path."
        )

    audio_dir = root / "data" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_base = audio_dir / f"{video_id}"

    # Download audio
    _run(
        [
            "yt-dlp",
            "-f",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "m4a",
            "-o",
            str(out_base) + ".%(ext)s",
            video_url,
        ]
    )

    audio_path = str(out_base) + ".m4a"
    if not Path(audio_path).exists():
        raise RuntimeError("Audio download failed (expected .m4a output).")

    # Transcribe via MacWhisper CLI (command varies by install; we keep this pluggable)
    # Expected behavior: command outputs a transcript file or prints transcript to stdout.
    transcript_text = _run_capture([macwhisper_cmd, audio_path]).strip()
    if not transcript_text:
        raise RuntimeError("MacWhisper CLI returned empty transcript.")
    return TranscriptResult(text=transcript_text, source="macwhisper")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _run_capture(cmd: list[str]) -> str:
    res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout or ""


def _load_dotenv_if_present(path: Path) -> None:
    # Minimal .env loader so you can run locally without extra deps.
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

