from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from youtube_summarizer.llm import (
    ContractViolationError,
    LLMOutput,
    OutputContract,
    PromptTier,
    _adaptive_counts,
    _call_with_contract,
    _compact_transcript,
    _deterministic_fallback_opener,
    _deterministic_fallback_summary,
    _select_tier,
    generate_opener,
    generate_summary,
    validate_opener,
    validate_outline,
    validate_summary,
)


# ---------------------------------------------------------------------------
# Validators: opener
# ---------------------------------------------------------------------------

def test_validate_opener_valid():
    assert validate_opener("Gradient descent converges faster with adaptive learning rates.") is True


def test_validate_opener_rejects_chatbot():
    assert validate_opener("It looks like this is a video about machine learning.") is False


def test_validate_opener_rejects_headers():
    assert validate_opener("# Title\nSome content here.") is False


def test_validate_opener_rejects_numbered_list():
    assert validate_opener("1. First point about ML.\n2. Second point.") is False


def test_validate_opener_rejects_bullets():
    assert validate_opener("- Point one about deep learning.\n- Point two.") is False


def test_validate_opener_rejects_too_long():
    assert validate_opener("A" * 501) is False


def test_validate_opener_rejects_empty():
    assert validate_opener("") is False
    assert validate_opener(None) is False


# ---------------------------------------------------------------------------
# Validators: summary
# ---------------------------------------------------------------------------

def test_validate_summary_valid():
    text = (
        "This video explores machine learning fundamentals. It covers gradient descent, "
        "neural network architectures, and practical training tips. The speaker demonstrates "
        "several key concepts with code examples that illustrate the principles clearly.\n\n"
        "Key Takeaways\n"
        "- Gradient descent requires careful learning rate selection for stable convergence.\n"
        "- Neural networks benefit from batch normalization in deep architectures.\n"
        "- Regular validation prevents overfitting on small datasets."
    )
    assert validate_summary(text) is True


def test_validate_summary_rejects_no_takeaways():
    text = "This is a summary without any key takeaways section. " * 10
    assert validate_summary(text) is False


def test_validate_summary_rejects_too_few_bullets():
    text = (
        "This video explores machine learning fundamentals extensively and in great depth. "
        "The content is rich with examples and demonstrations of key concepts.\n\n"
        "Key Takeaways\n"
        "- Only one bullet here."
    )
    assert validate_summary(text) is False


def test_validate_summary_rejects_no_prose():
    text = "Short.\n\nKey Takeaways\n- Bullet 1.\n- Bullet 2.\n- Bullet 3."
    assert validate_summary(text) is False  # body before KT is too short


def test_validate_summary_rejects_chatbot():
    text = (
        "It looks like this is a comprehensive overview of machine learning concepts. "
        "The speaker covers many important topics in this educational content.\n\n"
        "Key Takeaways\n"
        "- Point one.\n- Point two.\n- Point three."
    )
    assert validate_summary(text) is False


# ---------------------------------------------------------------------------
# Validators: outline
# ---------------------------------------------------------------------------

def test_validate_outline_valid():
    text = "1. Introduction to machine learning\n2. Gradient descent explained\n3. Neural network basics"
    assert validate_outline(text) is True


def test_validate_outline_rejects_too_few():
    text = "1. Only one item\n2. And two"
    assert validate_outline(text) is False


def test_validate_outline_rejects_chatbot():
    text = "It looks like this covers:\n1. Topic one\n2. Topic two\n3. Topic three"
    assert validate_outline(text) is False


# ---------------------------------------------------------------------------
# Tier + compaction
# ---------------------------------------------------------------------------

def test_select_tier_short():
    assert _select_tier(2999) == PromptTier.SHORT


def test_select_tier_medium():
    assert _select_tier(5000) == PromptTier.MEDIUM


def test_select_tier_long():
    assert _select_tier(20000) == PromptTier.LONG


def test_compact_transcript_short_unchanged():
    text = "Short transcript."
    assert _compact_transcript(text, PromptTier.SHORT) == text.strip()


