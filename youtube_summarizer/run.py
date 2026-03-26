from __future__ import annotations

import logging
import os
import json
import re
import resource
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
    level_name = os.environ.get("YTS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    log.debug("Logging initialised at level %s", level_name)


from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

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
    source: str


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
    audio_duration_s: float | None
    transcribe_ms: int | None
    summarize_ms: int | None
    email_render_ms: int | None
    email_send_ms: int | None
    avg_cpu_pct: float | None
    total_ms: int


# ---------------------------------------------------------------------------
# Hashtag stripping
# ---------------------------------------------------------------------------

_HASHTAG_RE = re.compile(r"\s*#\w+")


def _strip_hashtags(title: str) -> str:
    return _HASHTAG_RE.sub("", title).strip()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def _check_ollama(model: str | None) -> None:
    """Abort early if Ollama is configured but unreachable."""
    if not model:
        return
    try:
        res = subprocess.run(
            ["ollama", "list"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=10, env=_child_env(),
        )
        if res.returncode != 0:
            raise RuntimeError(f"ollama list failed: {res.stderr.strip()}")
    except FileNotFoundError:
        raise RuntimeError("ollama binary not found — check PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ollama list timed out — is ollama server running?")

def run_once(limit: int = 10) -> int:
    _load_dotenv_if_present(repo_root() / ".env")
    setup_logging()

    settings = load_settings()
    channels = load_channels()
    process_prompts = load_process_prompts()
    if not channels:
        raise RuntimeError("No channels configured. Add entries to config/channels.toml.")

    _check_ollama(settings.ollama_model)
    log.info("run_once: %d source(s) configured, limit=%d, dry_run=%s, ollama=%s",
             len(channels), limit, settings.dry_run, settings.ollama_model or "off")

    root = repo_root()
    _cleanup_downloads(root)
    env = Environment(
        loader=FileSystemLoader(str(root / "youtube_summarizer" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("email.html.j2")

    # Build prompt map by key for quick lookup
    prompt_map = {p.key: p for p in process_prompts}

    processed = 0
    with db.connect(root) as conn:
        remaining = max(1, limit)

        for ch in channels:
            if remaining <= 0:
                break

            log.debug("Checking source: [%s] %s", ch.source_type, ch.name or ch.url)

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

            t_rss = time.perf_counter()
            videos = fetch_latest_videos_from_rss(rss, limit=30)
            rss_fetch_ms = _ms_since(t_rss)
            log.debug("RSS fetch for '%s': %d video(s) in %dms", effective_channel_name, len(videos), rss_fetch_ms)

            if not videos:
                log.debug("RSS empty — falling back to yt-dlp playlist enumeration for %s", ch.url)
                videos = _fetch_videos_via_ytdlp_playlist(
                    playlist_url=ch.url,
                    limit=30,
                    ytdlp_cookies_from_browser=settings.ytdlp_cookies_from_browser,
                    ytdlp_cookies_file=settings.ytdlp_cookies_file,
                )
                log.debug("yt-dlp fallback found %d video(s)", len(videos))

            # Bootstrap: on first encounter of a subscription, mark all current RSS videos as seen.
            if ch.source_type == "subscription" and not has_bootstrapped(conn, ch.url):
                for v in videos:
                    if not db.has_seen(conn, v.video_id):
                        db.mark_seen(conn, db.SeenVideo(
                            video_id=v.video_id,
                            video_url=v.url,
                            channel_name=effective_channel_name,
                            video_title=_strip_hashtags(v.title),
                            published_at=v.published_at,
                        ))
                mark_bootstrapped(conn, ch.url)
                log.info("[bootstrap] %s: marked %d existing video(s) as seen",
                         effective_channel_name, len(videos))
                continue

            source_label = {
                "subscription": "Subscription",
                "summarize_queue": "Summarize Queue",
                "transcribe_queue": "Transcribe Queue",
            }.get(ch.source_type, ch.source_type)

            for v in videos:
                if remaining <= 0:
                    break
                if db.has_seen(conn, v.video_id):
                    log.debug("  skip (already seen): %s", v.title)
                    continue

                # Per-video channel name: use RSS entry author for queue sources
                if ch.source_type in ("summarize_queue", "transcribe_queue") and v.channel_name:
                    video_channel_name = v.channel_name
                else:
                    video_channel_name = effective_channel_name

                clean_title = _strip_hashtags(v.title)
                log.info("Processing [%s] '%s' — %s", ch.source_type, clean_title, v.video_id)

                # Mark seen immediately so no subsequent run (or a run triggered by a
                # state wipe) can pick this video up again, regardless of whether
                # transcription or email succeeds.
                if not settings.dry_run:
                    db.mark_seen(conn, db.SeenVideo(
                        video_id=v.video_id,
                        video_url=v.url,
                        channel_name=video_channel_name,
                        video_title=clean_title,
                        published_at=v.published_at,
                    ))

                t_total = time.perf_counter()
                ru_start = resource.getrusage(resource.RUSAGE_SELF)
                summary_id = _new_summary_id(v.video_id)

                # Fetch video metadata (description, chapters, duration) — fast, no audio download
                _meta_cookies: list[str] = []
                if settings.ytdlp_cookies_file:
                    _meta_cookies = ["--cookies", settings.ytdlp_cookies_file]
                elif settings.ytdlp_cookies_from_browser:
                    _meta_cookies = ["--cookies-from-browser", settings.ytdlp_cookies_from_browser]
                log.debug("  fetching video metadata ...")
                meta = _fetch_video_metadata(v.url, _meta_cookies)
                meta_description = (meta.get("description") or "").strip() or None
                meta_chapters = meta.get("chapters") or None
                meta_duration_s: float | None = meta.get("duration") or None
                video_context = _build_video_context(clean_title, meta_description, meta_chapters)
                log.debug("  metadata: description=%s chapters=%s duration=%s",
                          bool(meta_description), len(meta_chapters) if meta_chapters else 0, meta_duration_s)

                log.debug("  fetching transcript via %s ...", settings.transcribe_backend)
                try:
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
                except RuntimeError as e:
                    log.warning("  skipping '%s' — transcript unavailable: %s", clean_title, e)
                    remaining -= 1
                    continue

                log.debug("  transcript: source=%s chars=%d", transcript.source, len(transcript.text or ""))

                tier = _summary_tier(len(transcript.text))
                log.debug("Summary tier: %s (%d chars)", tier["tier"], len(transcript.text))

                # Apply per-feed prompt filter if specified in channels.toml.
                # "default" is a legacy alias meaning the core pipeline (opener + summary).
                effective_prompt_map = prompt_map
                if ch.prompts:
                    expanded: set[str] = set()
                    for key in ch.prompts:
                        if key == "default":
                            expanded.update(["opener", "summary"])
                        else:
                            expanded.add(key)
                    effective_prompt_map = {k: v for k, v in prompt_map.items() if k in expanded}
                    log.debug("  per-feed prompts filter: %s → %s", list(prompt_map.keys()), list(effective_prompt_map.keys()))

                # Build all email sections
                t_sum_total = time.perf_counter()
                sections, per_prompt_s, enabled_prompt_keys = _build_email_sections(
                    transcript=transcript.text,
                    ollama_model=settings.ollama_model,
                    tier=tier,
                    root=root,
                    prompt_map=effective_prompt_map,
                    video_context=video_context,
                    chapters=meta_chapters,
                    video_url=v.url,
                    video_duration_s=meta_duration_s or transcript_stats.audio_duration_s,
                )
                summarize_ms = _ms_since(t_sum_total)

                subject = f"[S] {clean_title}"

                ru_end = resource.getrusage(resource.RUSAGE_SELF)
                wall_s = time.perf_counter() - t_total
                cpu_s = (ru_end.ru_utime - ru_start.ru_utime) + (ru_end.ru_stime - ru_start.ru_stime)
                avg_cpu_pct = round(cpu_s / wall_s * 100, 1) if wall_s > 0 else None

                beta_stats = BetaStats(
                    video_id=v.video_id,
                    summary_id=summary_id,
                    transcript_source=transcript.source,
                    ollama_model=settings.ollama_model,
                    enabled_prompts=enabled_prompt_keys,
                    rss_fetch_ms=rss_fetch_ms,
                    audio_download_ms=transcript_stats.audio_download_ms,
                    audio_bytes=transcript_stats.audio_bytes,
                    audio_duration_s=transcript_stats.audio_duration_s,
                    transcribe_ms=transcript_stats.transcribe_ms,
                    summarize_ms=summarize_ms,
                    email_render_ms=None,
                    email_send_ms=None,
                    avg_cpu_pct=avg_cpu_pct,
                    total_ms=0,
                )
                beta_stats_view = {
                    "video_id": beta_stats.video_id,
                    "summary_id": beta_stats.summary_id,
                    "transcript_source": beta_stats.transcript_source,
                    "ollama_model": beta_stats.ollama_model,
                    "enabled_prompts": ", ".join(beta_stats.enabled_prompts),
                    "prompt_tier": tier["tier"],
                    "prompt_count": len(beta_stats.enabled_prompts),
                    "per_prompt_summarize_s": ", ".join(per_prompt_s),
                    "transcript_chars": len(transcript.text or ""),
                    "summary_chars": sum(len(str(s.get("text", "")) or "") for s in sections),
                    "mode": "summarize",
                    "rss_fetch_s": _fmt_seconds(beta_stats.rss_fetch_ms),
                    "media_size_mb": _fmt_mb(beta_stats.audio_bytes),
                    "download_media_s": _fmt_seconds(beta_stats.audio_download_ms),
                    "video_duration_s": beta_stats.audio_duration_s,
                    "transcribe_s": _fmt_seconds(beta_stats.transcribe_ms),
                    "summarize_s": _fmt_seconds(beta_stats.summarize_ms),
                    "avg_cpu_pct": beta_stats.avg_cpu_pct,
                    "has_description": bool(meta_description),
                    "chapters_count": len(meta_chapters) if meta_chapters else 0,
                    "email_render_s": None,
                    "email_send_s": None,
                    "total_before_send_s": None,
                    "total_to_send_s": None,
                    "qa_notes": "",
                }

                published_at_display = _fmt_published_at(v.published_at)
                video_duration_display = _fmt_duration(meta_duration_s or transcript_stats.audio_duration_s)
                render_ctx = dict(
                    subject=subject,
                    source_label=source_label,
                    source_name=video_channel_name,
                    video_title=clean_title,
                    video_url=v.url,
                    thumbnail_url=f"https://img.youtube.com/vi/{v.video_id}/maxresdefault.jpg",
                    sections=sections,
                    published_at=v.published_at,
                    published_at_display=published_at_display,
                    video_duration_display=video_duration_display,
                    beta_stats=beta_stats_view,
                )

                t_render = time.perf_counter()
                html = template.render(**render_ctx)
                email_render_ms = _ms_since(t_render)

                beta_stats = BetaStats(
                    **{**beta_stats.__dict__, "email_render_ms": email_render_ms, "total_ms": _ms_since(t_total)}
                )
                beta_stats_view["email_render_s"] = _fmt_seconds(beta_stats.email_render_ms)
                beta_stats_view["total_before_send_s"] = _fmt_seconds(beta_stats.total_ms)
                render_ctx["beta_stats"] = beta_stats_view
                html = template.render(**render_ctx)

                _write_summary_artifact(
                    root=root,
                    summary_id=summary_id,
                    channel_name=video_channel_name,
                    video_title=clean_title,
                    video_url=v.url,
                    video_id=v.video_id,
                    published_at=v.published_at,
                    transcript_source=transcript.source,
                    enabled_prompts=enabled_prompt_keys,
                    ollama_model=settings.ollama_model,
                    sections=sections,
                    beta_stats=beta_stats,
                )

                text = (
                    f"{video_channel_name}\n{clean_title}\n{v.url}\n\n"
                    f"{_format_sections_text(sections)}\n\n"
                    f"{_format_beta_stats_text(beta_stats)}\n"
                )

                email_ok = True
                if not settings.dry_run:
                    log.info("  sending email: %s", subject)
                    t_send = time.perf_counter()
                    try:
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
                        _append_summary_stats(root=root, summary_id=summary_id, beta_stats_view=beta_stats_view)
                    except Exception as e:
                        email_ok = False
                        log.error("  email send FAILED for '%s' (%s) — will retry next poll", clean_title, e)
                        beta_stats_view["qa_notes"] = f"email send failed: {e}"
                        _append_summary_stats(root=root, summary_id=summary_id, beta_stats_view=beta_stats_view)
                else:
                    log.info("  dry-run: email suppressed for '%s'", clean_title)
                    beta_stats_view["qa_notes"] = "dry-run (no email sent)"
                    beta_stats_view["total_processing_s"] = beta_stats_view.get("total_before_send_s")
                    _append_summary_stats(root=root, summary_id=summary_id, beta_stats_view=beta_stats_view)

                remaining -= 1
                processed += 1
                log.info("  done: total=%s remaining_slots=%d", _fmt_ms(_ms_since(t_total)), remaining)

    log.info("run_once complete: processed %d video(s)", processed)
    return processed


def run_forever(*, poll_seconds: int = 900, limit: int = 10) -> None:
    _load_dotenv_if_present(repo_root() / ".env")
    setup_logging()
    log.info("Starting watch loop (poll_seconds=%d, limit=%d)", poll_seconds, limit)
    while True:
        n = run_once(limit=limit)
        if n <= 0:
            log.debug("No new videos found — sleeping %ds", poll_seconds)
            time.sleep(max(5, int(poll_seconds)))
        else:
            continue


# ---------------------------------------------------------------------------
# Section builder
# ---------------------------------------------------------------------------

def _build_email_sections(
    *,
    transcript: str,
    ollama_model: str | None,
    tier: dict,
    root: Path,
    prompt_map: dict,
    video_context: str | None = None,
    chapters: list | None = None,
    video_url: str = "",
    video_duration_s: float | None = None,
) -> tuple[list[dict], list[str], list[str]]:
    """
    Builds email sections in fixed order:
    1. opener, 2. summary, 3. outline, 4. transcript
    Returns (sections, per_prompt_s, enabled_keys).
    """
    sections: list[dict] = []
    per_prompt_s: list[str] = []
    enabled_keys: list[str] = []

    is_short_video = (
        (video_duration_s is not None and video_duration_s < 180)
        or "/shorts/" in video_url
    )
    if is_short_video:
        log.info("  short video (duration=%s, url=%s) — skipping summary, outline, transcript",
                 f"{video_duration_s:.0f}s" if video_duration_s is not None else "unknown", video_url)

    # 1. Opener
    if "opener" in prompt_map:
        p = prompt_map["opener"]
        log.info("  [1/4] opener ...")
        t0 = time.perf_counter()
        tmpl = p.for_tier(tier["tier"])
        sentence_count = _opener_sentence_count(video_duration_s, len(transcript))
        out = _run_llm(transcript, ollama_model, tmpl, video_context=video_context, sentence_count=sentence_count)
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"opener={_fmt_ms(elapsed)}")
        enabled_keys.append("opener")
        log.info("  [1/4] opener done in %s", _fmt_ms(elapsed))
        sections.append({
            "key": "opener",
            "label": None,
            "style": "opener",
            "text": out,
            "html": _format_opener_html(out),
        })

    # 2. Summary
    if not is_short_video and "summary" in prompt_map:
        p = prompt_map["summary"]
        log.info("  [2/4] summary (%s tier) ...", tier["tier"])
        t0 = time.perf_counter()
        tmpl = p.for_tier(tier["tier"])
        out = _summarize(transcript, ollama_model, tmpl, video_context=video_context)
        out = _ensure_key_takeaways(out, transcript, ollama_model, min_bullets=int(tier["bullet_count"]))
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"summary={_fmt_ms(elapsed)}")
        enabled_keys.append("summary")
        log.info("  [2/4] summary done in %s", _fmt_ms(elapsed))
        sections.append({
            "key": "summary",
            "label": "Summary",
            "style": "body",
            "text": out,
            "html": _format_summary_html(out),
        })

    # 3. Outline — use creator-provided chapters if available, else LLM
    log.info("  [3/4] outline ...")
    t0 = time.perf_counter()
    if chapters:
        outline_html = _format_chapters_outline_html(chapters, video_url)
        outline_text = "\n".join(
            f"{_ts_fmt(int(ch.get('start_time') or 0))}  {ch.get('title','').strip()}"
            for ch in chapters
        )
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"outline(chapters)={_fmt_ms(elapsed)}")
        source_label_outline = "Chapters"
    elif "outline" in prompt_map:
        p = prompt_map["outline"]
        tmpl = p.for_tier(tier["tier"])
        outline_points = _outline_point_count(video_duration_s, len(transcript))
        out = _run_llm(transcript, ollama_model, tmpl, video_context=video_context, outline_points=outline_points)
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"outline={_fmt_ms(elapsed)}")
        outline_text = out
        outline_html = _format_outline_html(out)
        source_label_outline = "Outline"
    else:
        outline_text = outline_html = ""
        source_label_outline = "Outline"
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"outline=skipped")

    enabled_keys.append("outline")
    log.info("  [3/4] outline done in %s", _fmt_ms(elapsed))
    if outline_html:
        sections.append({
            "key": "outline",
            "label": source_label_outline,
            "style": "body",
            "text": outline_text,
            "html": outline_html,
        })

    # 5. Transcript (skipped for short videos < 3 min)
    if not is_short_video:
        log.info("  [4/4] transcript cleanup ...")
        t0 = time.perf_counter()
        cleaned = _clean_transcript_for_reading(transcript, ollama_model=ollama_model, video_context=video_context)
        elapsed = _ms_since(t0)
        per_prompt_s.append(f"transcript={_fmt_ms(elapsed)}")
        enabled_keys.append("transcript")
        log.info("  [4/4] transcript done in %s", _fmt_ms(elapsed))
        sections.append({
            "key": "transcript",
            "label": "Transcript",
            "style": "transcript",
            "text": cleaned,
            "html": _format_transcript_html(cleaned),
        })
    else:
        per_prompt_s.append("transcript=skipped(short)")
        log.info("  [4/4] transcript skipped (short video)")

    return sections, per_prompt_s, enabled_keys


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _run_llm(transcript: str, ollama_model: str | None, prompt_template: str, *, video_context: str | None = None, **extra_vars) -> str:
    """Run a prompt through Ollama with compacted transcript. Falls back to first 500 chars."""
    if ollama_model:
        try:
            out = summarize_with_ollama(
                transcript=transcript,
                model=ollama_model,
                prompt_template=prompt_template,
                compact=True,
                video_context=video_context,
                **extra_vars,
            )
            if out and out.strip():
                return out
            log.error("LLM call returned empty output — falling back to raw transcript snippet")
        except Exception as e:
            log.error("LLM call failed (%s) — falling back to raw transcript snippet", e)
    log.error("FALLBACK ACTIVE: email will contain raw transcript instead of LLM summary")
    return (transcript[:500] + "…").strip() if len(transcript) > 500 else transcript.strip()


