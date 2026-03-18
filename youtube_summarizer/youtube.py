from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, RequestBlocked, TranscriptsDisabled


@dataclass(frozen=True)
class Video:
    video_id: str
    url: str
    title: str
    published_at: str


_CHANNEL_ID_RE = re.compile(r"(?:youtube\.com/)?channel/(UC[a-zA-Z0-9_-]{20,})")
_PLAYLIST_ID_RE = re.compile(r"(?:list=)(PL[a-zA-Z0-9_-]{10,})")
_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{6,})")
_HANDLE_RE = re.compile(r"(?:youtube\.com/)?@([a-zA-Z0-9._-]{3,})/?")
_EXTERNAL_ID_RE = re.compile(r'"(?:externalId|channelId)"\s*:\s*"(UC[a-zA-Z0-9_-]{20,})"')


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

    # Handle URLs like https://www.youtube.com/@SomeHandle
    h = _HANDLE_RE.search(source_url)
    if h:
        channel_id = _resolve_handle_to_channel_id(h.group(1))
        if channel_id:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    return None


def _resolve_handle_to_channel_id(handle: str) -> str | None:
    """
    Resolves a YouTube handle (no @) to a UC... channel id by fetching the channel page HTML
    and extracting `externalId` / `channelId`.

    This avoids API keys and keeps RSS-based operation possible.
    """
    url = f"https://www.youtube.com/@{handle}"
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            },
        )
        r.raise_for_status()
    except Exception:
        return None
    m = _EXTERNAL_ID_RE.search(r.text)
    return m.group(1) if m else None


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
            published_at = datetime.now(timezone.utc).isoformat()

        video_id = _infer_video_id(entry, link)
        if not video_id or not link:
            continue

        videos.append(Video(video_id=video_id, url=link, title=title, published_at=published_at))

    return videos


def fetch_channel_title_from_rss(rss_url: str) -> str | None:
    """
    Best-effort: return the human display name for the RSS feed.
    """
    feed = feedparser.parse(rss_url)
    title = str(getattr(getattr(feed, "feed", None), "title", "") or "").strip()
    if title:
        return title
    return None


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
        # youtube-transcript-api v1.2+ uses instance methods `fetch` / `list`
        api = YouTubeTranscriptApi()
        parts = api.fetch(video_id, languages=list(preferred_languages))
    except (TranscriptsDisabled, NoTranscriptFound, RequestBlocked):
        return None

    lines = []
    for p in parts:
        # parts yields `FetchedTranscriptSnippet` items, each with `.text`
        text = str(getattr(p, "text", "") or "").strip()
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

