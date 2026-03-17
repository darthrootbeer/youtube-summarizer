from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    name: str
    url: str


@dataclass(frozen=True)
class Settings:
    email_from: str
    email_to: str
    gmail_app_password: str
    subject_prefix: str
    macwhisper_cmd: str | None


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
        if not name or not url:
            continue
        out.append(Channel(name=name, url=url))
    return out


def load_settings() -> Settings:
    # We intentionally keep this simple: values come from environment variables.
    email_from = os.environ.get("YTS_EMAIL_FROM", "").strip()
    email_to = os.environ.get("YTS_EMAIL_TO", "").strip()
    gmail_app_password = os.environ.get("YTS_GMAIL_APP_PASSWORD", "").strip()
    subject_prefix = os.environ.get("YTS_SUBJECT_PREFIX", "[YT Summary] ").strip() or "[YT Summary] "
    macwhisper_cmd = os.environ.get("YTS_MACWHISPER_CMD", "").strip() or None

    missing = []
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
        macwhisper_cmd=macwhisper_cmd,
    )

