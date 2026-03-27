from __future__ import annotations

import logging
import re
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import requests

log = logging.getLogger(__name__)

_CHANNEL_ID_RE = re.compile(r"(?:youtube\.com/)?channel/(UC[a-zA-Z0-9_-]{20,})")
_PLAYLIST_ID_RE = re.compile(r"(?:list=)(PL[a-zA-Z0-9_-]{10,})")
_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{6,})")
_HANDLE_RE = re.compile(r"(?:youtube\.com/)?@([a-zA-Z0-9._-]{3,})/?")
_EXTERNAL_ID_RE = re.compile(r'"(?:externalId|channelId)"\s*:\s*"(UC[a-zA-Z0-9_-]{20,})"')
_HASHTAG_RE = re.compile(r"\s*#\w+")


@dataclass(frozen=True)
class VideoMeta:
    video_id: str
    url: str
    title: str
    published_at: str    # ISO 8601 string
    channel_name: str | None


def strip_hashtags(title: str) -> str:
    return _HASHTAG_RE.sub("", title).strip()


def source_url_to_rss(source_url: str) -> str | None:
    m = _CHANNEL_ID_RE.search(source_url)
    if m:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}"

    p = _PLAYLIST_ID_RE.search(source_url)
    if p:
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={p.group(1)}"

    h = _HANDLE_RE.search(source_url)
    if h:
        channel_id = _resolve_handle_to_channel_id(h.group(1))
        if channel_id:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    return None


def _resolve_handle_to_channel_id(handle: str) -> str | None:
    url = f"https://www.youtube.com/@{handle}"
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            },
        )
        r.raise_for_status()
    except Exception:
        return None
    m = _EXTERNAL_ID_RE.search(r.text)
    return m.group(1) if m else None


def fetch_videos_from_rss(rss_url: str, limit: int = 15) -> list[VideoMeta]:
    feed = feedparser.parse(rss_url)
    videos: list[VideoMeta] = []
    for entry in (feed.entries or [])[:max(0, limit)]:
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

        author_detail = getattr(entry, "author_detail", None)
        channel_name = str(getattr(author_detail, "name", "") or "").strip() or None

        videos.append(VideoMeta(
            video_id=video_id,
            url=link,
            title=strip_hashtags(title),
            published_at=published_at,
            channel_name=channel_name,
        ))
    return videos


def _infer_video_id(entry: object, link: str) -> str | None:
    yt_id = getattr(entry, "yt_videoid", None)
    if yt_id:
        return str(yt_id)
    m = _VIDEO_ID_RE.search(link)
    if m:
        return m.group(1)
    return None


def fetch_duration_seconds(video_url: str) -> int | None:
    try:
        env = dict(os.environ)
        brew_bin = "/opt/homebrew/bin"
        if brew_bin not in env.get("PATH", ""):
            env["PATH"] = f"{brew_bin}:{env.get('PATH', '')}"
        res = subprocess.run(
            ["yt-dlp", "--print", "duration", "--no-download", video_url],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if res.returncode == 0 and res.stdout.strip():
            return int(float(res.stdout.strip()))
    except Exception as e:
        log.debug("fetch_duration_seconds failed: %s", e)
    return None