def _outline_point_count(video_duration_s: float | None, transcript_chars: int) -> int:
    """Map video duration to outline point count. Falls back to transcript length."""
    if video_duration_s is not None:
        if video_duration_s < 300:    # < 5 min
            return 3
        elif video_duration_s < 900:  # 5–15 min
            return 5
        elif video_duration_s < 1800: # 15–30 min
            return 7
        else:                         # 30+ min
            return 10
    # Fallback: estimate from transcript chars
    if transcript_chars < 8000:
        return 3
    elif transcript_chars < 22000:
        return 5
    else:
        return 7


def _opener_sentence_count(video_duration_s: float | None, transcript_chars: int) -> int:
    """Map video duration to opener sentence count. Falls back to transcript length."""
    if video_duration_s is not None:
        if video_duration_s < 300:   # < 5 min
            return 1
        elif video_duration_s < 900:  # 5–15 min
            return 2
        elif video_duration_s < 1800: # 15–30 min
            return 3
        else:                         # 30+ min
            return 4
    # Fallback: estimate from transcript chars
    if transcript_chars < 8000:
        return 1
    elif transcript_chars < 22000:
        return 2
    else:
        return 3


def _summarize(transcript: str, ollama_model: str | None, prompt_template: str, *, video_context: str | None = None) -> str:
    if ollama_model:
        try:
            out = summarize_with_ollama(
                transcript=transcript,
                model=ollama_model,
                prompt_template=prompt_template,
                compact=True,
                video_context=video_context,
            )
            if out:
                return out
        except Exception as e:
            log.error("Ollama summarization failed (%s) — falling back to raw transcript snippet", e)
    log.error("FALLBACK ACTIVE: email will contain raw transcript instead of LLM summary")
    return summarize_fallback(transcript)



