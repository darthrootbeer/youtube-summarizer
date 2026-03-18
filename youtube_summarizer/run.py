from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from youtube_summarizer import db
from youtube_summarizer.config import load_channels, load_prompts, load_settings, repo_root
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.summarizer import summarize_fallback, summarize_with_ollama
from youtube_summarizer.youtube import fetch_latest_videos_from_rss, fetch_youtube_transcript, source_url_to_rss


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    source: str  # "youtube" | "macwhisper" (fallback can be whisper.cpp)

@dataclass(frozen=True)
class BetaStats:
    video_id: str
    transcript_source: str
    prompt_key: str
    ollama_model: str | None
    rss_fetch_ms: int | None
    audio_download_ms: int | None
    audio_bytes: int | None
    transcribe_ms: int | None
    summarize_ms: int | None
    email_render_ms: int | None
    email_send_ms: int | None
    total_ms: int


def run_once(limit: int = 10) -> None:
    _load_dotenv_if_present(repo_root() / ".env")

    settings = load_settings()
    channels = load_channels()
    prompts = load_prompts()
    if not channels:
        raise RuntimeError("No channels configured. Add entries to config/channels.toml.")

    root = repo_root()
    _cleanup_downloads(root)
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

            # During beta, scan deeper into the RSS feed so we reliably find an unseen video.
            t_rss = time.perf_counter()
            videos = fetch_latest_videos_from_rss(rss, limit=30)
            rss_fetch_ms = _ms_since(t_rss)
            for v in videos:
                if remaining <= 0:
                    break
                if db.has_seen(conn, v.video_id):
                    continue

                t_total = time.perf_counter()
                if settings.dry_run:
                    transcript = TranscriptResult(text="[dry-run placeholder transcript]", source="mock")
                    transcript_stats = _TranscriptStats(
                        transcript_source="mock",
                        audio_download_ms=None,
                        audio_bytes=None,
                        transcribe_ms=None,
                    )
                else:
                    transcript, transcript_stats = _get_transcript(
                        video_id=v.video_id,
                        video_url=v.url,
                        transcribe_backend=settings.transcribe_backend,
                        parakeet_model=settings.parakeet_model,
                        whisper_cpp_model=settings.whisper_cpp_model,
                        ytdlp_cookies_from_browser=settings.ytdlp_cookies_from_browser,
                        ytdlp_cookies_file=settings.ytdlp_cookies_file,
                        root=root,
                    )
                prompt_key = ch.prompt or "default"
                prompt_template = prompts.get(prompt_key) or prompts["default"]
                t_sum = time.perf_counter()
                summary = _summarize(transcript.text, settings.ollama_model, prompt_template)
                summarize_ms = _ms_since(t_sum)

                subject = f"{settings.subject_prefix}{ch.name} — {v.title}"
                t_render = time.perf_counter()
                beta_stats = BetaStats(
                    video_id=v.video_id,
                    transcript_source=transcript.source,
                    prompt_key=prompt_key,
                    ollama_model=settings.ollama_model,
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
                    "transcript_source": beta_stats.transcript_source,
                    "prompt_key": beta_stats.prompt_key,
                    "ollama_model": beta_stats.ollama_model,
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
                }
                html = template.render(
                    subject=subject,
                    channel_name=ch.name,
                    video_title=v.title,
                    video_url=v.url,
                    summary_html=_format_summary_html(summary),
                    transcript_source=transcript.source,
                    published_at=v.published_at,
                    beta_stats=beta_stats_view,
                )
                email_render_ms = _ms_since(t_render)

                beta_stats = BetaStats(
                    **{**beta_stats.__dict__, "email_render_ms": email_render_ms, "total_ms": _ms_since(t_total)}
                )
                beta_stats_view["email_render_s"] = _fmt_seconds(beta_stats.email_render_ms)
                beta_stats_view["total_before_send_s"] = _fmt_seconds(beta_stats.total_ms)
                text = (
                    f"{ch.name}\n{v.title}\n{v.url}\n\nSummary:\n{summary}\n\n"
                    f"Transcript source: {transcript.source}\n\n"
                    f"{_format_beta_stats_text(beta_stats)}\n"
                )

                if not settings.dry_run:
                    t_send = time.perf_counter()
                    send_gmail_smtp(
                        email_from=settings.email_from,
                        email_to=settings.email_to,
                        gmail_app_password=settings.gmail_app_password,
                        content=EmailContent(subject=subject, text=text, html=html),
                    )
                    beta_stats = BetaStats(**{**beta_stats.__dict__, "email_send_ms": _ms_since(t_send)})
                    beta_stats_view["email_send_s"] = _fmt_seconds(beta_stats.email_send_ms)
                    total_to_send_s = None
                    if beta_stats_view["total_before_send_s"] is not None and beta_stats_view["email_send_s"] is not None:
                        total_to_send_s = round(beta_stats_view["total_before_send_s"] + beta_stats_view["email_send_s"], 2)
                    beta_stats_view["total_to_send_s"] = total_to_send_s

                if not settings.dry_run:
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


def _summarize(transcript: str, ollama_model: str | None, prompt_template: str) -> str:
    if ollama_model:
        try:
            out = summarize_with_ollama(transcript=transcript, model=ollama_model, prompt_template=prompt_template)
            if out:
                return out
        except Exception as e:
            # If Ollama is temporarily unavailable, we still send *something*.
            print(f"Warning: Ollama summarization failed ({e}), using fallback")
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
) -> tuple[TranscriptResult, _TranscriptStats]:
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
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


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
        f"- video_id: {s.video_id}",
        f"- transcript_source: {s.transcript_source}",
        f"- prompt: {s.prompt_key}",
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

