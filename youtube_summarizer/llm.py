from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

import requests

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class PromptTier(Enum):
    SHORT = "short"    # transcript < 3000 chars
    MEDIUM = "medium"  # 3000-15000 chars
    LONG = "long"      # > 15000 chars


@dataclass(frozen=True)
class LLMOutput:
    text: str
    tier: PromptTier
    attempts: int        # 1-3
    used_fallback: bool  # True if deterministic fallback was used


@dataclass(frozen=True)
class OutputContract:
    name: str
    validate: Callable[[str], bool]


class ContractViolationError(Exception):
    def __init__(self, contract_name: str, last_output: str = ""):
        self.contract_name = contract_name
        self.last_output = last_output
        super().__init__(f"LLM output failed {contract_name} contract after all retries")


# ---------------------------------------------------------------------------
# Validators -- pure functions, fully testable
# ---------------------------------------------------------------------------

_CHATBOT_PHRASES = (
    "it looks like", "it appears", "you've shared", "you have shared",
    "this transcript", "let me ", "i'll ", "sure,", "certainly,",
    "here's a", "feel free", "it sounds like", "it seems like",
    "based on the transcript", "based on your",
    "happy to help", "great question",
)


def validate_opener(text: str) -> bool:
    """1-4 sentences of plain declarative prose, no lists, no headers, no chatbot phrases."""
    s = (text or "").strip()
    if not s:
        return False
    lower = s.lower()
    if any(phrase in lower for phrase in _CHATBOT_PHRASES):
        return False
    # No markdown headers
    if re.search(r"^#{1,3}\s", s, re.MULTILINE):
        return False
    # No numbered lists
    if re.search(r"^\d+[.)]\s", s, re.MULTILINE):
        return False
    # No bullet lists
    if re.search(r"^[-*\u2022]\s", s, re.MULTILINE):
        return False
    # Max 500 chars
    if len(s) > 500:
        return False
    # At least one sentence
    sentences = [x.strip() for x in re.split(r"[.!?]+", s) if x.strip()]
    if len(sentences) < 1:
        return False
    return True


def validate_summary(text: str) -> bool:
    """Must have prose body + 'Key Takeaways' heading + 2+ bullets."""
    s = (text or "").strip()
    if not s:
        return False
    lower = s.lower()
    if any(phrase in lower for phrase in _CHATBOT_PHRASES):
        return False
    if "key takeaways" not in lower:
        return False
    kt_idx = lower.index("key takeaways")
    before = s[:kt_idx].strip()
    if len(before) < 100:
        return False
    after = s[kt_idx:]
    bullets = re.findall(r"^[-*\u2022]\s", after, re.MULTILINE)
    if len(bullets) < 2:
        return False
    return True


def validate_outline(text: str) -> bool:
    """Must be a numbered or bulleted list of 3+ items."""
    s = (text or "").strip()
    if not s:
        return False
    lower = s.lower()
    if any(phrase in lower for phrase in _CHATBOT_PHRASES):
        return False
    items = re.findall(r"^(?:\d+[.)]\s|[-*\u2022]\s)", s, re.MULTILINE)
    return len(items) >= 3


# ---------------------------------------------------------------------------
# Tier + transcript compaction
# ---------------------------------------------------------------------------


def _select_tier(char_count: int) -> PromptTier:
    if char_count < 3000:
        return PromptTier.SHORT
    if char_count < 15000:
        return PromptTier.MEDIUM
    return PromptTier.LONG


def _compact_transcript(text: str, tier: PromptTier) -> str:
    t = text.strip()
    if tier == PromptTier.SHORT:
        return t
    if tier == PromptTier.MEDIUM:
        return t[:15000]
    # LONG: head + tail
    if len(t) <= 16000:
        return t
    head = t[:12000].rstrip()
    tail = t[-3000:].lstrip()
    return f"{head}\n\n[... middle section omitted for brevity ...]\n\n{tail}"


def _adaptive_counts(duration_s: int | None) -> dict:
    dur = duration_s or 600
    if dur < 300:
        return {"sentence_count": 2, "bullet_count": 3, "outline_points": 3}
    if dur < 900:
        return {"sentence_count": 2, "bullet_count": 3, "outline_points": 4}
    if dur < 1800:
        return {"sentence_count": 3, "bullet_count": 4, "outline_points": 5}
    return {"sentence_count": 4, "bullet_count": 5, "outline_points": 7}


# ---------------------------------------------------------------------------
# Ollama REST API call
# ---------------------------------------------------------------------------

_OLLAMA_URL = "http://localhost:11434/api/generate"


def _call_ollama(prompt: str, model: str, timeout: int) -> str:
    resp = requests.post(
        _OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return (resp.json().get("response") or "").strip()


# ---------------------------------------------------------------------------
# Contract retry loop
# ---------------------------------------------------------------------------


def _call_with_contract(
    prompt: str,
    contract: OutputContract,
    model: str,
    timeout: int,
    max_retries: int,
) -> tuple[str, int]:
    """Retry up to (max_retries + 1) total attempts. Raises ContractViolationError on exhaustion."""
    last_output = ""
    for attempt in range(1, max_retries + 2):
        try:
            raw = _call_ollama(prompt, model, timeout)
        except Exception as e:
            log.warning("Ollama call failed (attempt %d/%d): %s", attempt, max_retries + 1, e)
            last_output = ""
            continue
        if contract.validate(raw):
            log.debug("LLM %s passed validation on attempt %d", contract.name, attempt)
            return (raw, attempt)
        log.warning(
            "LLM %s failed validation (attempt %d/%d): %.100s",
            contract.name, attempt, max_retries + 1, raw,
        )
        last_output = raw
    raise ContractViolationError(contract.name, last_output)


# ---------------------------------------------------------------------------
# Deterministic fallbacks
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if len(s.strip()) >= 20]


