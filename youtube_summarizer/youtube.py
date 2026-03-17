from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


@dataclass(frozen=True)
class Video:
    video_id: str
    url: str
    title: str
    published_at: str


_CHANNEL_ID_RE = re.compile(r"(?:youtube\.com/)?channel/(UC[a-zA-Z0-9_-]{20,})")
_PLAYLIST_ID_RE = re.compile(r"(?:list=)(PL[a-zA-Z0-9_-]{10,})")
_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{6,})")


def source_url_to_rss(source_url: str) -> str | None:
    """
    Supports:
    - Channel RSS:  https://www.youtube.com/feeds/videos.xml?channel_id=UC...
    - Playlist RSS: https://www.youtube.com/feeds/videos.xml?playlist_id=PL...
    """
    m = _CHANNEL_ID_RE.search(source_url)
    if m:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}"

    p = _PLAYLIST_ID_RE.search(source_url)
    if p:
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={p.group(1)}"

    return None


def fetch_latest_videos_from_rss(rss_url: str, limit: int = 10) -> list[Video]:
    feed = feedparser.parse(rss_url)
    videos: list[Video] = []
    for entry in (feed.entries or [])[: max(0, limit)]:
        link = str(getattr(entry, "link", "") or "")
        title = str(getattr(entry, "title", "") or "").strip() or "Untitled"

        published = str(getattr(entry, "published", "") or "").strip()
        if published:
            published_at = published
        else:
            published_at = datetime.utcnow().isoformat()

        video_id = _infer_video_id(entry, link)
        if not video_id or not link:
            continue

        videos.append(Video(video_id=video_id, url=link, title=title, published_at=published_at))

    return videos


def _infer_video_id(entry: object, link: str) -> str | None:
    yt_id = getattr(entry, "yt_videoid", None)
    if yt_id:
        return str(yt_id)

    m = _VIDEO_ID_RE.search(link)
    if m:
        return m.group(1)

    return None


def fetch_youtube_transcript(video_id: str, preferred_languages: Iterable[str] = ("en",)) -> str | None:
    try:
        parts = YouTubeTranscriptApi.get_transcript(video_id, languages=list(preferred_languages))
    except (TranscriptsDisabled, NoTranscriptFound):
        return None

    lines = []
    for p in parts:
        text = str(p.get("text", "")).strip()
        if not text:
            continue
        lines.append(text)

    transcript = "\n".join(lines).strip()
    return transcript or None


def download_audio_with_ytdlp(video_url: str, out_path_no_ext: str) -> str:
    """
    Downloads best audio and returns the final file path.
    """
    # We call yt-dlp as a subprocess in transcribe.py to keep dependencies minimal here.
    raise NotImplementedError


def fetch_video_title_fallback(url: str) -> str | None:
    # Very light fallback: try to read HTML title. This avoids API keys but isn't guaranteed.
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception:
        return None
    m = re.search(r"<title>(.*?)</title>", r.text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return t or None

