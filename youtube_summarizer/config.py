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
    prompts: list | None = None  # if set, only these prompt keys run (else all enabled prompts)


@dataclass
class ProcessPrompt:
    key: str
    label: str
    enabled: bool
    # Tiered templates keyed by "short", "medium", "long".
    # Single-template prompts (transcribe, legacy) store the same value under all three keys.
    templates: dict

    @property
    def template(self) -> str:
        """Backwards-compat: returns the medium template."""
        return self.templates.get("medium") or next(iter(self.templates.values()), "")

    def for_tier(self, tier: str) -> str:
        """Return the template for the given tier, falling back to medium."""
        return self.templates.get(tier) or self.template


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


def _parse_prompts_field(item: dict) -> list | None:
    """
    Parse the prompts field from a channel config item.
    Supports:
      prompts = ["default", "glossary"]   # new list form
      prompt  = "default"                 # legacy single-string form
    Returns None if neither is set (meaning: run all enabled prompts).
    """
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

    # Subscriptions — new-content-only channels/playlists (summarize mode)
    for item in raw.get("subscriptions", []):
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        name = str(item.get("name", "")).strip() or None
        prompts = _parse_prompts_field(item)
        out.append(Channel(name=name, url=url, mode="summarize", source_type="subscription", prompts=prompts))

    # Summarize queue — personal playlist, drain to empty (summarize mode)
    sq = raw.get("summarize_queue")
    if sq:
        url = str(sq.get("url", "")).strip()
        if url:
            name = str(sq.get("name", "")).strip() or None
            prompts = _parse_prompts_field(sq)
            out.append(Channel(name=name, url=url, mode="summarize", source_type="summarize_queue", prompts=prompts))

    # Transcribe queue — personal playlist, drain to empty (transcribe mode)
    tq = raw.get("transcribe_queue")
    if tq:
        url = str(tq.get("url", "")).strip()
        if url:
            name = str(tq.get("name", "")).strip() or None
            out.append(Channel(name=name, url=url, mode="transcribe", source_type="transcribe_queue"))

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


_PROCESS_SECTION_RE = re.compile(r"(?m)^###\s+([a-zA-Z0-9_-]+)\s*$")
_PROCESS_ENABLED_RE = re.compile(r"(?mi)^\s*enabled\s*:\s*(true|false)\s*$")
_PROCESS_LABEL_RE = re.compile(r"(?mi)^\s*label\s*:\s*(.+?)\s*$")
_PROCESS_FENCE_RE = re.compile(r"(?s)```prompt\s*(.*?)\s*```")
# Matches "## short", "## medium", "## long" tier headers in per-file prompt format
_TIER_SECTION_RE = re.compile(r"(?m)^##\s+(short|medium|long)\s*$")


def _parse_tiered_prompt_file(raw: str) -> dict[str, str]:
    """
    Parse a prompt file that has ## short / ## medium / ## long sections,
    each containing a ```prompt``` block.  Returns {"short": ..., "medium": ..., "long": ...}.
    Falls back: missing tiers inherit from medium, then from whatever is present.
    """
    tiers: dict[str, str] = {}
    sections = list(_TIER_SECTION_RE.finditer(raw))
    for i, m in enumerate(sections):
        tier = m.group(1).lower()
        start = m.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(raw)
        block = raw[start:end]
        fence_m = _PROCESS_FENCE_RE.search(block)
        if fence_m:
            t = fence_m.group(1).strip()
            if t and "{transcript}" in t:
                tiers[tier] = t
    if not tiers:
        return {}
    fallback = tiers.get("medium") or next(iter(tiers.values()))
    return {
        "short": tiers.get("short", fallback),
        "medium": tiers.get("medium", fallback),
        "long": tiers.get("long", fallback),
    }


def _key_from_filename(name: str) -> str:
    """'01_default.md' -> 'default'"""
    stem = Path(name).stem          # '01_default'
    stem = re.sub(r"^\d+_?", "", stem)  # 'default'
    return stem


def load_process_prompts(path: Path | None = None) -> list[ProcessPrompt]:
    """
    Loads prompt definitions.  Prefers individual files in `config/prompts/`,
    falling back to `config/process.md` if the directory doesn't exist.
    """
    prompts_dir = repo_root() / "config" / "prompts"
    if prompts_dir.is_dir():
        return _load_process_prompts_from_dir(prompts_dir)

    # Legacy: single process.md file
    cfg_path = path or (repo_root() / "config" / "process.md")
    if not cfg_path.exists():
        prompts = load_prompts()
        t = prompts["default"]
        return [ProcessPrompt(key="default", label="Default", enabled=True,
                              templates={"short": t, "medium": t, "long": t})]

    return _load_process_prompts_from_md(cfg_path)