# ---------------------------------------------------------------------------
# Tier
# ---------------------------------------------------------------------------

def _summary_tier(transcript_chars: int) -> dict:
    if transcript_chars < 8_000:
        return {"tier": "short", "bullet_count": "3"}
    if transcript_chars < 22_000:
        return {"tier": "medium", "bullet_count": "5"}
    return {"tier": "long", "bullet_count": "7"}


# ---------------------------------------------------------------------------
# Transcript cleanup
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _TranscriptStats:
    transcript_source: str
    audio_download_ms: int | None
    audio_bytes: int | None
    audio_duration_s: float | None
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
                _TranscriptStats(transcript_source="youtube", audio_download_ms=None, audio_bytes=None, audio_duration_s=None, transcribe_ms=None),
            )

    backend = (transcribe_backend or "").strip()
    if backend not in ("parakeet_mlx", "whisper_cpp"):
        raise RuntimeError("Invalid YTS_TRANSCRIBE_BACKEND. Use parakeet_mlx or whisper_cpp.")

    audio_dir = root / "data" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_base = audio_dir / f"{video_id}"

    cookies_args: list[str] = []
    if ytdlp_cookies_file:
        cookies_args = ["--cookies", ytdlp_cookies_file]
    elif ytdlp_cookies_from_browser:
        cookies_args = ["--cookies-from-browser", ytdlp_cookies_from_browser]

    t_dl = time.perf_counter()
    _run([
        "yt-dlp",
        "-f", "bestaudio[abr<=96]/bestaudio",
        "--extract-audio",
        "--audio-format", "m4a",
        "--audio-quality", "5",
        *cookies_args,
        "-o", str(out_base) + ".%(ext)s",
        video_url,
    ])
    audio_download_ms = _ms_since(t_dl)

    audio_path = str(out_base) + ".m4a"
    if not Path(audio_path).exists():
        raise RuntimeError("Audio download failed (expected .m4a output).")
    audio_bytes = Path(audio_path).stat().st_size

    audio_duration_s: float | None = None
    try:
        _dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=15,
        )
        audio_duration_s = float(_dur.stdout.strip())
    except Exception:
        pass

    transcript_text = ""
    source = "parakeet"
    transcribe_ms: int | None = None

    if backend == "parakeet_mlx":
        wav_path = str(out_base) + "_16k.wav"
        _run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            wav_path,
        ])

        out_dir = audio_dir / "parakeet"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path_no_ext = out_dir / f"{video_id}"
        t_tx = time.perf_counter()
        _run([
            "parakeet-mlx",
            wav_path,
            "--model", parakeet_model,
            "--output-dir", str(out_dir),
            "--output-format", "txt",
            "--output-template", str(out_path_no_ext.name),
        ])
        transcribe_ms = _ms_since(t_tx)
        txt_path = out_dir / f"{out_path_no_ext.name}.txt"
        transcript_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""

        try:
            Path(wav_path).unlink()
        except OSError:
            pass

    if backend == "whisper_cpp":
        if not whisper_cpp_model:
            raise RuntimeError(
                "No YouTube transcript found, and whisper.cpp fallback is selected but missing a model path. "
                "Set YTS_WHISPER_CPP_MODEL in .env."
            )
        t_tx = time.perf_counter()
        transcript_text = _run_capture([
            "whisper-cli", "-m", whisper_cpp_model, "-nt", "-np", audio_path,
        ]).strip()
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
            audio_duration_s=audio_duration_s,
            transcribe_ms=transcribe_ms,
        ),
    )


