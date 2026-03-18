from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from youtube_summarizer import db
from youtube_summarizer.config import load_channels, load_prompts, load_settings, repo_root
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.summarizer import summarize_fallback, summarize_with_ollama
from youtube_summarizer.youtube import fetch_latest_videos_from_rss, fetch_youtube_transcript, source_url_to_rss


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    source: str  # "youtube" | "macwhisper" (fallback can be whisper.cpp)


def run_once(limit: int = 10) -> None:
    _load_dotenv_if_present(repo_root() / ".env")

    settings = load_settings()
    channels = load_channels()
    prompts = load_prompts()
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

                if settings.dry_run:
                    transcript = TranscriptResult(text="[dry-run placeholder transcript]", source="mock")
                else:
                    transcript = _get_transcript(
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
                summary = _summarize(transcript.text, settings.ollama_model, prompt_template)

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

                if not settings.dry_run:
                    send_gmail_smtp(
                        email_from=settings.email_from,
                        email_to=settings.email_to,
                        gmail_app_password=settings.gmail_app_password,
                        content=EmailContent(subject=subject, text=text, html=html),
                    )

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


def _get_transcript(
    video_id: str,
    video_url: str,
    transcribe_backend: str,
    parakeet_model: str,
    whisper_cpp_model: str | None,
    ytdlp_cookies_from_browser: str | None,
    ytdlp_cookies_file: str | None,
    root: Path,
) -> TranscriptResult:
    yt = fetch_youtube_transcript(video_id)
    if yt:
        return TranscriptResult(text=yt, source="youtube")

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

    _run(
        [
            "yt-dlp",
            "-f",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "m4a",
            *cookies_args,
            "-o",
            str(out_base) + ".%(ext)s",
            video_url,
        ]
    )

    audio_path = str(out_base) + ".m4a"
    if not Path(audio_path).exists():
        raise RuntimeError("Audio download failed (expected .m4a output).")

    transcript_text = ""
    source = "macwhisper"

    if backend == "parakeet_mlx":
        # `parakeet-mlx` writes outputs to files; we read the .txt output.
        out_dir = audio_dir / "parakeet"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path_no_ext = out_dir / f"{video_id}"
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
        txt_path = out_dir / f"{out_path_no_ext.name}.txt"
        transcript_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        source = "parakeet"

    if backend == "whisper_cpp":
        if not whisper_cpp_model:
            raise RuntimeError(
                "No YouTube transcript found, and whisper.cpp fallback is selected but missing a model path. "
                "Set YTS_WHISPER_CPP_MODEL in .env to a ggml model file (e.g., ggml-base.en.bin)."
            )
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
        source = "whisper_cpp"

    if not transcript_text:
        raise RuntimeError("Transcription fallback returned empty transcript.")
    return TranscriptResult(text=transcript_text, source=source)


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

