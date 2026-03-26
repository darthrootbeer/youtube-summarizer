from pathlib import Path
from unittest.mock import patch

import pytest

from youtube_summarizer.email_builder import (
    _render_opener_html,
    _render_outline_html,
    _render_summary_html,
    build_email,
)
from youtube_summarizer.fetcher import VideoMeta
from youtube_summarizer.llm import LLMOutput, PromptTier


def _make_video():
    return VideoMeta(
        video_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Test Video Title",
        published_at="2025-01-15T12:00:00Z",
        channel_name="Test Channel",
    )


def _make_opener():
    return LLMOutput(text="Machine learning transforms data into insights.", tier=PromptTier.SHORT, attempts=1, used_fallback=False)


def _make_summary():
    return LLMOutput(
        text=(
            "This video covers machine learning fundamentals including gradient descent, "
            "neural networks, and model training best practices. The speaker provides "
            "several practical demonstrations that make complex concepts accessible.\n\n"
            "Key Takeaways\n"
            "- Gradient descent requires careful learning rate tuning.\n"
            "- Batch normalization speeds up deep network training.\n"
            "- Regularization prevents overfitting on small datasets."
        ),
        tier=PromptTier.SHORT,
        attempts=1,
        used_fallback=False,
    )


def _make_outline():
    return LLMOutput(
        text="1. Introduction to ML\n2. Gradient descent\n3. Neural networks",
        tier=PromptTier.SHORT,
        attempts=1,
        used_fallback=False,
    )


def _template_dir():
    return Path(__file__).resolve().parent.parent / "youtube_summarizer" / "templates"


def test_build_email_returns_html_and_text():
    subject, html, text = build_email(
        channel_name="Test Channel",
        video=_make_video(),
        opener=_make_opener(),
        summary=_make_summary(),
        outline=_make_outline(),
        transcript_source="youtube_api",
        subject_prefix="[YT] ",
        template_dir=_template_dir(),
    )
    assert isinstance(html, str)
    assert isinstance(text, str)
    assert isinstance(subject, str)
    assert len(html) > 100


def test_build_email_html_contains_opener():
    subject, html, text = build_email(
        channel_name="Test Channel",
        video=_make_video(),
        opener=_make_opener(),
        summary=_make_summary(),
        outline=None,
        transcript_source="youtube_api",
        subject_prefix="[YT] ",
        template_dir=_template_dir(),
    )
    assert "Machine learning transforms data into insights" in html


def test_build_email_html_contains_channel_name():
    subject, html, text = build_email(
        channel_name="Test Channel",
        video=_make_video(),
        opener=_make_opener(),
        summary=_make_summary(),
        outline=None,
        transcript_source="youtube_api",
        subject_prefix="[YT] ",
        template_dir=_template_dir(),
    )
    assert "Test Channel" in html
    assert "Test Channel" in subject


def test_render_summary_html_formats_bullets_as_li():
    text = (
        "This is a summary about some important topic that covers many ideas clearly.\n\n"
        "Key Takeaways\n"
        "- First bullet point.\n"
        "- Second bullet point."
    )
    html = _render_summary_html(text)
    assert "<li" in str(html)
    assert "First bullet point" in str(html)


def test_render_summary_html_key_takeaways_uppercase():
    text = (
        "This is a summary about some important topic.\n\n"
        "Key Takeaways\n"
        "- First.\n"
        "- Second."
    )
    html = _render_summary_html(text)
    assert "KEY TAKEAWAYS" in str(html)


def test_render_outline_html_formats_as_ol():
    text = "1. First topic\n2. Second topic\n3. Third topic"
    html = _render_outline_html(text)
    assert "<ol" in str(html)
    assert "<li" in str(html)
    assert "First topic" in str(html)