def _clean_transcript_for_reading(transcript: str, *, ollama_model: str | None, video_context: str | None = None) -> str:
    """
    Cleans transcript for the email transcript section.
    Step 1: deterministic pre-pass (filler removal, paragraph breaks, etc.)
    Step 2: LLM cleanup (sentence boundaries, capitalization, false starts, topic headers)
    Uses the FULL transcript — no compaction.
    """
    t = (transcript or "").strip()
    if not t:
        return t

    # Step 1: Deterministic pre-pass
    opts = load_transcribe_options()

    if opts.get("strip_stage_directions", False):
        t = re.sub(
            r"\[(?:music|applause|laughter|silence|noise|intro|outro|advertisement)[^\]]*\]",
            "", t, flags=re.I,
        )
        t = re.sub(r"\s{2,}", " ", t).strip()

    if opts.get("remove_fillers", True):
        t = re.sub(r"(?i)\b(um+|uh+|er+|ah+|eh+|hmm+)\b", "", t)
        t = re.sub(r"(?i)\b(kind of|sort of|you know|i mean)\b", "", t)
        t = re.sub(r"(?i)\b(\w+)(\s+\1\b)+", r"\1", t)
        t = re.sub(r",\s*,+", ",", t)
        t = re.sub(r"(?<=[.!?])\s*,\s*", " ", t)
        t = re.sub(r"^\s*,\s*", "", t)
        t = re.sub(r"(?<=[.!?])\s+([a-z])", lambda m: " " + m.group(1).upper(), t)
        t = re.sub(r"\s{2,}", " ", t).strip()

    if opts.get("split_long_clauses", False):
        def _maybe_split_clause(m: re.Match) -> str:
            before_start = m.string.rfind(". ", 0, m.start())
            before_start = before_start + 2 if before_start >= 0 else 0
            clause_before = m.string[before_start: m.start()]
            clause_after = m.string[m.end():]
            next_end = clause_after.find(". ")
            clause_after_preview = clause_after if next_end < 0 else clause_after[:next_end]
            if len(clause_before.strip()) >= 60 and len(clause_after_preview.strip()) >= 40:
                return f". {m.group(1).capitalize()} "
            return m.group(0)
        t = re.sub(r",\s+(and|but)\s+", _maybe_split_clause, t)
        t = re.sub(r"\s{2,}", " ", t).strip()

    # Basic paragraph reflow
    if len(t) > 1200:
        target = 1000 if opts.get("robust_sentence_breaks", False) else 1400
        paras: list[str] = []
        buf = ""
        for part in re.split(r"(?<=[.!?])\s+", t):
            if not part:
                continue
            if buf and len(buf) + 1 + len(part) > target:
                paras.append(buf.strip())
                buf = part
            else:
                buf = (buf + " " + part).strip()
        if buf.strip():
            paras.append(buf.strip())
        t = "\n\n".join(paras).strip()

    if opts.get("questions_own_paragraph", False):
        t = re.sub(r"(?m)(^.*\?\s*$)", r"\n\1\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()

    if opts.get("qa_paragraph_breaks", False):
        t = re.sub(
            r"(?i)(?<!\n\n)(?<!\n)(\b(?:first|second|third|fourth|fifth|next|last|final|closing)\s+question\b)",
            r"\n\n\1", t,
        )
        t = re.sub(
            r"(?i)(?<!\n\n)(?<!\n)(\b[A-Z][a-z]+(?:\s+[A-Z][\w.]*)?\s+(?:writes?|asks?),)",
            r"\n\n\1", t,
        )
        t = re.sub(r"\n{3,}", "\n\n", t).strip()

    # Step 2: LLM cleanup — always runs, full transcript (no compaction)
    if ollama_model:
        transcribe_prompts = [p for p in load_transcribe_prompts() if p.enabled]
        if transcribe_prompts:
            prompt_template = transcribe_prompts[0].template.strip()
            if prompt_template:
                prompt = prompt_template.format(transcript=t)
                if video_context:
                    prompt = f"VIDEO CONTEXT\n{video_context}\n---\n\n{prompt}"
                try:
                    res = subprocess.run(
                        ["ollama", "run", ollama_model],
                        input=prompt,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                        timeout=600,
                        env=_child_env(),
                    )
                    out = (res.stdout or "").strip()
                    if out:
                        ratio = len(out) / max(len(t), 1)
                        out_lower = out.lower()
                        non_ws = re.sub(r"\s", "", out)
                        cjk_count = len(re.findall(
                            r"[\u2E80-\u2FFF\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", out
                        ))
                        is_cjk = bool(non_ws) and (cjk_count / len(non_ws)) > 0.15
                        hallucinated = (
                            is_cjk
                            or ratio < 0.4
                            or out_lower.startswith("from the transcript")
                            or out_lower.startswith("in summary")
                            or out_lower.startswith("based on the")
                            or "here are some key points" in out_lower
                            or "here are some key takeaways" in out_lower
                            or "let me know if" in out_lower
                        )
                        if hallucinated:
                            log.warning(
                                "Transcript LLM cleanup looks like a summary or non-English (ratio=%.2f, cjk=%s) — using deterministic output",
                                ratio, is_cjk,
                            )
                        else:
                            return out
                except Exception as e:
                    log.warning("Transcript LLM cleanup failed (%s) — using deterministic output", e)

    return t


# ---------------------------------------------------------------------------
# HTML formatters
# ---------------------------------------------------------------------------

def _apply_inline(text: str) -> str:
    """HTML-escape then apply **bold** markers."""
    escaped = str(escape(text))
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)