def _deterministic_fallback_opener(transcript: str) -> str:
    sentences = _split_sentences(transcript[:3000])
    for s in sentences:
        if len(s) >= 30 and not any(p in s.lower() for p in _CHATBOT_PHRASES):
            # Clean up filler
            s = re.sub(r"(?i)\b(um+|uh+|er+|ah+)\b", "", s).strip()
            s = re.sub(r"\s{2,}", " ", s)
            if s:
                return s
    return "This video covers a range of topics discussed by the creator."


def _deterministic_fallback_summary(transcript: str, duration_s: int | None) -> str:
    sentences = _split_sentences(transcript)
    count = 5 if (duration_s or 0) < 600 else 8
    body_sentences = sentences[:count]
    body = " ".join(body_sentences) if body_sentences else transcript[:300]
    takeaway_sentences = sentences[count:count + 3] or sentences[:3]
    if not takeaway_sentences:
        takeaway_sentences = [
            "Key ideas from this video.",
            "Watch for practical examples.",
            "Apply the concepts shown.",
        ]
    bullets = "\n".join(f"- {s}" for s in takeaway_sentences[:3])
    return f"{body}\n\nKey Takeaways\n{bullets}"


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def _load_preamble(prompts_dir: Path) -> str:
    p = prompts_dir / "system_preamble.md"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def _load_prompt(prompts_dir: Path, name: str) -> str:
    p = prompts_dir / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt file not found: {p}")
    return p.read_text(encoding="utf-8").strip()


def _build_prompt(preamble: str, template: str, **kwargs) -> str:
    body = template.format(**kwargs)
    if preamble:
        return f"{preamble}\n\n---\n\n{body}"
    return body


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_opener(
    transcript: str,
    video_title: str,
    duration_s: int | None,
    *,
    model: str,
    timeout: int,
    max_retries: int,
    prompts_dir: Path,
) -> LLMOutput:
    tier = _select_tier(len(transcript))
    counts = _adaptive_counts(duration_s)
    preamble = _load_preamble(prompts_dir)
    template = _load_prompt(prompts_dir, "opener.md")
    prompt = _build_prompt(
        preamble, template,
        video_title=video_title,
        transcript_head=transcript[:2000],
        sentence_count=counts["sentence_count"],
    )
    contract = OutputContract(name="opener", validate=validate_opener)
    try:
        text, attempts = _call_with_contract(prompt, contract, model, timeout, max_retries)
        return LLMOutput(text=text, tier=tier, attempts=attempts, used_fallback=False)
    except ContractViolationError:
        log.error("Opener contract exhausted -- using deterministic fallback")
        return LLMOutput(
            text=_deterministic_fallback_opener(transcript),
            tier=tier,
            attempts=max_retries + 1,
            used_fallback=True,
        )


def generate_summary(
    transcript: str,
    video_title: str,
    duration_s: int | None,
    *,
    model: str,
    timeout: int,
    max_retries: int,
    prompts_dir: Path,
) -> LLMOutput:
    tier = _select_tier(len(transcript))
    counts = _adaptive_counts(duration_s)
    compacted = _compact_transcript(transcript, tier)
    preamble = _load_preamble(prompts_dir)
    prompt_file = {
        PromptTier.SHORT: "summary_short.md",
        PromptTier.MEDIUM: "summary_medium.md",
        PromptTier.LONG: "summary_long.md",
    }[tier]
    template = _load_prompt(prompts_dir, prompt_file)
    prompt = _build_prompt(
        preamble, template,
        video_title=video_title,
        transcript=compacted,
        bullet_count=counts["bullet_count"],
    )
    contract = OutputContract(name="summary", validate=validate_summary)
    try:
        text, attempts = _call_with_contract(prompt, contract, model, timeout, max_retries)
        return LLMOutput(text=text, tier=tier, attempts=attempts, used_fallback=False)
    except ContractViolationError:
        log.error("Summary contract exhausted -- using deterministic fallback")
        return LLMOutput(
            text=_deterministic_fallback_summary(transcript, duration_s),
            tier=tier,
            attempts=max_retries + 1,
            used_fallback=True,
        )


def generate_outline(
    transcript: str,
    video_title: str,
    chapters: list | None,
    video_url: str,
    duration_s: int | None,
    *,
    model: str,
    timeout: int,
    max_retries: int,
    prompts_dir: Path,
) -> LLMOutput | None:
    """Returns None if transcript is too short for an outline to be useful."""
    if len(transcript) < 2000 and not chapters:
        return None
    tier = _select_tier(len(transcript))
    counts = _adaptive_counts(duration_s)
    compacted = _compact_transcript(transcript, tier)
    preamble = _load_preamble(prompts_dir)
    template = _load_prompt(prompts_dir, "outline.md")
    prompt = _build_prompt(
        preamble, template,
        video_title=video_title,
        transcript=compacted,
        outline_points=counts["outline_points"],
    )
    contract = OutputContract(name="outline", validate=validate_outline)
    try:
        text, attempts = _call_with_contract(prompt, contract, model, timeout, max_retries)
        return LLMOutput(text=text, tier=tier, attempts=attempts, used_fallback=False)
    except ContractViolationError:
        log.warning("Outline contract exhausted -- skipping outline section")
        return None