def _load_process_prompts_from_dir(prompts_dir: Path) -> list[ProcessPrompt]:
    out: list[ProcessPrompt] = []
    for p in sorted(prompts_dir.glob("*.md")):
        if p.name.upper().startswith("README"):
            continue
        raw = p.read_text(encoding="utf-8")
        key = _key_from_filename(p.name)

        enabled_m = _PROCESS_ENABLED_RE.search(raw)
        enabled = (enabled_m.group(1).lower() == "true") if enabled_m else False

        label_m = _PROCESS_LABEL_RE.search(raw)
        label = (label_m.group(1).strip() if label_m else key).strip()

        templates = _parse_tiered_prompt_file(raw)
        if not templates:
            continue

        out.append(ProcessPrompt(key=key, label=label, enabled=enabled, templates=templates))

    if not any(p.enabled for p in out):
        # Emergency fallback
        prompts = load_prompts()
        t = prompts["default"]
        out.insert(0, ProcessPrompt(key="default", label="Default", enabled=True,
                                    templates={"short": t, "medium": t, "long": t}))
    return out


def _load_process_prompts_from_md(cfg_path: Path) -> list[ProcessPrompt]:
    raw = cfg_path.read_text(encoding="utf-8")
    sections = list(_PROCESS_SECTION_RE.finditer(raw))
    out: list[ProcessPrompt] = []
    for i, m in enumerate(sections):
        key = m.group(1).strip()
        start = m.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(raw)
        block = raw[start:end]

        enabled_m = _PROCESS_ENABLED_RE.search(block)
        enabled = (enabled_m.group(1).lower() == "true") if enabled_m else False

        label_m = _PROCESS_LABEL_RE.search(block)
        label = (label_m.group(1).strip() if label_m else key).strip()

        fence_m = _PROCESS_FENCE_RE.search(block)
        template = (fence_m.group(1).strip() if fence_m else "").strip()
        if not template or "{transcript}" not in template:
            continue

        templates = {"short": template, "medium": template, "long": template}
        out.append(ProcessPrompt(key=key, label=label, enabled=enabled, templates=templates))

    if not any(p.enabled for p in out):
        prompts = load_prompts()
        t = prompts["default"]
        out.insert(0, ProcessPrompt(key="default", label="Default", enabled=True,
                                    templates={"short": t, "medium": t, "long": t}))
    return out


def load_transcribe_prompts(path: Path | None = None) -> list[ProcessPrompt]:
    """
    Loads markdown-based prompt definitions from `config/transcribe.md`.
    Same shape as `config/process.md`, but used for transcript cleanup (transcribe mode).
    """
    cfg_path = path or (repo_root() / "config" / "transcribe.md")
    if not cfg_path.exists():
        return []

    raw = cfg_path.read_text(encoding="utf-8")
    sections = list(_PROCESS_SECTION_RE.finditer(raw))
    out: list[ProcessPrompt] = []
    for i, m in enumerate(sections):
        key = m.group(1).strip()
        start = m.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(raw)
        block = raw[start:end]

        enabled_m = _PROCESS_ENABLED_RE.search(block)
        enabled = (enabled_m.group(1).lower() == "true") if enabled_m else False

        label_m = _PROCESS_LABEL_RE.search(block)
        label = (label_m.group(1).strip() if label_m else key).strip()

        fence_m = _PROCESS_FENCE_RE.search(block)
        template = (fence_m.group(1).strip() if fence_m else "").strip()
        if not template or "{transcript}" not in template:
            continue

        templates = {"short": template, "medium": template, "long": template}
        out.append(ProcessPrompt(key=key, label=label, enabled=enabled, templates=templates))

    return out


def load_transcribe_options(path: Path | None = None) -> dict[str, bool]:
    """
    Parse boolean options from `config/transcribe.md`.
    Format: `key: true|false` anywhere in the file (first match wins).
    """
    cfg_path = path or (repo_root() / "config" / "transcribe.md")
    if not cfg_path.exists():
        return {}
    raw = cfg_path.read_text(encoding="utf-8")
    opts: dict[str, bool] = {}
    for m in re.finditer(r"(?mi)^\s*([a-zA-Z0-9_]+)\s*:\s*(true|false)\s*$", raw):
        k = m.group(1).strip()
        v = m.group(2).strip().lower() == "true"
        if k not in opts:
            opts[k] = v
    return opts


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