def _format_opener_html(text: str) -> Markup:
    s = (text or "").strip()
    if not s:
        return Markup("")
    return Markup(escape(s))


def _format_summary_html(summary: str) -> Markup:
    """
    Convert summary text into HTML.
    Handles paragraphs, bullets, Key takeaways header, walk-away.
    """
    s = (summary or "").strip()
    if not s:
        return Markup("")

    lines = [ln.rstrip() for ln in s.splitlines()]
    html_parts: list[str] = []
    in_list = False
    para_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal para_buf
        text = " ".join(x.strip() for x in para_buf if x.strip()).strip()
        para_buf = []
        if text:
            html_parts.append(f'<p style="margin:0 0 12px 0;">{_apply_inline(text)}</p>')

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
                '<div style="margin:14px 0 8px 0;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#6b6f85;font-weight:600;">Key takeaways</div>'
            )
            continue

        is_bullet = line.startswith("- ") or line.startswith("* ")
        if is_bullet:
            flush_paragraph()
            if not in_list:
                html_parts.append('<ul style="margin:0 0 12px 18px;padding:0;">')
                in_list = True
            html_parts.append(f'<li style="margin:0 0 7px 0;">{_apply_inline(line[2:].strip())}</li>')
            continue

        if in_list:
            html_parts.append("</ul>")
            in_list = False

        para_buf.append(line)

    flush_paragraph()
    if in_list:
        html_parts.append("</ul>")

    return Markup("\n".join(html_parts))



