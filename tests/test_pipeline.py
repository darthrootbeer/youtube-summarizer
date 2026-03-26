"""Tests for the youtube-summarizer pipeline.

Focuses on: cleanup_summary chatbot-confusion guard, LLM fallback behavior,
opener sentence count, HTML formatters, and prompt config loading.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from youtube_summarizer.summarizer import cleanup_summary
from youtube_summarizer.run import (
    _run_llm,
    _opener_sentence_count,
    _format_opener_html,
    _format_summary_html,
    _format_outline_html,
)
from youtube_summarizer.config import _key_from_filename, load_process_prompts


# ---------------------------------------------------------------------------
# 1. cleanup_summary — chatbot confusion guard
# ---------------------------------------------------------------------------

class TestCleanupSummaryChatbotConfusion:
    """Tests for the chatbot confusion guard in cleanup_summary."""

    def test_it_looks_like_youve_shared_extensive(self):
        """'It looks like you've shared an extensive transcript...' should be discarded."""
        text = "It looks like you've shared an extensive transcript from a tech conference."
        assert cleanup_summary(text) == ""

    def test_it_looks_like_you_have_shared_long(self):
        """'It looks like you have shared a long video...' should be discarded."""
        text = "It looks like you have shared a long video about machine learning."
        assert cleanup_summary(text) == ""

    def test_it_seems_like_youve_provided_detailed(self):
        """'It seems like you've provided a detailed transcript...' should be discarded."""
        text = "It seems like you've provided a detailed transcript from the keynote."
        assert cleanup_summary(text) == ""

    def test_it_seems_like_you_have_provided_long_transcript(self):
        """'It seems like you have provided a long transcript about AI tools.' should be discarded."""
        text = "It seems like you have provided a long transcript about AI tools."
        assert cleanup_summary(text) == ""

    def test_thank_you_for_sharing(self):
        """'Thank you for sharing this content.' should be discarded."""
        text = "Thank you for sharing this content."
        assert cleanup_summary(text) == ""

    def test_youve_shared_extensive(self):
        """'You've shared an extensive transcript from a live stream...' should be discarded."""
        text = "You've shared an extensive transcript from a live stream about AI."
        assert cleanup_summary(text) == ""

    def test_here_are_some_key_points_from_transcript(self):
        """'Here are some key points from your transcript...' should be discarded."""
        text = "Here are some key points from your transcript on productivity."
        assert cleanup_summary(text) == ""

    def test_here_are_key_highlights_from_video(self):
        """'Here are highlights from the video content.' should be discarded."""
        text = "Here are highlights from the video content."
        assert cleanup_summary(text) == ""

    def test_it_sounds_like_youre_wrapping_up(self):
        """'It sounds like you're wrapping up a live stream...' should be discarded."""
        text = "It sounds like you're wrapping up a live stream and providing updates."
        assert cleanup_summary(text) == ""

    def test_it_sounds_like_youre_describing(self):
        """'It sounds like you're describing an engaging live stream...' should be discarded."""
        text = "It sounds like you're describing an engaging and dynamic live stream session."
        assert cleanup_summary(text) == ""

    def test_it_seems_like_youve_shared_excerpt(self):
        """'It seems like you've shared an excerpt from a live stream...' should be discarded."""
        text = "It seems like you've shared an excerpt from a live stream or broadcast."
        assert cleanup_summary(text) == ""

    def test_feel_free_to_reach_out(self):
        """'Feel free to reach out...' sign-off should be discarded."""
        text = "Feel free to reach out for further assistance or if you need help."
        assert cleanup_summary(text) == ""

    def test_good_opener_single_sentence_passes_through(self):
        """A normal topic sentence should pass through unchanged."""
        text = "AI tools are evolving rapidly."
        result = cleanup_summary(text)
        assert result == "AI tools are evolving rapidly."

    def test_good_opener_multi_sentence_passes_through(self):
        """A multi-sentence good opener should pass through unchanged."""
        text = (
            "The speaker discusses the future of renewable energy. "
            "She argues that solar costs will drop below grid parity by 2030."
        )
        result = cleanup_summary(text)
        assert result == text