def test_compact_transcript_long_truncated():
    text = "A" * 20000
    result = _compact_transcript(text, PromptTier.LONG)
    assert "middle section omitted" in result
    assert len(result) < 20000


# ---------------------------------------------------------------------------
# Retry + fallback
# ---------------------------------------------------------------------------

def test_call_with_contract_succeeds_first_try():
    contract = OutputContract(name="test", validate=lambda x: True)
    with patch("youtube_summarizer.llm._call_ollama", return_value="good output"):
        text, attempts = _call_with_contract("prompt", contract, "model", 300, 2)
    assert text == "good output"
    assert attempts == 1


def test_call_with_contract_retries():
    call_count = [0]
    def mock_ollama(prompt, model, timeout):
        call_count[0] += 1
        if call_count[0] == 1:
            return "bad"
        return "good"

    contract = OutputContract(name="test", validate=lambda x: x == "good")
    with patch("youtube_summarizer.llm._call_ollama", side_effect=mock_ollama):
        text, attempts = _call_with_contract("prompt", contract, "model", 300, 2)
    assert text == "good"
    assert attempts == 2


def test_call_with_contract_exhausted():
    contract = OutputContract(name="test", validate=lambda x: False)
    with patch("youtube_summarizer.llm._call_ollama", return_value="always bad"):
        with pytest.raises(ContractViolationError):
            _call_with_contract("prompt", contract, "model", 300, 2)


def test_generate_opener_uses_fallback_on_exhaustion(tmp_path):
    # Create prompt files
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system_preamble.md").write_text("You are an analyst.")
    (prompts_dir / "opener.md").write_text("Write {sentence_count} sentence(s).\n\nVideo title: {video_title}\n\nTranscript:\n\"\"\"\n{transcript_head}\n\"\"\"")

    transcript = "Machine learning models learn patterns from data effectively. This enables powerful prediction capabilities across domains."
    with patch("youtube_summarizer.llm._call_ollama", return_value="It looks like you've shared a transcript."):
        result = generate_opener(
            transcript, "Test Video", 600,
            model="test", timeout=60, max_retries=1, prompts_dir=prompts_dir,
        )
    assert result.used_fallback is True
    assert isinstance(result, LLMOutput)


def test_generate_summary_uses_fallback_on_exhaustion(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system_preamble.md").write_text("You are an analyst.")
    (prompts_dir / "summary_short.md").write_text("Summarize.\n\nVideo title: {video_title}\n\nTranscript:\n\"\"\"\n{transcript}\n\"\"\"")

    transcript = "Short transcript about testing."
    with patch("youtube_summarizer.llm._call_ollama", return_value="It looks like you've shared something."):
        result = generate_summary(
            transcript, "Test Video", 200,
            model="test", timeout=60, max_retries=1, prompts_dir=prompts_dir,
        )
    assert result.used_fallback is True
    assert "Key Takeaways" in result.text


def test_deterministic_fallback_opener_no_chatbot_phrases():
    transcript = "Machine learning models learn patterns from data effectively. This enables powerful prediction capabilities across many different domains."
    result = _deterministic_fallback_opener(transcript)
    lower = result.lower()
    assert "it looks like" not in lower
    assert "you've shared" not in lower


def test_deterministic_fallback_summary_has_key_takeaways():
    transcript = "Machine learning models learn from data by finding patterns. " * 20
    result = _deterministic_fallback_summary(transcript, 600)
    assert "Key Takeaways" in result


def test_deterministic_fallback_summary_has_bullets():
    transcript = "Machine learning models learn from data by finding patterns. Neural networks use backpropagation for training. Deep learning requires large datasets for best results. Transfer learning reduces the need for massive datasets. Regularization prevents overfitting in complex models. Batch normalization speeds up training convergence. Attention mechanisms improve sequence modeling tasks. Transformers revolutionized natural language processing."
    result = _deterministic_fallback_summary(transcript, 300)
    bullet_count = result.count("\n- ")
    assert bullet_count >= 2