def _format_outline_html(text: str) -> Markup:
    s = (text or "").strip()
    if not s:
        return Markup("")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    # Strip leading bullets/dashes/numbers the model sometimes adds
    clean_lines = [re.sub(r"^[\-\*\•]\s*|^\d+[\.\)]\s*", "", ln).strip() for ln in lines]
    items = "".join(
        f'<li style="margin:0 0 8px 0;color:#1e2138;">{escape(ln)}</li>'
        for ln in clean_lines if ln
    )
    return Markup(f'<ol style="margin:0;padding-left:22px;">{items}</ol>')


def _ts_fmt(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


_CHAPTER_TITLE_MAX = 52  # characters before truncation with ellipsis


def _format_chapters_outline_html(chapters: list, video_url: str) -> str:
    """Render creator chapters as a linked list with timestamp URLs."""
    # Build base URL for timestamp anchors: strip existing &t= if present
    base = re.sub(r"[&?]t=\d+", "", video_url)
    sep = "&" if "?" in base else "?"
    items = []
    for ch in chapters:
        t = int(ch.get("start_time") or 0)
        ts_url = f"{base}{sep}t={t}"
        ts_display = _ts_fmt(t)
        raw_title = ch.get("title", "").strip()
        if len(raw_title) > _CHAPTER_TITLE_MAX:
            raw_title = raw_title[:_CHAPTER_TITLE_MAX].rstrip() + "\u2026"
        title = escape(raw_title)
        items.append(
            f'<span style="color:#9096bb;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;">'
            f'<a href="{ts_url}" style="color:#9096bb;text-decoration:none;">{ts_display}</a>'
            f'</span>'
            f'&ensp;{title}'
        )
    return Markup("<br>\n".join(items))


def _fetch_video_metadata(video_url: str, cookies_args: list[str]) -> dict:
    """Fetch yt-dlp JSON metadata (no download). Returns {} on any failure."""
    try:
        res = subprocess.run(
            ["yt-dlp", "--dump-json", *cookies_args, video_url],
            capture_output=True, text=True, timeout=30, env=_child_env(),
        )
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout.strip())
    except Exception as e:
        log.debug("_fetch_video_metadata failed: %s", e)
    return {}


