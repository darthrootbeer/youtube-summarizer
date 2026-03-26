from __future__ import annotations

import os
import subprocess
import re


def _ollama_env() -> dict[str, str]:
    """Ensure /opt/homebrew/bin is on PATH so ollama is found regardless of how the process was launched."""
    env = dict(os.environ)
    brew_bin = "/opt/homebrew/bin"
    path = env.get("PATH", "")
    if brew_bin not in path.split(os.pathsep):
        env["PATH"] = f"{brew_bin}{os.pathsep}{path}" if path else brew_bin
    return env


def summarize_with_ollama(
    *,
    transcript: str,
    model: str,
    prompt_template: str,
    compact: bool = True,
    video_context: str | None = None,
    **extra_vars,
) -> str:
    t = _compact_transcript(transcript) if compact else transcript
    prompt = prompt_template.format(transcript=t, **extra_vars)
    if video_context:
        prompt = f"VIDEO CONTEXT\n{video_context}\n---\n\n{prompt}"
    res = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        timeout=300,
        env=_ollama_env(),
    )
    return cleanup_summary((res.stdout or "").strip())


def summarize_fallback(transcript: str) -> str:
    t = " ".join(transcript.split())
    if not t:
        return "No transcript available."
    snippet = t[:900]
    if len(t) > len(snippet):
        snippet += "…"
    return cleanup_summary(snippet)


_MD_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+", flags=re.MULTILINE)
_BOLD_MARKER_RE = re.compile(r"\*\*(.*?)\*\*")
_BRACKET_SIGNOFF_RE = re.compile(r"(?im)^\s*\[[^\]]*\]\s*$")
_OLLAMA_CONTROL_TOKEN_RE = re.compile(r"<\|[^|>]{1,80}\|>")
# CJK Unified Ideographs + common CJK blocks
_CJK_RE = re.compile(r"[\u2E80-\u2FFF\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")


def cleanup_summary(text: str) -> str:
    """
    Safety net for common LLM failure modes:
    - Markdown headers leaking into the email
    - Drops extra sections after Key takeaways (but preserves the walk-away after bullets)
    """
    s = (text or "").strip()
    if not s:
        return s

    # Discard output that is predominantly CJK (model responded in Chinese/Japanese/Korean)
    non_ws = re.sub(r"\s", "", s)
    if non_ws and len(_CJK_RE.findall(s)) / len(non_ws) > 0.15:
        return ""

    # Remove markdown heading markers ("### Foo" -> "Foo")
    s = _MD_HEADER_RE.sub("", s).strip()
    # Remove simple bold markers (**Foo** -> Foo)  — but only outside glossary context
    # (glossary output legitimately uses **bold** for terms; handled separately)
    # Drop any standalone bracketed sign-offs like "[End Brief]"
    s = _BRACKET_SIGNOFF_RE.sub("", s).strip()
    # Drop common model/control tokens sometimes leaked by local models
    s = _OLLAMA_CONTROL_TOKEN_RE.sub("", s).strip()

    # If a "Key Points" section appears, drop everything from it onward.
    m = re.search(r"(?im)^\s*key points\s*:?\s*$", s)
    if m:
        s = s[: m.start()].rstrip()

    # If a "Conclusion" section appears, drop everything from it onward.
    m = re.search(r"(?im)^\s*conclusion\s*:?\s*$", s)
    if m:
        s = s[: m.start()].rstrip()

    # Keep only the first "Key takeaways" section — preserve walk-away after bullets.
    kt = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", s)
    if kt:
        before = s[: kt.start()].rstrip()
        after = s[kt.end() :].lstrip()

        bullets: list[str] = []
        rest_lines: list[str] = []
        collecting_rest = False
        for line in after.splitlines():
            ln = line.rstrip()
            stripped = ln.strip()
            if not collecting_rest and stripped.startswith(("-", "*")):
                bullets.append(stripped)
            else:
                if bullets:
                    collecting_rest = True
                if stripped:
                    rest_lines.append(stripped)

        if bullets:
            norm = []
            for b in bullets:  # no cap here — tier-specific trimming handles it
                btxt = b.lstrip("*-").strip()
                if btxt:
                    norm.append(f"- {btxt}")
            bullets_block = "\n".join(norm)
            parts = [before, "Key takeaways", bullets_block]
            wrap = " ".join(rest_lines).strip()
            if wrap:
                parts.append(wrap)
            s = "\n\n".join(parts).strip()

    return s.strip()


def _compact_transcript(transcript: str, *, head_chars: int = 14000, tail_chars: int = 2500) -> str:
    """
    Keeps summaries reliable by limiting context size.
    We keep the beginning (setup) and a small ending slice (conclusion/Q&A).
    """
    t = transcript.strip()
    if len(t) <= head_chars + tail_chars + 200:
        return t
    head = t[:head_chars].rstrip()
    tail = t[-tail_chars:].lstrip()
    return f"{head}\n\n[... transcript truncated ...]\n\n{tail}"
