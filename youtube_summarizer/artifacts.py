from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def write_artifact(
    video_id: str,
    channel_name: str,
    video_title: str,
    video_url: str,
    opener_text: str,
    summary_text: str,
    outline_text: str | None,
    transcript_source: str,
    data_dir: Path,
) -> Path:
    """Write a debug .txt file to data/summaries/{video_id}.txt. Overwrites if exists."""
    out_dir = data_dir / "summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{video_id}.txt"
    now = datetime.now(timezone.utc).isoformat()
    content = (
        f"video_id: {video_id}\n"
        f"channel: {channel_name}\n"
        f"title: {video_title}\n"
        f"url: {video_url}\n"
        f"transcript_source: {transcript_source}\n"
        f"generated_at: {now}\n"
        f"\nOPENER\n{opener_text}\n"
        f"\n---\n"
        f"\nSUMMARY\n{summary_text}\n"
        f"\n---\n"
        f"\nOUTLINE\n{outline_text or '(none)'}\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def artifact_exists(video_id: str, data_dir: Path) -> bool:
    return (data_dir / "summaries" / f"{video_id}.txt").exists()