def _build_video_context(title: str, description: str | None, chapters: list | None) -> str | None:
    parts: list[str] = []
    if description and description.strip():
        desc = description.strip()
        if len(desc) > 900:
            # Keep first 900 chars, try to cut at a newline boundary
            cut = desc.rfind("\n", 0, 900)
            desc = desc[: cut if cut > 400 else 900].strip() + "…"
        parts.append(f"Description:\n{desc}")
    if chapters:
        lines = []
        for ch in chapters:
            t = int(ch.get("start_time") or 0)
            h, rem = divmod(t, 3600)
            m, s = divmod(rem, 60)
            ts = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            lines.append(f"{ts}  {ch.get('title', '').strip()}")
        if lines:
            parts.append("Chapters:\n" + "\n".join(lines))
    if not parts:
        return None
    return f"Title: {title}\n" + "\n\n".join(parts)


def _format_transcript_html(transcript: str) -> Markup:
    s = (transcript or "").strip()
    if not s:
        return Markup("")

    # Split into paragraphs and render as <p> tags
    paras = [p.strip() for p in re.split(r"\n\n+", s) if p.strip()]
    if not paras:
        return Markup(f'<div style="white-space:pre-wrap;">{escape(s)}</div>')

    html_parts = []
    for para in paras:
        lines = para.splitlines()
        # Check if first line looks like a section header (short, no sentence-ending punctuation)
        if len(lines) >= 2 and len(lines[0]) < 60 and not lines[0].rstrip().endswith((".", "?", "!", ",")):
            header = escape(lines[0].strip())
            body = escape(" ".join(ln.strip() for ln in lines[1:]).strip())
            html_parts.append(
                f'<p style="margin:0 0 4px 0;font-weight:600;color:#22253d;font-size:13px;">{header}</p>'
                f'<p style="margin:0 0 14px 0;">{body}</p>'
            )
        else:
            html_parts.append(f'<p style="margin:0 0 14px 0;">{escape(para)}</p>')

    return Markup("\n".join(html_parts))


# ---------------------------------------------------------------------------
# Key-takeaways repair
# ---------------------------------------------------------------------------

def _ensure_key_takeaways(summary: str, transcript: str, ollama_model: str | None, *, min_bullets: int = 3) -> str:
    s = (summary or "").strip()
    if not s:
        return s

    if _has_enough_bullets(s, min_bullets):
        return _trim_bullets(s, min_bullets)

    if not ollama_model:
        repaired = _trim_bullets(s, min_bullets)
        if _has_enough_bullets(repaired, min_bullets):
            return repaired
        core = "\n".join([ln for ln in s.splitlines() if ln.strip()][:12]).strip()
        bullets_placeholder = "\n".join(f"- Key point {i+1}" for i in range(min_bullets))
        return (core + f"\n\nKey takeaways\n{bullets_placeholder}\n").strip()

    bullet_examples = "\n".join(f"- <point {i+1}>" for i in range(min_bullets))
    prompt = f"""Rewrite the summary below so it follows this format exactly. Output ONLY the rewritten summary — no preamble, no explanation.

REQUIRED FORMAT:
<1 sentence intro>

<prose paragraphs>

Key takeaways
{bullet_examples}

<wrap-up sentence(s)>

Rules:
- Plain prose paragraphs only (no bullets, no bold, no headers in the paragraphs)
- The line "Key takeaways" must appear exactly as written, alone on its line
- Exactly {min_bullets} bullets after "Key takeaways", each starting with "- "
- End with a wrap-up after the bullets
- Do NOT start with "Here is", "Here's", or any preamble

Current (malformed) summary:
\"\"\"
{s}
\"\"\"
"""
    try:
        res = subprocess.run(
            ["ollama", "run", ollama_model],
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=120,
            env=_child_env(),
        )
        fixed = (res.stdout or "").strip() or s
        return _trim_bullets(fixed, min_bullets)
    except Exception:
        return _trim_bullets(s, min_bullets)


def _has_enough_bullets(text: str, min_count: int = 3) -> bool:
    m = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", text)
    if not m:
        return False
    after = text[m.end():].strip("\n")
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
    return len(bullets) >= min_count


