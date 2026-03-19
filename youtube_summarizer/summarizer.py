from __future__ import annotations

import subprocess
import re


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


def cleanup_summary(text: str) -> str:
    """
    Safety net for common LLM failure modes:
    - Markdown headers leaking into the email
    - Drops extra sections after Key takeaways (but preserves the walk-away after bullets)
    """
    s = (text or "").strip()
    if not s:
        return s

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
