from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    name: str | None
    url: str
    mode: str  # "summarize" | "transcribe"
    source_type: str  # "subscription" | "summarize_queue" | "transcribe_queue"
    prompts: list | None = None


@dataclass(frozen=True)
class Settings:
    email_from: str
    email_to: str
    gmail_app_password: str
    subject_prefix: str
    dry_run: bool
    ytdlp_cookies_from_browser: str | None
    ytdlp_cookies_file: str | None
    ollama_model: str
    ollama_timeout: int
    max_retries: int
    data_dir: Path
    prompts_dir: Path
    parakeet_model: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    """Simple .env parser: KEY=VALUE, strips quotes, skips comments."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_prompts_field(item: dict) -> list | None:
    if "prompts" in item:
        val = item["prompts"]
        if isinstance(val, list):
            keys = [str(k).strip() for k in val if str(k).strip()]
            return keys or None
        if isinstance(val, str) and val.strip():
            return [val.strip()]
    if "prompt" in item:
        val = str(item["prompt"]).strip()
        return [val] if val else None
    return None


def load_channels(path: Path | None = None) -> list[Channel]:
    cfg_path = path or (repo_root() / "config" / "channels.toml")
    if not cfg_path.exists():
        example = cfg_path.parent / "channels.example.toml"
        raise FileNotFoundError(
            f"{cfg_path} not found. "
            f"Copy the example to get started:\n"
            f"  cp {example} {cfg_path}\n"
            f"Then edit it to add your channels and playlist URLs."
        )
    raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    out: list[Channel] = []

    for item in raw.get("subscriptions", []):
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        name = str(item.get("name", "")).strip() or None
        prompts = _parse_prompts_field(item)
        out.append(Channel(name=name, url=url, mode="summarize", source_type="subscription", prompts=prompts))

    sq = raw.get("summarize_queue")
    if sq:
        url = str(sq.get("url", "")).strip()
        if url:
            name = str(sq.get("name", "")).strip() or None
            prompts = _parse_prompts_field(sq)
            out.append(Channel(name=name, url=url, mode="summarize", source_type="summarize_queue", prompts=prompts))

    tq = raw.get("transcribe_queue")
    if tq:
        url = str(tq.get("url", "")).strip()
        if url:
            name = str(tq.get("name", "")).strip() or None
            out.append(Channel(name=name, url=url, mode="transcribe", source_type="transcribe_queue"))

    return out


def load_settings() -> Settings:
    email_from = os.environ.get("YTS_EMAIL_FROM", "").strip()
    email_to = os.environ.get("YTS_EMAIL_TO", "").strip()
    gmail_app_password = os.environ.get("YTS_GMAIL_APP_PASSWORD", "").strip()
    subject_prefix = os.environ.get("YTS_SUBJECT_PREFIX", "[YT Summary] ").strip() or "[YT Summary] "
    dry_run = os.environ.get("YTS_DRY_RUN", "").strip().lower() in ("1", "true", "yes", "y", "on")
    ytdlp_cookies_from_browser = os.environ.get("YTS_YTDLP_COOKIES_FROM_BROWSER", "").strip() or None
    ytdlp_cookies_file = os.environ.get("YTS_YTDLP_COOKIES_FILE", "").strip() or None
    ollama_model = os.environ.get("YTS_OLLAMA_MODEL", "qwen2.5:14b").strip() or "qwen2.5:14b"
    ollama_timeout = int(os.environ.get("YTS_OLLAMA_TIMEOUT", "300").strip() or "300")
    max_retries = int(os.environ.get("YTS_LLM_MAX_RETRIES", "2").strip() or "2")
    data_dir = Path(os.environ.get("YTS_DATA_DIR", "").strip() or str(repo_root() / "data"))
    prompts_dir = Path(os.environ.get("YTS_PROMPTS_DIR", "").strip() or str(repo_root() / "config" / "prompts"))
    parakeet_model = os.environ.get("YTS_PARAKEET_MODEL", "mlx-community/parakeet-tdt-0.6b-v2").strip() or "mlx-community/parakeet-tdt-0.6b-v2"

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
        dry_run=dry_run,
        ytdlp_cookies_from_browser=ytdlp_cookies_from_browser,
        ytdlp_cookies_file=ytdlp_cookies_file,
        ollama_model=ollama_model,
        ollama_timeout=ollama_timeout,
        max_retries=max_retries,
        data_dir=data_dir,
        prompts_dir=prompts_dir,
        parakeet_model=parakeet_model,
    )