# ---------------------------------------------------------------------------
# 1b. cleanup_summary — other safety guards
# ---------------------------------------------------------------------------

class TestCleanupSummaryOtherGuards:
    """Tests for CJK, markdown header, control token, bracket signoff, section cutoffs."""

    def test_cjk_predominantly_chinese_returns_empty(self):
        """Predominantly CJK text should be discarded (model responded in wrong language)."""
        text = "这个视频讨论了人工智能的未来发展趋势，包括机器学习和深度学习的应用场景。"
        assert cleanup_summary(text) == ""

    def test_markdown_header_stripped(self):
        """'### Summary\\nContent here' strips the ### marker; header word remains as a line."""
        text = "### Summary\nContent here"
        result = cleanup_summary(text)
        # The regex strips '### ' but keeps the header word — result is 'Summary\nContent here'
        assert "###" not in result
        assert "Summary" in result
        assert "Content here" in result

    def test_control_token_stripped(self):
        """Text with <|im_end|> should have the token removed."""
        text = "Great insights on AI.<|im_end|>"
        result = cleanup_summary(text)
        assert "<|im_end|>" not in result
        assert "Great insights on AI." in result

    def test_bracket_signoff_stripped(self):
        """Text ending with '[End Brief]' should have that stripped."""
        text = "Key insights here.\n\n[End Brief]"
        result = cleanup_summary(text)
        assert "[End Brief]" not in result
        assert "Key insights here." in result

    def test_key_takeaways_section_kept_with_walkaway(self):
        """Summary with 'Key takeaways' header + bullets should be kept; walk-away preserved."""
        text = (
            "This talk covered LLM deployment strategies.\n\n"
            "Key takeaways\n\n"
            "- Use quantized models for edge devices\n"
            "- Batch inference improves throughput\n\n"
            "Overall, prioritize latency over accuracy for real-time apps."
        )
        result = cleanup_summary(text)
        assert "Key takeaways" in result
        assert "quantized models" in result
        assert "prioritize latency" in result

    def test_key_points_section_dropped(self):
        """Everything from a standalone 'Key Points' line onward should be dropped."""
        text = "Good intro content.\n\nKey Points\n\n- Point one\n- Point two"
        result = cleanup_summary(text)
        assert "Good intro content." in result
        assert "Point one" not in result

    def test_conclusion_section_dropped(self):
        """Everything from a standalone 'Conclusion' line onward should be dropped."""
        text = "Main content here.\n\nConclusion\n\nFinal thoughts that should be dropped."
        result = cleanup_summary(text)
        assert "Main content here." in result
        assert "Final thoughts" not in result

    def test_empty_string_returns_empty(self):
        """Empty string input should return empty string."""
        assert cleanup_summary("") == ""

    def test_none_input_returns_empty(self):
        """None input should return empty string."""
        assert cleanup_summary(None) == ""

    def test_whitespace_only_returns_empty(self):
        """Whitespace-only input should return empty string."""
        assert cleanup_summary("   \n\n  ") == ""


# ---------------------------------------------------------------------------
# 2. _run_llm — LLM fallback behavior
# ---------------------------------------------------------------------------

