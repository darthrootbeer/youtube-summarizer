from __future__ import annotations

import subprocess


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
    return (res.stdout or "").strip()


def summarize_fallback(transcript: str) -> str:
    t = " ".join(transcript.split())
    if not t:
        return "No transcript available."
    snippet = t[:900]
    if len(t) > len(snippet):
        snippet += "…"
    return snippet


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

