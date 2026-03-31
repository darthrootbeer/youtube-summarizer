from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from youtube_summarizer import db
from youtube_summarizer.artifacts import write_artifact
from youtube_summarizer.config import Settings, load_channels, load_dotenv, load_settings, repo_root
from youtube_summarizer.email_builder import build_email
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.fetcher import VideoMeta, fetch_duration_seconds, fetch_videos_from_rss, source_url_to_rss, strip_hashtags
from youtube_summarizer.llm import LLMOutput, generate_opener, generate_outline, generate_summary
from youtube_summarizer.transcript import TranscriptResult, TranscriptUnavailableError, get_transcript

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessedVideo:
    video: VideoMeta
    channel_name: str
    transcript: TranscriptResult
    opener: LLMOutput
    summary: LLMOutput
    outline: LLMOutput | None
    email_html: str
    email_text: str
    subject: str


def _setup_logging(debug: bool = False) -> None:
    level_name = "DEBUG" if debug else os.environ.get("YTS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def _check_ollama() -> bool:
    """Returns True if Ollama is reachable."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        return resp.status_code == 200
    except Exception as e:
        log.error("Ollama health check failed: %s", e)
        return False


def run_once(limit: int = 10, dry_run: bool = False, debug: bool = False) -> int:
    """Main entry point. Loads config, polls channels, processes new videos."""
    load_dotenv(repo_root() / ".env")
    if dry_run:
        os.environ["YTS_DRY_RUN"] = "1"
    if debug:
        os.environ["YTS_LOG_LEVEL"] = "DEBUG"
    _setup_logging(debug)

    settings = load_settings()
    channels = load_channels()
    if not channels:
        raise RuntimeError("No channels configured. Add entries to config/channels.toml.")

    if not _check_ollama():
        log.error("Ollama is not reachable at localhost:11434. Aborting.")
        return 0

    log.info("run_once: %d source(s), limit=%d, dry_run=%s, model=%s",
             len(channels), limit, settings.dry_run, settings.ollama_model)

    conn = db.connect(settings.data_dir)
    bootstrapped_at = db.get_bootstrapped_at(conn)

    # Bootstrap: mark all current videos as seen, don't send emails
    if not bootstrapped_at:
        log.info("First run — bootstrapping (marking existing videos as seen)")
        for ch in channels:
            rss = source_url_to_rss(ch.url)
            if not rss:
                log.warning("Could not build RSS URL for %s — skipping", ch.url)
                continue
            videos = fetch_videos_from_rss(rss, limit=30)
            channel_name = ch.name or ch.url
            for v in videos:
                if not db.has_seen(conn, v.video_id):
                    db.mark_seen(conn, db.SeenVideo(
                        video_id=v.video_id,
                        video_url=v.url,
                        channel_name=channel_name,
                        video_title=v.title,
                        published_at=v.published_at,
                    ))
            log.info("[bootstrap] %s: marked %d existing video(s) as seen", channel_name, len(videos))
        db.set_bootstrapped(conn)
        log.info("Bootstrap complete. Next run will process new videos.")
        conn.close()
        return 0

    processed = 0
    remaining = max(1, limit)

    for ch in channels:
        if remaining <= 0:
            break

        rss = source_url_to_rss(ch.url)
        if not rss:
            log.warning("Could not build RSS URL for %s — skipping", ch.url)
            continue

        channel_name = ch.name or ch.url
        videos = fetch_videos_from_rss(rss, limit=30)
        log.debug("RSS: '%s' returned %d video(s)", channel_name, len(videos))

        for v in videos:
            if remaining <= 0:
                break
            if db.has_seen(conn, v.video_id):
                continue
            # Pre-bootstrap guard
            if v.published_at and v.published_at < bootstrapped_at:
                log.info("  skip (pre-bootstrap): %s", v.title)
                db.mark_seen(conn, db.SeenVideo(
                    video_id=v.video_id,
                    video_url=v.url,
                    channel_name=channel_name,
                    video_title=v.title,
                    published_at=v.published_at,
                ))
                continue

            # Mark seen IMMEDIATELY before processing
            db.mark_seen(conn, db.SeenVideo(
                video_id=v.video_id,
                video_url=v.url,
                channel_name=channel_name,
                video_title=v.title,
                published_at=v.published_at,
            ))

            if settings.dry_run:
                log.info("  [dry-run] would process: %s — %s", channel_name, v.title)
                remaining -= 1
                processed += 1
                continue

            try:
                result = process_video(v, channel_name, settings)
                # Write artifact
                write_artifact(
                    video_id=v.video_id,
                    channel_name=channel_name,
                    video_title=v.title,
                    video_url=v.url,
                    opener_text=result.opener.text,
                    summary_text=result.summary.text,
                    outline_text=result.outline.text if result.outline else None,
                    transcript_source=result.transcript.source,
                    data_dir=settings.data_dir,
                )
                # Send email
                send_gmail_smtp(
                    email_from=settings.email_from,
                    email_to=settings.email_to,
                    gmail_app_password=settings.gmail_app_password,
                    content=EmailContent(
                        subject=result.subject,
                        text=result.email_text,
                        html=result.email_html,
                    ),
                )
                log.info("  done: %s — %s", channel_name, v.title)
            except Exception as e:
                log.error("  FAILED: %s — %s: %s", channel_name, v.title, e)
                db.mark_failed(conn, v.video_id, channel_name, v.title, v.url, str(e))

            remaining -= 1
            processed += 1

    log.info("run_once complete: processed %d video(s)", processed)
    conn.close()
    return processed


def process_video(
    video: VideoMeta,
    channel_name: str,
    settings: Settings,
) -> ProcessedVideo:
    """Process a single video end-to-end."""
    duration_s = fetch_duration_seconds(video.url)
    transcript = get_transcript(video.video_id, video.url, settings)

    llm_kwargs = dict(
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
        max_retries=settings.max_retries,
        prompts_dir=settings.prompts_dir,
    )

    opener = generate_opener(
        transcript.text, video.title, duration_s, **llm_kwargs,
    )
    summary = generate_summary(
        transcript.text, video.title, duration_s, **llm_kwargs,
    )
    outline = generate_outline(
        transcript.text, video.title, None, video.url, duration_s, **llm_kwargs,
    )

    template_dir = Path(__file__).resolve().parent / "templates"
    subject, html, text = build_email(
        channel_name=channel_name,
        video=video,
        opener=opener,
        summary=summary,
        outline=outline,
        transcript_source=transcript.source,
        subject_prefix=settings.subject_prefix,
        template_dir=template_dir,
        duration_s=duration_s,
    )

    return ProcessedVideo(
        video=video,
        channel_name=channel_name,
        transcript=transcript,
        opener=opener,
        summary=summary,
        outline=outline,
        email_html=html,
        email_text=text,
        subject=subject,
    )


def force_process_video(video_id: str, *, dry_run: bool = False, debug: bool = False) -> None:
    """Force-process a single video by ID, bypassing the seen check."""
    load_dotenv(repo_root() / ".env")
    if debug:
        os.environ["YTS_LOG_LEVEL"] = "DEBUG"
    _setup_logging(debug)

    settings = load_settings()

    if not _check_ollama():
        log.error("Ollama is not reachable at localhost:11434. Aborting.")
        return

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    log.info("force: fetching metadata for %s", video_url)

    # Fetch title and channel name via yt-dlp
    import subprocess
    env = dict(os.environ)
    brew_bin = "/opt/homebrew/bin"
    if brew_bin not in env.get("PATH", ""):
        env["PATH"] = f"{brew_bin}:{env.get('PATH', '')}"
    res = subprocess.run(
        ["yt-dlp", "--print", "%(title)s\t%(uploader)s\t%(upload_date)s", "--no-download", video_url],
        capture_output=True, text=True, timeout=30, env=env,
    )
    if res.returncode != 0 or not res.stdout.strip():
        log.error("yt-dlp could not fetch metadata for %s: %s", video_id, res.stderr.strip())
        return

    parts = res.stdout.strip().split("\t")
    title = strip_hashtags(parts[0]) if len(parts) > 0 else video_id
    channel_name = parts[1] if len(parts) > 1 else "Unknown"
    raw_date = parts[2] if len(parts) > 2 else ""
    published_at = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else ""

    video = VideoMeta(
        video_id=video_id,
        url=video_url,
        title=title,
        published_at=published_at,
        channel_name=channel_name,
    )

    log.info("force: processing '%s' by %s", title, channel_name)

    if dry_run:
        log.info("force: [dry-run] skipping actual processing")
        return

    result = process_video(video, channel_name, settings)

    write_artifact(
        video_id=video_id,
        channel_name=channel_name,
        video_title=title,
        video_url=video_url,
        opener_text=result.opener.text,
        summary_text=result.summary.text,
        outline_text=result.outline.text if result.outline else None,
        transcript_source=result.transcript.source,
        data_dir=settings.data_dir,
    )
    send_gmail_smtp(
        email_from=settings.email_from,
        email_to=settings.email_to,
        gmail_app_password=settings.gmail_app_password,
        content=EmailContent(
            subject=result.subject,
            text=result.email_text,
            html=result.email_html,
        ),
    )
    log.info("force: done — email sent for '%s'", title)


def run_forever(*, poll_seconds: int = 900, limit: int = 10, debug: bool = False) -> None:
    load_dotenv(repo_root() / ".env")
    _setup_logging(debug)
    log.info("Starting watch loop (poll_seconds=%d, limit=%d)", poll_seconds, limit)
    while True:
        n = run_once(limit=limit, debug=debug)
        if n <= 0:
            log.debug("No new videos found — sleeping %ds", poll_seconds)
            time.sleep(max(5, int(poll_seconds)))
