import pytest
import sqlite3
from pathlib import Path
from youtube_summarizer.db import _migrate


@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


@pytest.fixture
def tmp_data_dir(tmp_path):
    (tmp_path / "summaries").mkdir()
    (tmp_path / "audio").mkdir()
    return tmp_path


@pytest.fixture
def short_transcript():
    return "Machine learning models learn from data by finding patterns. The key insight is that optimization algorithms like gradient descent find the minimum loss. Neural networks excel at tasks requiring feature extraction from raw inputs."


@pytest.fixture
def medium_transcript():
    return ("This is a video about Python programming best practices. " * 100).strip()


@pytest.fixture
def long_transcript():
    return ("Welcome to the live stream everyone. " * 600).strip()


@pytest.fixture
def chatbot_output():
    return "It looks like you've shared an extensive transcript from a live stream about AI tools."
