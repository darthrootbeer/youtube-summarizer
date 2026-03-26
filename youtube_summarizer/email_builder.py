from __future__ import annotations

import re
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from youtube_summarizer.fetcher import VideoMeta
from youtube_summarizer.llm import LLMOutput


def build_email(
    channel_name: str,
    video: VideoMeta,
    opener: LLMOutput,
    summary: LLMOutput,
    outline: LLMOutput | None,
    transcript_source: str,
    subject_prefix: str,
    template_dir: Path,
) -> tuple[str, str, str]:
    """Returns (subject, html, plaintext)."""
    subject = f"{subject_prefix}{channel_name}: {video.title}"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("email.html.j2")

    opener_html = _render_opener_html(opener.text)
    summary_html = _render_summary_html(summary.text)
    outline_html = _render_outline_html(outline.text) if outline else Markup("")

    # Build sections list matching the v1 template structure
    sections = []
    sections.append({
        "key": "opener",
        "label": None,
        "style": "opener",
        "text": opener.text,
        "html": opener_html,
    })
    sections.append({
        "key": "summary",
        "label": "Summary",
        "style": "body",
        "text": summary.text,
        "html": summary_html,
    })
    if outline and outline.text:
        sections.append({
            "key": "outline",
            "label": "Outline",
            "style": "body",
            "text": outline.text,
            "html": outline_html,
        })

    published_at_display = _fmt_published_at(video.published_at)

    # Build fallback badge info
    fallback_notes = []
    if opener.used_fallback:
        fallback_notes.append("opener")
    if summary.used_fallback:
        fallback_notes.append("summary")

    beta_stats = {
        "video_id": video.video_id,
        "summary_id": video.video_id,
        "transcript_source": transcript_source,
        "ollama_model": "v2",
        "enabled_prompts": "opener, summary" + (", outline" if outline else ""),
        "prompt_tier": summary.tier.value,
        "prompt_count": 2 + (1 if outline else 0),
        "per_prompt_summarize_s": "n/a",
        "transcript_chars": "n/a",
        "summary_chars": len(summary.text),
        "mode": "summarize",
        "rss_fetch_s": "n/a",
        "media_size_mb": "n/a",
        "download_media_s": "n/a",
        "video_duration_s": None,
        "transcribe_s": "n/a",
        "summarize_s": "n/a",
        "avg_cpu_pct": "n/a",
        "has_description": False,
        "chapters_count": 0,
        "email_render_s": "n/a",
        "email_send_s": "n/a",
        "total_before_send_s": "n/a",
        "total_to_send_s": "n/a",
        "total_processing_s": "n/a",
        "qa_notes": "; ".join(f"fallback: {n}" for n in fallback_notes) if fallback_notes else "",
    }

    html = template.render(
        subject=subject,
        source_label="Subscription",
        source_name=channel_name,
        video_title=video.title,
        video_url=video.url,
        thumbnail_url=f"https://img.youtube.com/vi/{video.video_id}/maxresdefault.jpg",
        sections=sections,
        published_at=video.published_at,
        published_at_display=published_at_display,
        video_duration_display=None,
        beta_stats=beta_stats,
    )

    text = _plaintext(opener.text, summary.text, outline.text if outline else None)

    return (subject, html, text)


def _render_opener_html(text: str) -> Markup:
    s = (text or "").strip()
    if not s:
        return Markup("")
    return Markup(escape(s))


def _render_summary_html(text: str) -> Markup:
    s = (text or "").strip()
    if not s:
        return Markup("")

    lines = [ln.rstrip() for ln in s.splitlines()]
    html_parts: list[str] = []
    in_list = False
    para_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal para_buf
        joined = " ".join(x.strip() for x in para_buf if x.strip()).strip()
        para_buf = []
        if joined:
            html_parts.append(f'<p style="margin:0 0 12px 0;">{_apply_inline(joined)}</p>')

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        low = line.lower().strip(":")
        if low in ("key takeaways", "key takeaways:"):
            flush_paragraph()
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(
                '<div style="margin:14px 0 8px 0;font-size:11px;letter-spacing:.08em;'
                'text-transform:uppercase;color:#6b6f85;font-weight:600;">KEY TAKEAWAYS</div>'
            )
            continue

        is_bullet = line.startswith("- ") or line.startswith("* ")
        if is_bullet:
            flush_paragraph()
            if not in_list:
                html_parts.append('<ul style="margin:0 0 12px 18px;padding:0;">')
                in_list = True
            html_parts.append(f'<li style="margin:0 0 7px 0;">{_apply_inline(line[2:].strip())}</li>')
            continue

        if in_list:
            html_parts.append("</ul>")
            in_list = False

        para_buf.append(line)

    flush_paragraph()
    if in_list:
        html_parts.append("</ul>")

    return Markup("\n".join(html_parts))


def _render_outline_html(text: str) -> Markup:
    s = (text or "").strip()
    if not s:
        return Markup("")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    clean_lines = [re.sub(r"^[-*\u2022]\s*|^\d+[.)]\s*", "", ln).strip() for ln in lines]
    items = "".join(
        f'<li style="margin:0 0 8px 0;color:#1e2138;">{escape(ln)}</li>'
        for ln in clean_lines if ln
    )
    return Markup(f'<ol style="margin:0;padding-left:22px;">{items}</ol>')


def _apply_inline(text: str) -> str:
    """HTML-escape then apply **bold** markers."""
    escaped = str(escape(text))
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)


def _plaintext(opener: str, summary: str, outline: str | None) -> str:
    parts = [opener, "", summary]
    if outline:
        parts.extend(["", "---", "", outline])
    return "\n".join(parts)


def _fmt_published_at(published_at: str) -> str | None:
    if not published_at:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published_at)
        return dt.strftime("%b %d, %Y")
    except Exception:
        pass
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return published_at[:10] if len(published_at) >= 10 else None
