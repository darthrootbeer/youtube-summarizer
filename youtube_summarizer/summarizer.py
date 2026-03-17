from __future__ import annotations

import subprocess


SUMMARY_PROMPT = """You are a helpful assistant.

Explain or summarize this in 200 words or fewer using clear, plain English that is easy to skim before coffee.
Focus on the main ideas and why they matter, not technical details or implementation specifics.
Break the explanation into small paragraphs or mini-sections so it is quick to scan, covering the core concept,
the practical meaning or implications, and the real-world relevance.
End with exactly three concise bullet points labeled Key Takeaways that highlight the most important insights;
each takeaway should emphasize why the idea matters or what it helps you understand, not simply restate the content.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""


def summarize_with_ollama(*, transcript: str, model: str) -> str:
    prompt = SUMMARY_PROMPT.format(transcript=_compact_transcript(transcript))
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