class TestRunLLM:
    """Tests for _run_llm fallback behavior."""

    TRANSCRIPT = "This is a test transcript about machine learning and neural networks."
    PROMPT = "Summarize: {transcript}"

    def test_normal_path_returns_llm_output(self):
        """When LLM returns good text, it should be returned as-is."""
        with patch("youtube_summarizer.run.summarize_with_ollama", return_value="Great summary.") as mock_llm:
            result = _run_llm(self.TRANSCRIPT, "llama3", self.PROMPT)
        assert result == "Great summary."
        mock_llm.assert_called_once()

    def test_llm_empty_string_retries_then_falls_back(self):
        """When LLM returns empty string both attempts, should fall back to transcript snippet."""
        with patch("youtube_summarizer.run.summarize_with_ollama", return_value="") as mock_llm:
            result = _run_llm(self.TRANSCRIPT, "llama3", self.PROMPT)
        assert mock_llm.call_count == 2
        assert result == self.TRANSCRIPT.strip()

    def test_llm_whitespace_only_retries_then_falls_back(self):
        """When LLM returns only whitespace both attempts, should fall back to transcript snippet."""
        with patch("youtube_summarizer.run.summarize_with_ollama", return_value="   ") as mock_llm:
            result = _run_llm(self.TRANSCRIPT, "llama3", self.PROMPT)
        assert mock_llm.call_count == 2
        assert result == self.TRANSCRIPT.strip()

    def test_llm_succeeds_on_retry(self):
        """When first attempt returns empty but second returns valid text, return the good output."""
        responses = ["", "Good summary on retry."]
        with patch("youtube_summarizer.run.summarize_with_ollama", side_effect=responses) as mock_llm:
            result = _run_llm(self.TRANSCRIPT, "llama3", self.PROMPT)
        assert mock_llm.call_count == 2
        assert result == "Good summary on retry."

    def test_llm_exception_retries_then_falls_back(self):
        """When LLM raises exceptions on both attempts, should fall back to transcript snippet."""
        with patch("youtube_summarizer.run.summarize_with_ollama", side_effect=RuntimeError("connection refused")) as mock_llm:
            result = _run_llm(self.TRANSCRIPT, "llama3", self.PROMPT)
        assert mock_llm.call_count == 2
        assert result == self.TRANSCRIPT.strip()

    def test_no_ollama_model_falls_back_immediately(self):
        """When ollama_model is None, no LLM call should be made; falls back to transcript."""
        with patch("youtube_summarizer.run.summarize_with_ollama") as mock_llm:
            result = _run_llm(self.TRANSCRIPT, None, self.PROMPT)
        mock_llm.assert_not_called()
        assert result == self.TRANSCRIPT.strip()

    def test_long_transcript_fallback_truncated_to_500(self):
        """Fallback for a long transcript should be capped at 500 chars with ellipsis."""
        long_transcript = "word " * 200  # well over 500 chars
        with patch("youtube_summarizer.run.summarize_with_ollama", return_value=""):
            result = _run_llm(long_transcript, "llama3", self.PROMPT)
        assert result.endswith("…")
        # The result should be no longer than 501 chars (500 + ellipsis)
        assert len(result) <= 502


# ---------------------------------------------------------------------------
# 3. _opener_sentence_count — duration mapping
# ---------------------------------------------------------------------------

class TestOpenerSentenceCount:
    """Tests for _opener_sentence_count duration-to-sentence-count mapping."""

    def test_short_video_under_5min(self):
        """Videos under 300s (< 5 min) should get 1 opener sentence."""
        assert _opener_sentence_count(299, 5000) == 1

    def test_short_video_exactly_0(self):
        """Zero duration should get 1 opener sentence."""
        assert _opener_sentence_count(0, 5000) == 1

    def test_medium_video_5_to_15_min(self):
        """Videos 300–899s (5–15 min) should get 2 opener sentences."""
        assert _opener_sentence_count(300, 10000) == 2
        assert _opener_sentence_count(899, 10000) == 2

    def test_longer_video_15_to_30_min(self):
        """Videos 900–1799s (15–30 min) should get 3 opener sentences."""
        assert _opener_sentence_count(900, 15000) == 3
        assert _opener_sentence_count(1799, 15000) == 3

    def test_long_video_30_plus_min(self):
        """Videos ≥ 1800s (30+ min) should get 4 opener sentences."""
        assert _opener_sentence_count(1800, 20000) == 4
        assert _opener_sentence_count(3600, 20000) == 4

    def test_none_duration_short_transcript(self):
        """None duration with short transcript (< 8000 chars) should get 1."""
        assert _opener_sentence_count(None, 7999) == 1

    def test_none_duration_medium_transcript(self):
        """None duration with medium transcript (8000–21999 chars) should get 2."""
        assert _opener_sentence_count(None, 8000) == 2
        assert _opener_sentence_count(None, 21999) == 2

    def test_none_duration_long_transcript(self):
        """None duration with long transcript (≥ 22000 chars) should get 3."""
        assert _opener_sentence_count(None, 22000) == 3
        assert _opener_sentence_count(None, 50000) == 3


