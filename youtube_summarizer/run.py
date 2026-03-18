from __future__ import annotations

import logging
import os
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from uuid import uuid4

log = logging.getLogger("youtube_summarizer")


def setup_logging() -> None:
    """Configure logging from YTS_LOG_LEVEL env var (default INFO, DEBUG for full audit trail)."""
    level_name = os.environ.get("YTS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    log.debug("Logging initialised at level %s", level_name)

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
import re

from youtube_summarizer import db
from youtube_summarizer.db import has_bootstrapped, mark_bootstrapped
from youtube_summarizer.config import (
    load_channels,
    load_process_prompts,
    load_settings,
    load_transcribe_options,
    load_transcribe_prompts,
    repo_root,
)
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.summarizer import summarize_fallback, summarize_with_ollama
from youtube_summarizer.youtube import (
    fetch_channel_title_from_rss,
    fetch_latest_videos_from_rss,
    fetch_youtube_transcript,
    source_url_to_rss,
)


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    source: str  # "youtube" | "macwhisper" (fallback can be whisper.cpp)

@dataclass(frozen=True)
class BetaStats:
    video_id: str
    summary_id: str
    transcript_source: str
    ollama_model: str | None
    enabled_prompts: list[str]
    rss_fetch_ms: int | None
    audio_download_ms: int | None
    audio_bytes: int | None
    transcribe_ms: int | None
    summarize_ms: int | None  # total summarize time (all prompts)
    email_render_ms: int | None
    email_send_ms: int | None
    total_ms: int


def run_once(limit: int = 10) -> int:
    _load_dotenv_if_present(repo_root() / ".env")
    setup_logging()

    settings = load_settings()
    channels = load_channels()
    process_prompts = load_process_prompts()
    all_enabled_prompts = [p for p in process_prompts if p.enabled]
    if not channels:
        raise RuntimeError("No channels configured. Add entries to config/channels.toml.")

    log.info("run_once: %d source(s) configured, limit=%d, dry_run=%s, ollama=%s",
             len(channels), limit, settings.dry_run, settings.ollama_model or "off")
    log.debug("Enabled summarize prompts: %s", [p.key for p in all_enabled_prompts])

    root = repo_root()
    _cleanup_downloads(root)
    env = Environment(
        loader=FileSystemLoader(str(root / "youtube_summarizer" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("email.html.j2")

    processed = 0
    with db.connect(root) as conn:
        remaining = max(1, limit)

        for ch in channels:
            if remaining <= 0:
                break
            mode = ch.mode
            mode_filter = os.environ.get("YTS_MODE_FILTER", "").strip().lower()
            if mode_filter and mode != mode_filter:
                log.debug("Skipping %s (mode filter: %s != %s)", ch.url, mode, mode_filter)
                continue

            log.debug("Checking source: [%s] %s (%s)", ch.source_type, ch.name or ch.url, mode)

            rss = source_url_to_rss(ch.url)
            if not rss:
                log.warning("Could not build RSS URL for %s — skipping", ch.url)
                continue

            channel_title = fetch_channel_title_from_rss(rss)
            effective_channel_name = (ch.name or "").strip() or (channel_title or "").strip() or ch.url
            if (not ch.name) and channel_title:
                _best_effort_update_channel_name_in_config(
                    config_path=repo_root() / "config" / "channels.toml",
                    url=ch.url,
                    name=channel_title,
                )

            # During beta, scan deeper into the RSS feed so we reliably find an unseen video.
            t_rss = time.perf_counter()
            videos = fetch_latest_videos_from_rss(rss, limit=30)
            rss_fetch_ms = _ms_since(t_rss)
            log.debug("RSS fetch for '%s': %d video(s) in %dms", effective_channel_name, len(videos), rss_fetch_ms)
            if not videos:
                # Some playlists don't reliably expose items via RSS (even when unlisted).
                # Fallback to yt-dlp to enumerate playlist items (best-effort).
                log.debug("RSS empty — falling back to yt-dlp playlist enumeration for %s", ch.url)
                videos = _fetch_videos_via_ytdlp_playlist(
                    playlist_url=ch.url,
                    limit=30,
                    ytdlp_cookies_from_browser=settings.ytdlp_cookies_from_browser,
                    ytdlp_cookies_file=settings.ytdlp_cookies_file,
                )
                log.debug("yt-dlp fallback found %d video(s)", len(videos))

            # Bootstrap: on first encounter of a subscription, mark all current RSS videos as seen
            # without processing them. This prevents flooding on newly-added channels.
            # Queue playlists are NOT bootstrapped — they are always drained to empty.
            if ch.source_type == "subscription" and not has_bootstrapped(conn, ch.url):
                for v in videos:
                    seen_id = v.video_id if mode != "transcribe" else f"transcribe:{v.video_id}"
                    if not db.has_seen(conn, seen_id):
                        db.mark_seen(
                            conn,
                            db.SeenVideo(
                                video_id=seen_id,
                                video_url=v.url,
                                channel_name=effective_channel_name,
                                video_title=v.title,
                                published_at=v.published_at,
                            ),
                        )
                mark_bootstrapped(conn, ch.url)
                log.info("[bootstrap] %s: marked %d existing video(s) as seen — will only process new videos going forward",
                         effective_channel_name, len(videos))
                continue

            # Determine which prompts to run for this channel.
            # If ch.prompt is set, filter to that one key only; otherwise use all enabled.
            if ch.prompt:
                channel_prompts = [p for p in all_enabled_prompts if p.key == ch.prompt]
                if not channel_prompts:
                    channel_prompts = all_enabled_prompts
            else:
                channel_prompts = all_enabled_prompts

            log.debug("Prompts for '%s': %s", effective_channel_name, [p.key for p in channel_prompts])

            # Source label for the email (human-readable type tag).
            source_label = {
                "subscription": "Subscription",
                "summarize_queue": "Summarize Queue",
                "transcribe_queue": "Transcribe Queue",
            }.get(ch.source_type, ch.source_type)

            unseen = [v for v in videos if not db.has_seen(conn, v.video_id if mode != "transcribe" else f"transcribe:{v.video_id}")]
            log.debug("'%s': %d/%d video(s) unseen", effective_channel_name, len(unseen), len(videos))

            for v in videos:
                if remaining <= 0:
                    break
                # Allow the same video to be processed separately for summarize vs transcribe queues.
                seen_id = v.video_id if mode != "transcribe" else f"transcribe:{v.video_id}"
                if db.has_seen(conn, seen_id):
                    log.debug("  skip (already seen): %s", v.title)
                    continue

                log.info("Processing [%s] '%s' — %s", ch.source_type, v.title, v.video_id)
                t_total = time.perf_counter()
                summary_id = _new_summary_id(v.video_id)
                # Dry-run means: don't email + don't mark as seen.
                # We still fetch real transcripts/transcriptions so QA runs are meaningful.
                log.debug("  fetching transcript via %s ...", settings.transcribe_backend)
                transcript, transcript_stats = _get_transcript(
                    video_id=v.video_id,
                    video_url=v.url,
                    transcribe_backend=settings.transcribe_backend,
                    parakeet_model=settings.parakeet_model,
                    whisper_cpp_model=settings.whisper_cpp_model,
                    ytdlp_cookies_from_browser=settings.ytdlp_cookies_from_browser,
                    ytdlp_cookies_file=settings.ytdlp_cookies_file,
                    root=root,
                    prefer_youtube=False,
                )
                log.debug("  transcript: source=%s chars=%d download=%s transcribe=%s",
                          transcript.source, len(transcript.text or ""),
                          _fmt_ms(transcript_stats.audio_download_ms),
                          _fmt_ms(transcript_stats.transcribe_ms))

                # Build email sections
                t_sum_total = time.perf_counter()
                sections: list[dict[str, object]] = []
                per_prompt_s: list[str] = []
                enabled_prompt_keys: list[str] = []
                if mode == "transcribe":
                    enabled_prompt_keys = ["transcribe_clean"]
                    log.debug("  running transcribe cleanup...")
                    t_clean = time.perf_counter()
                    cleaned = _clean_transcript_for_reading(transcript.text, ollama_model=settings.ollama_model)
                    per_prompt_s.append(f"transcribe_clean={_fmt_ms(_ms_since(t_clean))}")
                    log.debug("  transcribe cleanup done in %s", _fmt_ms(_ms_since(t_clean)))
                    sections.append(
                        {
                            "key": "transcribe_clean",
                            "label": "Transcript (cleaned)",
                            "text": cleaned,
                            "html": _format_transcript_html(cleaned),
                        }
                    )
                else:
                    enabled_prompt_keys = [p.key for p in channel_prompts]
                    for p in channel_prompts:
                        log.debug("  running prompt '%s' via ollama=%s ...", p.key, settings.ollama_model or "off")
                        t_sum = time.perf_counter()
                        out = _summarize(transcript.text, settings.ollama_model, p.template)
                        if p.key == "default":
                            out = _ensure_key_takeaways(out, transcript.text, settings.ollama_model)
                        elapsed = _ms_since(t_sum)
                        per_prompt_s.append(f"{p.key}={_fmt_ms(elapsed)}")
                        log.debug("  prompt '%s' done in %s (%d chars out)", p.key, _fmt_ms(elapsed), len(out))
                        sections.append(
                            {
                                "key": p.key,
                                "label": p.label,
                                "text": out,
                                "html": _format_summary_html(out),
                            }
                        )
                summarize_ms = _ms_since(t_sum_total)

                # summarize_queue: just the video title (no tag, no playlist name)
                # subscription: [SUB] Channel — Title
                # transcribe_queue: [TRANSCRIPTION] Title
                if ch.source_type == "summarize_queue":
                    subject = f"{settings.subject_prefix}{v.title}"
                elif ch.source_type == "transcribe_queue":
                    subject = f"{settings.subject_prefix}[TRANSCRIPTION] {v.title}"
                else:
                    subject = f"{settings.subject_prefix}[SUB] {effective_channel_name} — {v.title}"
                beta_stats = BetaStats(
                    video_id=v.video_id,
                    summary_id=summary_id,
                    transcript_source=transcript.source,
                    ollama_model=settings.ollama_model,
                    enabled_prompts=enabled_prompt_keys,
                    rss_fetch_ms=rss_fetch_ms,
                    audio_download_ms=transcript_stats.audio_download_ms,
                    audio_bytes=transcript_stats.audio_bytes,
                    transcribe_ms=transcript_stats.transcribe_ms,
                    summarize_ms=summarize_ms,
                    email_render_ms=None,
                    email_send_ms=None,
                    total_ms=0,  # set below
                )
                beta_stats_view = {
                    "video_id": beta_stats.video_id,
                    "summary_id": beta_stats.summary_id,
                    "transcript_source": beta_stats.transcript_source,
                    "ollama_model": beta_stats.ollama_model,
                    "enabled_prompts": ", ".join(beta_stats.enabled_prompts),
                    "prompt_count": len(beta_stats.enabled_prompts),
                    "per_prompt_summarize_s": ", ".join(per_prompt_s),
                    "transcript_chars": len(transcript.text or ""),
                    "summary_chars": sum(len(str(s.get("text", "")) or "") for s in sections),
                    "mode": mode,
                    "rss_fetch_s": _fmt_seconds(beta_stats.rss_fetch_ms),
                    "media_size_mb": _fmt_mb(beta_stats.audio_bytes),
                    "download_media_s": _fmt_seconds(beta_stats.audio_download_ms),
                    "transcribe_s": _fmt_seconds(beta_stats.transcribe_ms),
                    "summarize_s": _fmt_seconds(beta_stats.summarize_ms),
                    "email_render_s": None,
                    "email_send_s": None,
                    # End-to-end is computed as (total_before_send_s + email_send_s).
                    # We include both so you can see the breakdown.
                    "total_before_send_s": None,
                    "total_to_send_s": None,
                    "qa_notes": "multi-prompt email enabled (beta)",
                }
                published_at_display = _fmt_published_at(v.published_at)
                render_ctx = dict(
                    subject=subject,
                    source_label=source_label,
                    source_name=effective_channel_name,
                    video_title=v.title,
                    video_url=v.url,
                    sections=sections,
                    transcript_source=transcript.source,
                    published_at=v.published_at,
                    published_at_display=published_at_display,
                    beta_stats=beta_stats_view,
                )
                # Render twice so the email itself can include accurate `email_render_s`.
                t_render = time.perf_counter()
                html = template.render(**render_ctx)
                email_render_ms = _ms_since(t_render)

                beta_stats = BetaStats(
                    **{**beta_stats.__dict__, "email_render_ms": email_render_ms, "total_ms": _ms_since(t_total)}
                )
                beta_stats_view["email_render_s"] = _fmt_seconds(beta_stats.email_render_ms)
                beta_stats_view["total_before_send_s"] = _fmt_seconds(beta_stats.total_ms)
                render_ctx["beta_stats"] = beta_stats_view
                # Re-render with updated stats (small overhead, but removes "n/a" during beta).
                html = template.render(**render_ctx)
                # Persist the summary + stats after we know render/total timings.
                _write_summary_artifact(
                    root=root,
                    summary_id=summary_id,
                    channel_name=effective_channel_name,
                    video_title=v.title,
                    video_url=v.url,
                    video_id=v.video_id,
                    published_at=v.published_at,
                    transcript_source=transcript.source,
                    enabled_prompts=[p.key for p in channel_prompts],
                    ollama_model=settings.ollama_model,
                    sections=sections,
                    beta_stats=beta_stats,
                )
                text = (
                    f"{effective_channel_name}\n{v.title}\n{v.url}\n\n"
                    f"{_format_sections_text(sections)}\n\n"
                    f"Transcript source: {transcript.source}\n\n"
                    f"{_format_beta_stats_text(beta_stats)}\n"
                )

                if not settings.dry_run:
                    log.info("  sending email: %s", subject)
                    t_send = time.perf_counter()
                    send_gmail_smtp(
                        email_from=settings.email_from,
                        email_to=settings.email_to,
                        gmail_app_password=settings.gmail_app_password,
                        content=EmailContent(subject=subject, text=text, html=html),
                    )
                    beta_stats = BetaStats(**{**beta_stats.__dict__, "email_send_ms": _ms_since(t_send)})
                    log.info("  email sent in %s", _fmt_ms(beta_stats.email_send_ms))
                    beta_stats_view["email_send_s"] = _fmt_seconds(beta_stats.email_send_ms)
                    total_to_send_s = None
                    if beta_stats_view["total_before_send_s"] is not None and beta_stats_view["email_send_s"] is not None:
                        total_to_send_s = round(beta_stats_view["total_before_send_s"] + beta_stats_view["email_send_s"], 2)
                    beta_stats_view["total_to_send_s"] = total_to_send_s
                    beta_stats_view["total_processing_s"] = total_to_send_s
                    # Persist final stats (including send timing) to the stored summary file.
                    _append_summary_stats(root=root, summary_id=summary_id, beta_stats_view=beta_stats_view)
                else:
                    # Even in dry-run, append the final timings we do have for QA.
                    log.info("  dry-run: email suppressed for '%s'", v.title)
                    beta_stats_view["qa_notes"] = "dry-run (no email sent)"
                    beta_stats_view["total_processing_s"] = beta_stats_view.get("total_before_send_s")
                    _append_summary_stats(root=root, summary_id=summary_id, beta_stats_view=beta_stats_view)

                if not settings.dry_run:
                    log.debug("  marking seen: %s", seen_id)
                    db.mark_seen(
                        conn,
                        db.SeenVideo(
                            video_id=seen_id,
                            video_url=v.url,
                            channel_name=effective_channel_name,
                            video_title=v.title,
                            published_at=v.published_at,
                        ),
                    )
                remaining -= 1
                processed += 1
                log.info("  done: total=%s remaining_slots=%d", _fmt_ms(_ms_since(t_total)), remaining)

    log.info("run_once complete: processed %d video(s)", processed)
    return processed


def run_forever(*, poll_seconds: int = 900, limit: int = 10) -> None:
    """
    Poll continuously:
    - Process anything new from configured sources (channels + playlists)
    - If nothing new is found, sleep until the next poll
    """
    _load_dotenv_if_present(repo_root() / ".env")
    setup_logging()
    log.info("Starting watch loop (poll_seconds=%d, limit=%d)", poll_seconds, limit)
    while True:
        n = run_once(limit=limit)
        if n <= 0:
            log.debug("No new videos found — sleeping %ds", poll_seconds)
            time.sleep(max(5, int(poll_seconds)))
        else:
            # If we processed something, loop again immediately to catch up quickly.
            continue


def _summarize(transcript: str, ollama_model: str | None, prompt_template: str) -> str:
    if ollama_model:
        try:
            out = summarize_with_ollama(transcript=transcript, model=ollama_model, prompt_template=prompt_template)
            if out:
                return out
        except Exception as e:
            # If Ollama is temporarily unavailable, we still send *something*.
            log.warning("Ollama summarization failed (%s) — using fallback", e)
            pass
    return summarize_fallback(transcript)

@dataclass(frozen=True)
class _TranscriptStats:
    transcript_source: str
    audio_download_ms: int | None
    audio_bytes: int | None
    transcribe_ms: int | None


def _get_transcript(
    video_id: str,
    video_url: str,
    transcribe_backend: str,
    parakeet_model: str,
    whisper_cpp_model: str | None,
    ytdlp_cookies_from_browser: str | None,
    ytdlp_cookies_file: str | None,
    root: Path,
    *,
    prefer_youtube: bool = True,
) -> tuple[TranscriptResult, _TranscriptStats]:
    if prefer_youtube:
        yt = fetch_youtube_transcript(video_id)
        if yt:
            return (
                TranscriptResult(text=yt, source="youtube"),
                _TranscriptStats(transcript_source="youtube", audio_download_ms=None, audio_bytes=None, transcribe_ms=None),
            )

    backend = (transcribe_backend or "").strip()
    if backend not in ("parakeet_mlx", "whisper_cpp"):
        raise RuntimeError("Invalid YTS_TRANSCRIBE_BACKEND. Use parakeet_mlx or whisper_cpp.")

    audio_dir = root / "data" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_base = audio_dir / f"{video_id}"

    # Download audio
    cookies_args: list[str] = []
    if ytdlp_cookies_file:
        cookies_args = ["--cookies", ytdlp_cookies_file]
    elif ytdlp_cookies_from_browser:
        cookies_args = ["--cookies-from-browser", ytdlp_cookies_from_browser]

    t_dl = time.perf_counter()
    _run(
        [
            "yt-dlp",
            # We only need audio (not video). Prefer a smaller audio stream to reduce
            # download time + disk usage during beta testing.
            #
            # - `bestaudio[abr<=96]` tries to pick an audio-only format at ~96kbps or lower.
            # - Falls back to `bestaudio` if that constraint isn't available.
            "-f",
            "bestaudio[abr<=96]/bestaudio",
            "--extract-audio",
            "--audio-format",
            "m4a",
            # When re-encoding is needed, don't aim for "best"; smaller is fine for ASR.
            "--audio-quality",
            "5",
            *cookies_args,
            "-o",
            str(out_base) + ".%(ext)s",
            video_url,
        ]
    )
    audio_download_ms = _ms_since(t_dl)

    audio_path = str(out_base) + ".m4a"
    if not Path(audio_path).exists():
        raise RuntimeError("Audio download failed (expected .m4a output).")
    audio_bytes = Path(audio_path).stat().st_size

    transcript_text = ""
    source = "macwhisper"
    transcribe_ms: int | None = None

    if backend == "parakeet_mlx":
        # `parakeet-mlx` writes outputs to files; we read the .txt output.
        out_dir = audio_dir / "parakeet"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path_no_ext = out_dir / f"{video_id}"
        t_tx = time.perf_counter()
        _run(
            [
                "parakeet-mlx",
                audio_path,
                "--model",
                parakeet_model,
                "--output-dir",
                str(out_dir),
                "--output-format",
                "txt",
                "--output-template",
                str(out_path_no_ext.name),
            ]
        )
        transcribe_ms = _ms_since(t_tx)
        txt_path = out_dir / f"{out_path_no_ext.name}.txt"
        transcript_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        source = "parakeet"

    if backend == "whisper_cpp":
        if not whisper_cpp_model:
            raise RuntimeError(
                "No YouTube transcript found, and whisper.cpp fallback is selected but missing a model path. "
                "Set YTS_WHISPER_CPP_MODEL in .env to a ggml model file (e.g., ggml-base.en.bin)."
            )
        t_tx = time.perf_counter()
        transcript_text = _run_capture(
            [
                "whisper-cli",
                "-m",
                whisper_cpp_model,
                "-nt",
                "-np",
                audio_path,
            ]
        ).strip()
        transcribe_ms = _ms_since(t_tx)
        source = "whisper_cpp"

    if not transcript_text:
        raise RuntimeError("Transcription fallback returned empty transcript.")
    return (
        TranscriptResult(text=transcript_text, source=source),
        _TranscriptStats(
            transcript_source=source,
            audio_download_ms=audio_download_ms,
            audio_bytes=audio_bytes,
            transcribe_ms=transcribe_ms,
        ),
    )


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, env=_child_env())
    except subprocess.CalledProcessError as e:
        if cmd and cmd[0] == "yt-dlp":
            msg = (getattr(e, "stderr", None) or "") if hasattr(e, "stderr") else ""
            # If ffprobe/ffmpeg is missing, yt-dlp extraction can fail even when cookies are fine.
            if "ffprobe" in msg.lower() or "ffmpeg" in msg.lower():
                raise RuntimeError(
                    "Audio processing failed because ffmpeg/ffprobe was not found. "
                    "Fix: install ffmpeg (brew install ffmpeg) and ensure Homebrew is on PATH."
                ) from e
            raise RuntimeError(
                "Audio download failed. YouTube may be blocking automated downloads on this network. "
                "Fix: set YTS_YTDLP_COOKIES_FROM_BROWSER (e.g. 'chrome' or 'safari') "
                "or YTS_YTDLP_COOKIES_FILE to a cookies.txt export, then retry."
            ) from e
        raise


def _run_capture(cmd: list[str]) -> str:
    res = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_child_env(),
    )
    return res.stdout or ""


def _child_env() -> dict[str, str]:
    """
    Ensure subprocesses can find tools installed in the active venv (e.g. `parakeet-mlx`).
    """
    env = dict(os.environ)
    # Don't `.resolve()` here: venv python is often a symlink to the base interpreter,
    # and resolving would point us at the Homebrew python bin instead of `.venv/bin`.
    venv_bin = str(Path(sys.executable).parent)
    base_path = env.get("PATH", "")
    # launchd often provides a minimal PATH; add common Homebrew locations so tools like
    # `yt-dlp`, `ffmpeg`, and `ffprobe` are discoverable.
    brew_prefixes = ["/opt/homebrew/bin", "/opt/homebrew/sbin"]
    for p in reversed(brew_prefixes):
        if p and p not in base_path:
            base_path = f"{p}{os.pathsep}{base_path}" if base_path else p
    env["PATH"] = f"{venv_bin}{os.pathsep}{base_path}"
    return env


def _fmt_published_at(published_at: str) -> str:
    """Parse and format a video's published date for display in emails."""
    if not published_at:
        return ""
    # Try RFC 2822 (feedparser default: "Thu, 13 Mar 2025 14:30:00 +0000")
    try:
        dt = parsedate_to_datetime(published_at).astimezone(timezone.utc)
        return dt.strftime("%B %-d, %Y at %-I:%M %p UTC")
    except Exception:
        pass
    # Try ISO 8601
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%B %-d, %Y at %-I:%M %p UTC")
    except Exception:
        pass
    return published_at


def _ms_since(t0: float) -> int:
    return int(round((time.perf_counter() - t0) * 1000))


def _fmt_ms(ms: int | None) -> str:
    if ms is None:
        return "n/a"
    return f"{ms / 1000:.2f} s"


def _fmt_seconds(ms: int | None) -> float | None:
    if ms is None:
        return None
    return round(ms / 1000.0, 2)


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "n/a"
    return f"{(n / (1024.0 * 1024.0)):.2f} MB"


def _fmt_mb(n: int | None) -> float | None:
    if n is None:
        return None
    return round(n / (1024.0 * 1024.0), 2)


def _format_beta_stats_text(s: BetaStats) -> str:
    lines = [
        "---",
        "Beta stats",
        f"- summary_id: {s.summary_id}",
        f"- video_id: {s.video_id}",
        f"- transcript_source: {s.transcript_source}",
        f"- enabled_prompts: {', '.join(s.enabled_prompts)}",
        f"- ollama_model: {s.ollama_model or 'n/a'}",
        f"- rss_fetch_s: {_fmt_ms(s.rss_fetch_ms)}",
        f"- media_size_mb: {_fmt_bytes(s.audio_bytes)}",
        f"- download_media_s: {_fmt_ms(s.audio_download_ms)}",
        f"- transcribe_s: {_fmt_ms(s.transcribe_ms)}",
        f"- summarize_s: {_fmt_ms(s.summarize_ms)}",
        f"- email_render_s: {_fmt_ms(s.email_render_ms)}",
        f"- email_send_s: {_fmt_ms(s.email_send_ms)}",
        f"- total_before_send_s: {_fmt_ms(s.total_ms)}",
        "- total_to_send_s: total_before_send_s + email_send_s",
        "---",
    ]
    return "\n".join(lines)


def _format_sections_text(sections: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for i, s in enumerate(sections):
        label = str(s.get("label", "") or "").strip() or str(s.get("key", "") or "").strip() or "Summary"
        text = str(s.get("text", "") or "").strip()
        if i > 0:
            parts.append("\n---\n")
        parts.append(f"{label}\n{text}".strip())
    return "\n\n".join([p for p in parts if p.strip()]).strip()


def _new_summary_id(video_id: str) -> str:
    # Short, readable, and unique enough for beta (also safe to paste in chats).
    return f"{video_id}_{uuid4().hex[:8]}"


def _summaries_dir(root: Path) -> Path:
    p = root / "data" / "summaries"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_summary_artifact(
    *,
    root: Path,
    summary_id: str,
    channel_name: str,
    video_title: str,
    video_url: str,
    video_id: str,
    published_at: str,
    transcript_source: str,
    enabled_prompts: list[str],
    ollama_model: str | None,
    sections: list[dict[str, object]],
    beta_stats: BetaStats,
) -> None:
    """
    Store the exact summary text locally so we can reference it during beta.
    """
    path = _summaries_dir(root) / f"{summary_id}.txt"
    beta_lines = _format_beta_stats_text(beta_stats)
    body = "\n".join(
        [
            f"summary_id: {summary_id}",
            f"video_id: {video_id}",
            f"channel: {channel_name}",
            f"title: {video_title}",
            f"url: {video_url}",
            f"published_at: {published_at}",
            f"transcript_source: {transcript_source}",
            f"enabled_prompts: {', '.join(enabled_prompts)}",
            f"ollama_model: {ollama_model or 'n/a'}",
            "",
            "SUMMARY",
            _format_sections_text(sections),
            "",
            beta_lines.strip(),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")


def _append_summary_stats(*, root: Path, summary_id: str, beta_stats_view: dict) -> None:
    """
    After we have send timing, append a compact block (best-effort).
    """
    path = _summaries_dir(root) / f"{summary_id}.txt"
    if not path.exists():
        return
    try:
        lines = [
            "",
            "FINAL_STATS",
            f"email_render_s: {beta_stats_view.get('email_render_s', 'n/a')}",
            f"email_send_s: {beta_stats_view.get('email_send_s', 'n/a')}",
            f"total_before_send_s: {beta_stats_view.get('total_before_send_s', 'n/a')}",
            f"total_to_send_s: {beta_stats_view.get('total_to_send_s', 'n/a')}",
            "",
        ]
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        return


def _best_effort_update_channel_name_in_config(*, config_path: Path, url: str, name: str) -> None:
    """
    If a channel entry is missing `name`, write it back into `config/channels.toml`.
    This is best-effort and intentionally simple (string-based) to avoid adding deps.
    """
    try:
        raw = config_path.read_text(encoding="utf-8")
    except Exception:
        return

    # Only patch entries that already contain the URL and do NOT already have a name.
    # Example accepted shapes:
    # - { url = "...", prompt = "default" }
    # - { url = "..." }
    u = url.replace("\\", "\\\\").replace('"', '\\"')
    n = name.replace("\\", "\\\\").replace('"', '\\"')

    def repl(match: re.Match) -> str:
        block = match.group(0)
        if "name" in block:
            return block
        # Insert `name = "..."` right after `{`
        return block.replace("{", '{ name = "' + n + '", ', 1)

    # Find object literals that contain this url.
    pattern = re.compile(r"\{[^}]*\burl\s*=\s*\"" + re.escape(u) + r"\"[^}]*\}")
    updated, n_subs = pattern.subn(repl, raw, count=1)
    if n_subs <= 0 or updated == raw:
        return
    try:
        config_path.write_text(updated, encoding="utf-8")
    except Exception:
        return
    try:
        lines = [
            "",
            "FINAL_STATS",
            f"email_render_s: {beta_stats_view.get('email_render_s', 'n/a')}",
            f"email_send_s: {beta_stats_view.get('email_send_s', 'n/a')}",
            f"total_before_send_s: {beta_stats_view.get('total_before_send_s', 'n/a')}",
            f"total_to_send_s: {beta_stats_view.get('total_to_send_s', 'n/a')}",
            "",
        ]
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        return


def _cleanup_downloads(root: Path) -> None:
    """
    Keep the data folder from growing forever.

    Deletes old files in:
    - data/audio/
    - data/audio/parakeet/

    Config:
    - YTS_AUDIO_RETENTION_DAYS (default: 7)
    """
    keep_days_raw = os.environ.get("YTS_AUDIO_RETENTION_DAYS", "").strip()
    try:
        keep_days = int(keep_days_raw) if keep_days_raw else 7
    except Exception:
        keep_days = 7

    if keep_days < 0:
        return

    cutoff = time.time() - (keep_days * 24 * 60 * 60)
    dirs = [
        root / "data" / "audio",
        root / "data" / "audio" / "parakeet",
    ]
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        for p in d.iterdir():
            if not p.is_file():
                continue
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
            except Exception:
                # Best-effort cleanup; never break the main run.
                continue


def _format_summary_html(summary: str) -> Markup:
    """
    Convert a lightweight markdown-ish summary into nice HTML.

    Supported:
    - Blank-line separated paragraphs
    - Bullets starting with "- " or "* "
    - "Key Takeaways" line becomes a small section header
    """
    s = (summary or "").strip()
    if not s:
        return Markup("")

    lines = [ln.rstrip() for ln in s.splitlines()]
    html_parts: list[str] = []

    def close_list() -> None:
        if html_parts and html_parts[-1] == "<ul>":
            # empty list guard
            html_parts.pop()
            return
        if any(p == "<ul>" for p in html_parts) and (not html_parts or html_parts[-1] != "</ul>"):
            html_parts.append("</ul>")

    in_list = False
    para_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal para_buf
        text = " ".join(x.strip() for x in para_buf if x.strip()).strip()
        para_buf = []
        if text:
            html_parts.append(f"<p style=\"margin:0 0 10px 0;\">{escape(text)}</p>")

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        low = line.lower().strip(":")
        if low in ("key takeaways", "key takeaways:"):
            flush_paragraph()
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(
                "<div style=\"margin:12px 0 6px 0; font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:#6b6f85;\">Key takeaways</div>"
            )
            continue

        is_bullet = line.startswith("- ") or line.startswith("* ")
        if is_bullet:
            flush_paragraph()
            if not in_list:
                html_parts.append("<ul style=\"margin:0 0 10px 18px; padding:0;\">")
                in_list = True
            html_parts.append(f"<li style=\"margin:0 0 6px 0;\">{escape(line[2:].strip())}</li>")
            continue

        if in_list:
            html_parts.append("</ul>")
            in_list = False

        para_buf.append(line)

    flush_paragraph()
    if in_list:
        html_parts.append("</ul>")

    # Ensure Jinja doesn't escape our generated HTML
    return Markup("\n".join(html_parts))


def _format_transcript_html(transcript: str) -> Markup:
    # For cleaned transcript emails: keep it readable and preserve line breaks.
    s = (transcript or "").strip()
    if not s:
        return Markup("")
    return Markup(f"<div style=\"white-space:pre-wrap;\">{escape(s)}</div>")


def _clean_transcript_for_reading(transcript: str, *, ollama_model: str | None) -> str:
    """
    Produces an "email-friendly" transcript:
    - improves punctuation/paragraph breaks
    - does NOT summarize
    """
    t = (transcript or "").strip()
    if not t:
        return t

    # Default: deterministic cleanup for accuracy (no LLM rewriting).
    # Optional: allow Ollama-based cleanup if explicitly enabled.
    use_ollama = os.environ.get("YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA", "").strip().lower() in ("1", "true", "yes", "on")
    if use_ollama and ollama_model:
        transcribe_prompts = [p for p in load_transcribe_prompts() if p.enabled]
        prompt_template = (transcribe_prompts[0].template if transcribe_prompts else "").strip()
        prompt = (prompt_template.format(transcript=t) if prompt_template else f"\"\"\"\n{t}\n\"\"\"")
        try:
            res = subprocess.run(
                ["ollama", "run", ollama_model],
                input=prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=300,
            )
            out = (res.stdout or "").strip()
            return out or t
        except Exception:
            return t

    # Simple, accurate reflow:
    # - remove blank-line noise
    # - collapse runs of whitespace
    # - add paragraph breaks on sentence boundaries (without changing wording)
    opts = load_transcribe_options()
    raw = " ".join([ln.strip() for ln in t.splitlines() if ln.strip()]).strip()

    if opts.get("strip_stage_directions", False):
        raw = re.sub(
            r"\[(?:music|applause|laughter|silence|noise|intro|outro|advertisement)[^\]]*\]",
            "",
            raw,
            flags=re.I,
        )
        raw = re.sub(r"\s{2,}", " ", raw).strip()

    if opts.get("remove_fillers", True):
        # Remove standalone filler tokens.
        raw = re.sub(r"(?i)\b(um+|uh+|er+|ah+|eh+|hmm+)\b", "", raw)
        # Remove obvious double-word stutters: "the the" -> "the"
        raw = re.sub(r"(?i)\b(\w+)(\s+\1\b)+", r"\1", raw)
        raw = re.sub(r"\s{2,}", " ", raw).strip()

    if len(raw) <= 1200:
        return raw

    target = 1000 if opts.get("robust_sentence_breaks", False) else 1400
    paras: list[str] = []
    buf = ""
    for part in re.split(r"(?<=[.!?])\s+", raw):
        if not part:
            continue
        if buf and len(buf) + 1 + len(part) > target:
            paras.append(buf.strip())
            buf = part
        else:
            buf = (buf + " " + part).strip()
    if buf.strip():
        paras.append(buf.strip())
    out = "\n\n".join(paras).strip()

    if opts.get("questions_own_paragraph", False):
        # Put questions on their own paragraph (blank line before & after).
        out = re.sub(r"(?m)(^.*\?\s*$)", r"\n\1\n", out)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()

    return out


def _ensure_key_takeaways(summary: str, transcript: str, ollama_model: str | None) -> str:
    """
    Default summary must contain exactly 3 "- " bullets under a "Key takeaways" line.
    If the model forgets, we repair it.
    """
    s = (summary or "").strip()
    if not s:
        return s

    if _has_three_key_takeaway_bullets(s):
        return _truncate_key_takeaways_to_three(s)

    if not ollama_model:
        repaired = _truncate_key_takeaways_to_three(s)
        if _has_three_key_takeaway_bullets(repaired):
            return repaired
        core = "\n".join([ln for ln in s.splitlines() if ln.strip()][:12]).strip()
        return (core + "\n\nKey takeaways\n- Main idea\n- Why it matters\n- What to do next\n").strip()

    prompt = f”””Rewrite the summary below so it follows this format exactly. Output ONLY the rewritten summary — no intro, no preamble, no explanation.

REQUIRED FORMAT:
<paragraph 1>

<paragraph 2>

Key takeaways
- <point 1>
- <point 2>
- <point 3>

Rules:
- Plain prose paragraphs only (no bullets, no bold, no headers in the paragraphs)
- The line “Key takeaways” must appear exactly as written, alone on its line
- Exactly 3 bullets after “Key takeaways”, each starting with “- “
- Nothing after the 3rd bullet
- Do NOT start with “Here is”, “Here's”, or any preamble

Current (malformed) summary:
\”\”\”
{s}
\”\”\”
“””
    try:
        res = subprocess.run(
            ["ollama", "run", ollama_model],
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=120,
        )
        fixed = (res.stdout or "").strip() or s
        fixed = _truncate_key_takeaways_to_three(fixed)
        return fixed
    except Exception:
        return _truncate_key_takeaways_to_three(s)


def _has_three_key_takeaway_bullets(text: str) -> bool:
    m = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", text)
    if not m:
        return False
    after = text[m.end() :].strip("\n")
    bullets = []
    for ln in after.splitlines():
        line = ln.strip()
        if not line:
            continue
        if line.startswith("- "):
            bullets.append(line)
            continue
        if bullets:
            break
    return len(bullets) >= 3


def _truncate_key_takeaways_to_three(text: str) -> str:
    m = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", text)
    if not m:
        return text.strip()
    before = text[: m.start()].rstrip()
    after = text[m.end() :].lstrip()
    bullets = []
    for ln in after.splitlines():
        line = ln.strip()
        if line.startswith("- "):
            bullets.append(line)
            continue
        if bullets:
            break
    bullets = bullets[:3]
    return "\n\n".join([before, "Key takeaways", "\n".join(bullets)]).strip()


def _fetch_videos_via_ytdlp_playlist(
    *,
    playlist_url: str,
    limit: int,
    ytdlp_cookies_from_browser: str | None,
    ytdlp_cookies_file: str | None,
) -> list[object]:
    """
    Best-effort playlist enumeration using yt-dlp (used when RSS is empty).

    Returns objects shaped like `youtube_summarizer.youtube.Video` without importing it here:
    { video_id, url, title, published_at }.
    """
    cookies_args: list[str] = []
    if ytdlp_cookies_file:
        cookies_args = ["--cookies", ytdlp_cookies_file]
    elif ytdlp_cookies_from_browser:
        cookies_args = ["--cookies-from-browser", ytdlp_cookies_from_browser]

    try:
        res = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--dump-single-json",
                *cookies_args,
                playlist_url,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_child_env(),
            timeout=60,
        )
    except Exception:
        return []

    try:
        data = json.loads(res.stdout or "{}")
    except Exception:
        return []

    entries = data.get("entries") or []
    out = []
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    for e in entries:
        if len(out) >= max(0, limit):
            break
        vid = str((e or {}).get("id") or "").strip()
        title = str((e or {}).get("title") or "").strip() or "Untitled"
        if not vid:
            continue
        out.append(
            type(
                "Video",
                (),
                {
                    "video_id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "title": title,
                    "published_at": now_iso,
                },
            )()
        )
    return out


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

