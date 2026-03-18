# Architecture

This document explains how YouTube Summarizer works.

It starts with a plain‑language overview, then progressively gets more detailed.

## What this does (plain language)

You give the app a list of YouTube channels and/or playlists.

On a schedule (or when you run it manually), it:

- Checks each channel for new videos.
- For each new video, it tries to grab the written transcript from YouTube.
- If there’s no transcript, it downloads **audio only** and transcribes it locally on your Mac.
- It produces one or more outputs (summaries and/or transcripts), then emails you the result.
- It remembers what it already processed so you don’t get duplicates.

## The “happy path” (high level pipeline)

1. **Load configuration**
   - Channels list from `config/channels.toml`
   - Summarize prompt set from `config/process.md`
   - (Optional) Transcribe cleanup prompt from `config/transcribe.md`
   - Settings from `.env` (loaded into environment variables)
2. **Fetch recent videos**
   - Build an RSS URL for each channel
   - Parse RSS entries into “videos”
3. **Skip already-processed videos**
   - Use SQLite (`data/state.db`) to check if we’ve seen a video id before
4. **Get transcript**
   - Prefer YouTube’s transcript when available
   - Otherwise download audio + transcribe locally
5. **Produce output**
   - **Summarize mode**: run one or more enabled prompts (each becomes a separate email section)
   - **Transcribe mode**: generate a cleaned transcript (no summarizing)
6. **Render + send email**
   - Render HTML email with a clean layout
   - Include a “Beta stats” footer so we can see performance characteristics
7. **Mark video as seen**
   - Write the video id to SQLite so we don’t re-send it next run

## Key concepts / files

### Configuration

- `config/channels.toml`
  - A list of sources (usually YouTube channel URLs in the `.../channel/UC...` form)
  - Each source can be `mode = "summarize"` or `mode = "transcribe"`
- `config/process.md`
  - Summarize-mode “jobs” (prompt templates)
  - Each enabled prompt becomes a labeled section in the email
- `config/transcribe.md`
  - Transcribe-mode optional AI cleanup prompt (only used when enabled via env)
- `.env` (not committed)
  - Email settings, transcription backend choice, cookies settings, and optional Ollama model name
- `.env.example`
  - Copy this to `.env` when setting up

### Main orchestration

- `youtube_summarizer/run.py`
  - This is the “conductor”
  - It loads config, fetches videos, gets transcripts, summarizes, renders email, sends email, and marks videos as seen

### YouTube integration

- `youtube_summarizer/youtube.py`
  - Converts channel/playlist URLs into RSS feed URLs
  - Parses RSS into video items
  - Fetches YouTube transcripts when available (fast path)

### Summarization

- `youtube_summarizer/summarizer.py`
  - Calls Ollama (`ollama run ...`) using enabled prompt templates
  - Includes a conservative cleanup pass to avoid repeated/extra sections leaking into emails

### Email sending

- `youtube_summarizer/templates/email.html.j2`
  - Email HTML layout template
  - Summary is rendered as HTML (paragraphs + bullet list formatting)
  - Beta stats are appended at the bottom
- `youtube_summarizer/emailer.py`
  - Sends the message via Gmail SMTP using an App Password

### State tracking (deduping)

- `youtube_summarizer/db.py` (and the SQLite database)
  - Stores a `seen_videos` table keyed by video id
  - Prevents duplicate sends
  - Lives at `data/state.db` by default

## Transcript strategy (fast path vs fallback)

### Fast path: YouTube transcript

If YouTube provides an official transcript/captions, we use that.

Benefits:
- Very fast
- No downloads
- No local compute

### Fallback: audio download + local transcription

If there’s no transcript:

1. **Download audio-only media**
   - Uses `yt-dlp`
   - Prefers smaller, low-bitrate audio streams (still good enough for transcription)
2. **Transcribe locally**
   - Default: Parakeet (`parakeet-mlx`) on Apple Silicon
   - Optional alternative: `whisper.cpp`

## Summarization strategy

### Local summarization (Ollama)

If `YTS_OLLAMA_MODEL` is set, the summarizer:

- Builds prompts from `config/process.md`
- Calls `ollama run <model>`
- Returns the generated output text

## Transcribe mode (transcript-only emails)

Transcribe mode is designed for “just give me an accurate transcript” workflows:

- Always downloads audio and transcribes locally (Parakeet by default)
- Produces a cleaned, readable transcript (no summarizing)
- Optional: enable AI-assisted cleanup using `config/transcribe.md` + `YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`

### Fallback summarization

If Ollama isn’t running / configured, the system still sends an email with a simple fallback summary.

## Email rendering

The summary text often contains lightweight markdown-like formatting (paragraphs, `-` bullets).

Before sending HTML email, we convert that into proper HTML so Gmail shows:

- Paragraph spacing
- Bullets as real list items
- A “Key takeaways” header when present

This keeps the email skimmable.

## Beta stats (performance instrumentation)

During beta, every email includes a footer showing:

- Media size (MB)
- Download time (seconds)
- Transcribe time (seconds)
- Summarize time (seconds)
- Total time to send (seconds)

This makes it easy to see where time is being spent.

## Cleanup (disk usage)

When we download audio and create transcripts, those files can accumulate.

On every run, the app performs best‑effort cleanup of old files in:

- `data/audio/`
- `data/audio/parakeet/`

Retention is controlled by:

- `YTS_AUDIO_RETENTION_DAYS` (default: 7)

## Running it

- Manual run:
  - `python -m youtube_summarizer run --limit 1`
- Dry run (no email sent, no “seen” writes):
  - `python -m youtube_summarizer run --dry-run --limit 1`

## What’s intentionally NOT here (yet)

- A hosted server/API (this is a local Mac app)
- A cloud-based summarization provider (Ollama is local)
- A YouTube Data API integration (RSS avoids API keys)

