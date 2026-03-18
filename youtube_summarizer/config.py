from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    prompt: str | None = None


@dataclass(frozen=True)
class Settings:
    email_from: str
    email_to: str
    gmail_app_password: str
    subject_prefix: str
    transcribe_backend: str
    parakeet_model: str
    whisper_cpp_model: str | None
    ollama_model: str | None
    dry_run: bool
    ytdlp_cookies_from_browser: str | None
    ytdlp_cookies_file: str | None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_channels(path: Path | None = None) -> list[Channel]:
    cfg_path = path or (repo_root() / "config" / "channels.toml")
    raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    channels = raw.get("channels", [])
    out: list[Channel] = []
    for item in channels:
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        prompt = str(item.get("prompt", "")).strip() or None
        if not name or not url:
            continue
        out.append(Channel(name=name, url=url, prompt=prompt))
    return out


def load_prompts(path: Path | None = None) -> dict[str, str]:
    cfg_path = path or (repo_root() / "config" / "prompts.toml")
    raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    prompts = raw.get("prompts", {}) or {}
    out: dict[str, str] = {}
    for k, v in prompts.items():
        key = str(k).strip()
        val = str(v or "").strip()
        if not key or not val:
            continue
        out[key] = val
    if "default" not in out:
        raise RuntimeError("Missing prompts.default in config/prompts.toml")
    return out


def load_settings() -> Settings:
    # We intentionally keep this simple: values come from environment variables.
    email_from = os.environ.get("YTS_EMAIL_FROM", "").strip()
    email_to = os.environ.get("YTS_EMAIL_TO", "").strip()
    gmail_app_password = os.environ.get("YTS_GMAIL_APP_PASSWORD", "").strip()
    subject_prefix = os.environ.get("YTS_SUBJECT_PREFIX", "[YT Summary] ").strip() or "[YT Summary] "
    transcribe_backend = os.environ.get("YTS_TRANSCRIBE_BACKEND", "parakeet_mlx").strip() or "parakeet_mlx"
    parakeet_model = os.environ.get("YTS_PARAKEET_MODEL", "mlx-community/parakeet-tdt-0.6b-v3").strip() or "mlx-community/parakeet-tdt-0.6b-v3"
    whisper_cpp_model = os.environ.get("YTS_WHISPER_CPP_MODEL", "").strip() or None
    ollama_model = os.environ.get("YTS_OLLAMA_MODEL", "").strip() or None
    dry_run = os.environ.get("YTS_DRY_RUN", "").strip().lower() in ("1", "true", "yes", "y", "on")
    ytdlp_cookies_from_browser = os.environ.get("YTS_YTDLP_COOKIES_FROM_BROWSER", "").strip() or None
    ytdlp_cookies_file = os.environ.get("YTS_YTDLP_COOKIES_FILE", "").strip() or None

    missing = []
    if not dry_run:
        if not email_from:
            missing.append("YTS_EMAIL_FROM")
        if not email_to:
            missing.append("YTS_EMAIL_TO")
        if not gmail_app_password:
            missing.append("YTS_GMAIL_APP_PASSWORD")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing) + ". "
            "Copy .env.example to .env and fill it in."
        )

    return Settings(
        email_from=email_from,
        email_to=email_to,
        gmail_app_password=gmail_app_password,
        subject_prefix=subject_prefix,
        transcribe_backend=transcribe_backend,
        parakeet_model=parakeet_model,
        whisper_cpp_model=whisper_cpp_model,
        ollama_model=ollama_model,
        dry_run=dry_run,
        ytdlp_cookies_from_browser=ytdlp_cookies_from_browser,
        ytdlp_cookies_file=ytdlp_cookies_file,
    )

