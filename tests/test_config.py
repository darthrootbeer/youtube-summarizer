import os
import pytest
from pathlib import Path
from unittest.mock import patch

from youtube_summarizer.config import Channel, Settings, load_channels, load_dotenv, load_settings


def test_load_channels_valid(tmp_path):
    cfg = tmp_path / "channels.toml"
    cfg.write_text("""
[[subscriptions]]
name = "Test Channel"
url = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
""")
    channels = load_channels(cfg)
    assert len(channels) == 1
    assert channels[0].name == "Test Channel"
    assert channels[0].source_type == "subscription"


def test_load_channels_empty_list(tmp_path):
    cfg = tmp_path / "channels.toml"
    cfg.write_text("[subscriptions]\n")
    # tomllib parses [subscriptions] as a table, not an array. Need [[subscriptions]] for array.
    # An empty file with no subscriptions:
    cfg.write_text("")
    channels = load_channels(cfg)
    assert channels == []


def test_load_channels_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_channels(tmp_path / "nonexistent.toml")


def test_load_channels_missing_url(tmp_path):
    cfg = tmp_path / "channels.toml"
    cfg.write_text("""
[[subscriptions]]
name = "No URL Channel"
""")
    channels = load_channels(cfg)
    assert channels == []


def test_load_settings_all_vars():
    env = {
        "YTS_EMAIL_FROM": "test@example.com",
        "YTS_EMAIL_TO": "to@example.com",
        "YTS_GMAIL_APP_PASSWORD": "password123",
        "YTS_SUBJECT_PREFIX": "[Test] ",
        "YTS_DRY_RUN": "false",
        "YTS_OLLAMA_MODEL": "llama3.2",
        "YTS_OLLAMA_TIMEOUT": "600",
        "YTS_LLM_MAX_RETRIES": "3",
        "YTS_PARAKEET_MODEL": "mlx-community/parakeet-tdt-0.6b-v2",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = load_settings()
    assert settings.email_from == "test@example.com"
    assert settings.ollama_model == "llama3.2"
    assert settings.ollama_timeout == 600
    assert settings.max_retries == 3


def test_load_settings_defaults():
    env = {
        "YTS_EMAIL_FROM": "test@example.com",
        "YTS_EMAIL_TO": "to@example.com",
        "YTS_GMAIL_APP_PASSWORD": "password123",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = load_settings()
    assert settings.ollama_model == "qwen2.5:14b"
    assert settings.ollama_timeout == 300
    assert settings.max_retries == 2
    assert settings.subject_prefix == "[YT Summary]"


def test_load_settings_missing_required_raises():
    env = {"YTS_EMAIL_FROM": "", "YTS_EMAIL_TO": "", "YTS_GMAIL_APP_PASSWORD": "", "YTS_DRY_RUN": ""}
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(RuntimeError, match="Missing required"):
            load_settings()


def test_load_settings_dry_run_skips_email_validation():
    env = {
        "YTS_EMAIL_FROM": "",
        "YTS_EMAIL_TO": "",
        "YTS_GMAIL_APP_PASSWORD": "",
        "YTS_DRY_RUN": "1",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = load_settings()
    assert settings.dry_run is True


def test_load_dotenv(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('TEST_DOTENV_VAR="hello world"\n# comment\nANOTHER=plain\n')
    # Make sure the var isn't already set
    os.environ.pop("TEST_DOTENV_VAR", None)
    os.environ.pop("ANOTHER", None)
    load_dotenv(env_file)
    assert os.environ.get("TEST_DOTENV_VAR") == "hello world"
    assert os.environ.get("ANOTHER") == "plain"
    # Cleanup
    os.environ.pop("TEST_DOTENV_VAR", None)
    os.environ.pop("ANOTHER", None)
