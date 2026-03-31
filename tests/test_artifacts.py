from pathlib import Path
from youtube_summarizer.artifacts import make_summary_id, write_artifact


def test_make_summary_id_format():
    sid = make_summary_id("abc123")
    assert sid.startswith("abc123-")
    assert len(sid) == len("abc123-") + 6  # 3 hex bytes = 6 chars


def test_make_summary_id_unique():
    ids = {make_summary_id("vid") for _ in range(20)}
    assert len(ids) == 20


def test_write_artifact_creates_file(tmp_data_dir):
    sid = make_summary_id("abc123")
    path = write_artifact(
        video_id="abc123",
        summary_id=sid,
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
    assert path.name == f"{sid}.txt"


def test_write_artifact_content(tmp_data_dir):
    sid = make_summary_id("abc123")
    write_artifact(
        video_id="abc123",
        summary_id=sid,
        channel_name="Test Channel",
        video_title="Test Video",
        video_url="https://youtube.com/watch?v=abc123",
        opener_text="This is the opener.",
        summary_text="This is the summary.",
        outline_text="1. First\n2. Second",
        transcript_source="parakeet_mlx",
        data_dir=tmp_data_dir,
    )
    content = (tmp_data_dir / "summaries" / f"{sid}.txt").read_text()
    assert f"summary_id: {sid}" in content
    assert "video_id: abc123" in content
    assert "OPENER" in content
    assert "SUMMARY" in content
    assert "OUTLINE" in content
    assert "parakeet_mlx" in content