# ---------------------------------------------------------------------------
# 4. _format_opener_html — HTML escaping
# ---------------------------------------------------------------------------

class TestFormatOpenerHtml:
    """Tests for _format_opener_html."""

    def test_empty_string_returns_empty_markup(self):
        """Empty string should return empty Markup."""
        from markupsafe import Markup
        result = _format_opener_html("")
        assert result == Markup("")

    def test_normal_text_returned_escaped(self):
        """Normal text should be returned as escaped text (no wrapper tags)."""
        result = _format_opener_html("AI tools are evolving rapidly.")
        assert str(result) == "AI tools are evolving rapidly."

    def test_html_less_than_escaped(self):
        """'<' in text should be escaped to '&lt;'."""
        result = _format_opener_html("Score < 50 is failing.")
        assert "&lt;" in str(result)
        assert "<" not in str(result).replace("&lt;", "")

    def test_html_greater_than_escaped(self):
        """'>' in text should be escaped to '&gt;'."""
        result = _format_opener_html("Score > 90 is excellent.")
        assert "&gt;" in str(result)

    def test_html_ampersand_escaped(self):
        """'&' in text should be escaped to '&amp;'."""
        result = _format_opener_html("Pros & cons discussed.")
        assert "&amp;" in str(result)

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped."""
        result = _format_opener_html("  Hello world.  ")
        assert str(result) == "Hello world."


# ---------------------------------------------------------------------------
# 5. _format_summary_html — full HTML rendering
# ---------------------------------------------------------------------------

class TestFormatSummaryHtml:
    """Tests for _format_summary_html."""

    def test_empty_returns_empty_markup(self):
        """Empty string should return empty Markup."""
        from markupsafe import Markup
        result = _format_summary_html("")
        assert result == Markup("")

    def test_plain_paragraph_wrapped_in_p_tag(self):
        """A plain paragraph should be wrapped in a <p> tag."""
        result = _format_summary_html("This is a plain paragraph.")
        html = str(result)
        assert "<p" in html
        assert "This is a plain paragraph." in html

    def test_bullet_list_wrapped_in_ul_li_tags(self):
        """Bullet lines should produce <ul><li> structure."""
        text = "- First point\n- Second point\n- Third point"
        html = str(_format_summary_html(text))
        assert "<ul" in html
        assert "<li" in html
        assert "First point" in html
        assert "Second point" in html

    def test_star_bullets_also_wrapped(self):
        """Star-prefixed bullets should also produce <ul><li> structure."""
        text = "* Alpha\n* Beta"
        html = str(_format_summary_html(text))
        assert "<ul" in html
        assert "<li" in html

    def test_key_takeaways_renders_as_uppercase_div(self):
        """'Key takeaways' header line should render as an uppercase styled div."""
        text = "Key takeaways\n\n- Point one\n- Point two"
        html = str(_format_summary_html(text))
        assert "text-transform:uppercase" in html
        assert "Key takeaways" in html

    def test_bold_markers_converted_to_strong(self):
        """**bold** markers should be converted to <strong> tags."""
        text = "This is **very important** content."
        html = str(_format_summary_html(text))
        assert "<strong>very important</strong>" in html

    def test_mixed_content_correct_structure(self):
        """Mixed paragraphs, bullets, key takeaways, and walk-away should produce correct HTML."""
        text = (
            "Opening paragraph with context.\n\n"
            "Key takeaways\n\n"
            "- Use quantized models\n"
            "- Batch inference helps\n\n"
            "Final walk-away sentence."
        )
        html = str(_format_summary_html(text))
        assert "<p" in html           # paragraph rendered
        assert "<ul" in html          # bullet list rendered
        assert "text-transform:uppercase" in html   # key takeaways header
        assert "Opening paragraph" in html
        assert "quantized models" in html
        assert "Final walk-away" in html


# ---------------------------------------------------------------------------
# 6. _format_outline_html — ordered list rendering
# ---------------------------------------------------------------------------

class TestFormatOutlineHtml:
    """Tests for _format_outline_html."""

    def test_empty_returns_empty_markup(self):
        """Empty string should return empty Markup."""
        from markupsafe import Markup
        result = _format_outline_html("")
        assert result == Markup("")

    def test_bullet_lines_become_ol_li(self):
        """Lines with leading dashes should be stripped and wrapped in <ol><li>."""
        text = "- First topic\n- Second topic\n- Third topic"
        html = str(_format_outline_html(text))
        assert "<ol" in html
        assert "<li" in html
        assert "First topic" in html
        assert "Second topic" in html
        # Dashes should be stripped
        assert "- First" not in html

    def test_numbered_lines_become_ol_li(self):
        """Lines with leading numbers should be stripped and wrapped in <ol><li>."""
        text = "1. Introduction\n2. Main argument\n3. Conclusion"
        html = str(_format_outline_html(text))
        assert "<ol" in html
        assert "<li" in html
        assert "Introduction" in html
        # Numbers stripped
        assert "1." not in html

    def test_plain_lines_become_ol_li(self):
        """Plain lines with no prefix should also be wrapped in <ol><li>."""
        text = "Topic one\nTopic two"
        html = str(_format_outline_html(text))
        assert "<ol" in html
        assert "<li" in html

    def test_html_chars_escaped_in_outline(self):
        """HTML characters in outline items should be escaped."""
        text = "Score < 50 & > 10"
        html = str(_format_outline_html(text))
        assert "&lt;" in html
        assert "&amp;" in html


# ---------------------------------------------------------------------------
# 7. config — prompt loading
# ---------------------------------------------------------------------------

class TestConfigPromptLoading:
    """Tests for _key_from_filename and load_process_prompts."""

    def test_key_from_filename_default(self):
        """'01_default.md' should yield key 'default'."""
        assert _key_from_filename("01_default.md") == "default"

    def test_key_from_filename_glossary(self):
        """'08_glossary.md' should yield key 'glossary'."""
        assert _key_from_filename("08_glossary.md") == "glossary"

    def test_key_from_filename_no_number_prefix(self):
        """A filename without a number prefix should still yield correct key."""
        assert _key_from_filename("summary.md") == "summary"

    def test_key_from_filename_multidigit_prefix(self):
        """A two-digit prefix like '10_quote_bank.md' should yield 'quote_bank'."""
        assert _key_from_filename("10_quote_bank.md") == "quote_bank"

    def test_load_process_prompts_returns_list(self):
        """load_process_prompts() should return a non-empty list of ProcessPrompt."""
        prompts = load_process_prompts()
        assert isinstance(prompts, list)
        assert len(prompts) > 0

    def test_load_process_prompts_has_enabled_prompts(self):
        """load_process_prompts() should have at least one enabled prompt."""
        prompts = load_process_prompts()
        enabled = [p for p in prompts if p.enabled]
        assert len(enabled) > 0

    def test_glossary_prompt_is_disabled(self):
        """The glossary prompt should have enabled=False."""
        prompts = load_process_prompts()
        glossary = next((p for p in prompts if p.key == "glossary"), None)
        assert glossary is not None, "glossary prompt not found"
        assert glossary.enabled is False
