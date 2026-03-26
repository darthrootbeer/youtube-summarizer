from pathlib import Path
from youtube_summarizer.artifacts import artifact_exists, write_artifact


def test_write_artifact_creates_file(tmp_data_dir):
    path = write_artifact(
        video_id="abc123",
        channel_name="Test Channel",
        video_title="Test Video",
        video_url="https://youtube.com/watch?v=abc123",
        opener_text="This is the opener.",
        summary_text="This is the summary.",
        outline_text="1. First point",
        transcript_source="youtube_api",
        data_dir=tmp_data_dir,
    )
    assert path.exists()
    assert path.name == "abc123.txt"


def test_write_artifact_content(tmp_data_dir):
    write_artifact(
        video_id="abc123",
        channel_name="Test Channel",
        video_title="Test Video",
        video_url="https://youtube.com/watch?v=abc123",
        opener_text="This is the opener.",
        summary_text="This is the summary.",
        outline_text="1. First\n2. Second",
        transcript_source="parakeet_mlx",
        data_dir=tmp_data_dir,
    )
    content = (tmp_data_dir / "summaries" / "abc123.txt").read_text()
    assert "video_id: abc123" in content
    assert "OPENER" in content
    assert "SUMMARY" in content
    assert "OUTLINE" in content
    assert "parakeet_mlx" in content


def test_artifact_exists(tmp_data_dir):
    assert artifact_exists("abc123", tmp_data_dir) is False
    write_artifact(
        video_id="abc123",
        channel_name="Ch",
        video_title="T",
        video_url="https://example.com",
        opener_text="o",
        summary_text="s",
        outline_text=None,
        transcript_source="youtube_api",
        data_dir=tmp_data_dir,
    )
    assert artifact_exists("abc123", tmp_data_dir) is True


def test_write_artifact_overwrites(tmp_data_dir):
    write_artifact(
        video_id="abc123",
        channel_name="Ch",
        video_title="T",
        video_url="https://example.com",
        opener_text="first",
        summary_text="s",
        outline_text=None,
        transcript_source="youtube_api",
        data_dir=tmp_data_dir,
    )
    write_artifact(
        video_id="abc123",
        channel_name="Ch",
        video_title="T",
        video_url="https://example.com",
        opener_text="second",
        summary_text="s",
        outline_text=None,
        transcript_source="youtube_api",
        data_dir=tmp_data_dir,
    )
    content = (tmp_data_dir / "summaries" / "abc123.txt").read_text()
    assert "second" in content
    assert "first" not in content
