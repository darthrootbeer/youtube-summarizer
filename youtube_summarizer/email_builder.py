from __future__ import annotations

import re
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

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
    duration_s: int | None = None,
    summary_id: str | None = None,
) -> tuple[str, str, str]:
    """Returns (subject, html, plaintext)."""
    subject = f"[YT] {video.title}"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("email.html.j2")

    is_short_video = duration_s is not None and duration_s <= 180

    opener_html = _render_opener_html(opener.text)

    # Build sections list matching the v1 template structure
    sections = []
    sections.append({
        "key": "opener",
        "label": None,
        "style": "opener",
        "text": opener.text,
        "html": opener_html,
    })

    if is_short_video:
        bullets_only = _extract_bullets(summary.text)
        if bullets_only:
            sections.append({
                "key": "takeaways",
                "label": None,
                "style": "body",
                "text": bullets_only,
                "html": _render_summary_html(bullets_only),
            })
    else:
        summary_html = _render_summary_html(summary.text)
        sections.append({
            "key": "summary",
            "label": "Summary",
            "style": "body",
            "text": summary.text,
            "html": summary_html,
        })
        if outline and outline.text:
            outline_html = _render_outline_html(outline.text)
            sections.append({
                "key": "outline",
                "label": "Outline",
                "style": "body",
                "text": outline.text,
                "html": outline_html,
            })

    published_at_display = _fmt_published_at(video.published_at)
    duration_display = _fmt_duration(duration_s)

    from datetime import datetime, timezone
    from youtube_summarizer import __version__

    meta = {
        "summary_id": summary_id or video.video_id,
        "version": __version__,
        "generated_at": datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d.%H%M%S"),
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
        video_duration_display=duration_display,
        meta=meta,
    )

    text = _plaintext(
        opener.text,
        summary.text if not is_short_video else None,
        outline.text if (outline and not is_short_video) else None,
    )

    return (subject, html, text)


def _extract_bullets(text: str) -> str:
    """Return only the Key Takeaways heading + bullets from a summary, stripping prose."""
    s = (text or "").strip()
    lower = s.lower()
    idx = lower.find("key takeaways")
    if idx == -1:
        # No heading — grab any bullet lines directly
        lines = [ln for ln in s.splitlines() if ln.strip().startswith("- ")]
        return "\n".join(lines)
    return s[idx:]


def _strip_markdown(text: str) -> str:
    """Remove markdown characters that should never appear in email output."""
    # Remove ATX headers (## Heading)
    s = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove === section labels (=== SECTION NAME ===)
    s = re.sub(r"^===.*?===\s*$", "", s, flags=re.MULTILINE)
    # Remove bold/italic markers
    s = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", s)
    s = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", s)
    return s


def _render_opener_html(text: str) -> Markup:
    s = _strip_markdown((text or "").strip())
    if not s:
        return Markup("")
    return Markup(escape(s))


def _render_summary_html(text: str) -> Markup:
    s = _strip_markdown((text or "").strip())
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
        numbered_match = re.match(r'^\d+[.)]\s+(.*)', line)
        if is_bullet or numbered_match:
            flush_paragraph()
            if not in_list:
                html_parts.append('<ul style="margin:0 0 12px 18px;padding:0;">')
                in_list = True
            bullet_text = numbered_match.group(1).strip() if numbered_match else line[2:].strip()
            html_parts.append(f'<li style="margin:0 0 7px 0;">{_apply_inline(bullet_text)}</li>')
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
    """HTML-escape text (markdown already stripped upstream)."""
    return str(escape(text))


def _plaintext(opener: str, summary: str | None, outline: str | None) -> str:
    parts = [opener]
    if summary:
        parts.extend(["", summary])
    if outline:
        parts.extend(["", "---", "", outline])
    return "\n".join(parts)


def _fmt_published_at(published_at: str) -> str | None:
    if not published_at:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published_at)
        return dt.strftime("%A %Y-%m-%d")
    except Exception:
        pass
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%A %Y-%m-%d")
    except Exception:
        return published_at[:10] if len(published_at) >= 10 else None


def _fmt_duration(duration_s: int | None) -> str | None:
    if not duration_s:
        return None
    m = max(1, -(-duration_s // 60))  # ceiling division, minimum 1m
    h = m // 60
    rem = m % 60
    if h:
        return f"[{h}h {rem}m]"
    return f"[{m}m]"
