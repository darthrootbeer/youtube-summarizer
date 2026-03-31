from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path


def make_summary_id(video_id: str) -> str:
    """Return a unique summary ID: {video_id}-{5 random hex chars}."""
    return f"{video_id}-{secrets.token_hex(3)}"


def write_artifact(
    video_id: str,
    summary_id: str,
    channel_name: str,
    video_title: str,
    video_url: str,
    opener_text: str,
    summary_text: str,
    outline_text: str | None,
    transcript_source: str,
    data_dir: Path,
) -> Path:
    """Write a debug .txt file to data/summaries/{summary_id}.txt."""
    out_dir = data_dir / "summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{summary_id}.txt"
    now = datetime.now(timezone.utc).isoformat()
    content = (
        f"summary_id: {summary_id}\n"
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