def _trim_bullets(text: str, max_count: int = 3) -> str:
    m = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", text)
    if not m:
        return text.strip()
    before = text[: m.start()].rstrip()
    after = text[m.end():].lstrip()
    bullets = []
    remaining_lines = []
    collecting_remaining = False
    for ln in after.splitlines():
        line = ln.strip()
        if not collecting_remaining and line.startswith("- "):
            bullets.append(line)
        elif bullets:
            collecting_remaining = True
            if line:
                remaining_lines.append(line)
    bullets = bullets[:max_count]
    parts = [before, "Key takeaways", "\n".join(bullets)]
    if remaining_lines:
        parts.append(" ".join(remaining_lines))
    return "\n\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, env=_child_env())
    except subprocess.CalledProcessError as e:
        if cmd and cmd[0] == "yt-dlp":
            msg = (getattr(e, "stderr", None) or "") if hasattr(e, "stderr") else ""
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
    env = dict(os.environ)
    venv_bin = str(Path(sys.executable).parent)
    base_path = env.get("PATH", "")
    brew_prefixes = ["/opt/homebrew/bin", "/opt/homebrew/sbin"]
    for p in reversed(brew_prefixes):
        if p and p not in base_path:
            base_path = f"{p}{os.pathsep}{base_path}" if base_path else p
    env["PATH"] = f"{venv_bin}{os.pathsep}{base_path}"
    return env


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: float | None) -> str | None:
    if not seconds:
        return None
    s = int(seconds)
    if s < 60:
        return f"{s} sec"
    if s < 3600:
        m = round(s / 60)
        return f"{m} min"
    h, rem = divmod(s, 3600)
    m = round(rem / 60)
    return f"{h} hr {m} min" if m else f"{h} hr"


def _fmt_published_at(published_at: str) -> str:
    if not published_at:
        return ""
    from zoneinfo import ZoneInfo
    eastern = ZoneInfo("America/New_York")
    try:
        dt = parsedate_to_datetime(published_at).astimezone(eastern)
        return dt.strftime("%A %Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(eastern)
        return dt.strftime("%A %Y-%m-%d %H:%M")
    except Exception:
        pass
    return published_at


# ---------------------------------------------------------------------------
# Stats / artifacts
# ---------------------------------------------------------------------------

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
        f"- download_media_s: {_fmt_ms(s.audio_download_ms)}",
        f"- transcribe_s: {_fmt_ms(s.transcribe_ms)}",
        f"- summarize_s: {_fmt_ms(s.summarize_ms)}",
        "---",
    ]
    return "\n".join(lines)


def _format_sections_text(sections: list[dict]) -> str:
    parts: list[str] = []
    for i, s in enumerate(sections):
        label = str(s.get("label", "") or s.get("key", "") or "").strip() or "Section"
        text = str(s.get("text", "") or "").strip()
        if i > 0:
            parts.append("\n---\n")
        parts.append(f"{label}\n{text}".strip())
    return "\n\n".join([p for p in parts if p.strip()]).strip()


def _new_summary_id(video_id: str) -> str:
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
    sections: list[dict],
    beta_stats: BetaStats,
) -> None:
    path = _summaries_dir(root) / f"{summary_id}.txt"
    beta_lines = _format_beta_stats_text(beta_stats)
    body = "\n".join([
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
    ])
    path.write_text(body, encoding="utf-8")


def _append_summary_stats(*, root: Path, summary_id: str, beta_stats_view: dict) -> None:
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


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _best_effort_update_channel_name_in_config(*, config_path: Path, url: str, name: str) -> None:
    try:
        raw = config_path.read_text(encoding="utf-8")
    except Exception:
        return
    u = url.replace("\\", "\\\\").replace('"', '\\"')
    n = name.replace("\\", "\\\\").replace('"', '\\"')

    def repl(match: re.Match) -> str:
        block = match.group(0)
        if "name" in block:
            return block
        return block.replace("{", '{ name = "' + n + '", ', 1)

    pattern = re.compile(r"\{[^}]*\burl\s*=\s*\"" + re.escape(u) + r"\"[^}]*\}")
    updated, n_subs = pattern.subn(repl, raw, count=1)
    if n_subs <= 0 or updated == raw:
        return
    try:
        config_path.write_text(updated, encoding="utf-8")
    except Exception:
        return


# ---------------------------------------------------------------------------
# Cleanup / yt-dlp playlist
# ---------------------------------------------------------------------------

def _cleanup_downloads(root: Path) -> None:
    keep_days_raw = os.environ.get("YTS_AUDIO_RETENTION_DAYS", "").strip()
    try:
        keep_days = int(keep_days_raw) if keep_days_raw else 7
    except Exception:
        keep_days = 7

    if keep_days < 0:
        return

    cutoff = time.time() - (keep_days * 24 * 60 * 60)
    dirs = [root / "data" / "audio", root / "data" / "audio" / "parakeet"]
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
                continue


def _fetch_videos_via_ytdlp_playlist(
    *,
    playlist_url: str,
    limit: int,
    ytdlp_cookies_from_browser: str | None,
    ytdlp_cookies_file: str | None,
) -> list:
    cookies_args: list[str] = []
    if ytdlp_cookies_file:
        cookies_args = ["--cookies", ytdlp_cookies_file]
    elif ytdlp_cookies_from_browser:
        cookies_args = ["--cookies-from-browser", ytdlp_cookies_from_browser]

    try:
        res = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-single-json", *cookies_args, playlist_url],
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
        channel_name = str((e or {}).get("uploader") or (e or {}).get("channel") or "").strip() or None
        if not vid:
            continue
        out.append(type("Video", (), {
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": title,
            "published_at": now_iso,
            "channel_name": channel_name,
        })())
    return out


def _load_dotenv_if_present(path: Path) -> None:
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
