from __future__ import annotations

import subprocess
import re


def summarize_with_ollama(*, transcript: str, model: str, prompt_template: str) -> str:
    prompt = prompt_template.format(transcript=_compact_transcript(transcript))
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
    Safety net for common LLM failure modes during beta:
    - Markdown headers leaking into the email (### ...)
    - Repeating the same section twice (often after "Key takeaways")
    - Adding "Conclusion" / extra recap blocks

    This is intentionally conservative: it won't try to be clever, just prevent
    the most obvious "double summary" feel.
    """
    s = (text or "").strip()
    if not s:
        return s

    # Remove markdown heading markers ("### Foo" -> "Foo")
    s = _MD_HEADER_RE.sub("", s).strip()
    # Remove simple bold markers (**Foo** -> Foo)
    s = _BOLD_MARKER_RE.sub(r"\1", s).strip()
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

    # Keep only the first "Key takeaways" section (case-insensitive).
    # If multiple occur, truncate to the first block + its bullets.
    kt = re.search(r"(?im)^\s*key takeaways\s*:?\s*$", s)
    if kt:
        before = s[: kt.start()].rstrip()
        after = s[kt.end() :].lstrip()

        # Capture up to 3 bullet lines; stop when we hit a blank line followed by non-bullet text.
        bullets: list[str] = []
        rest_lines: list[str] = []
        for line in after.splitlines():
            ln = line.rstrip()
            if ln.strip().startswith(("-", "*")):
                bullets.append(ln.strip())
                continue
            rest_lines.append(ln)
            # once we have bullets, and we hit a non-bullet, we stop collecting
            if bullets:
                break

        if bullets:
            # Normalize bullets to "- " and cap at 3
            norm = []
            for b in bullets[:3]:
                btxt = b.lstrip("*-").strip()
                if btxt:
                    norm.append(f"- {btxt}")
            bullets_block = "\n".join(norm)
            s = "\n\n".join([before, "Key takeaways", bullets_block]).strip()
        else:
            # If no bullets, keep original structure
            s = "\n\n".join([before, "Key takeaways", after]).strip()

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

