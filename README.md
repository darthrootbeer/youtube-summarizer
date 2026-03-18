# YouTube Summarizer

Monitors YouTube channels and playlists, transcribes audio locally, and emails you a clean summary when a new video posts.

## How it works

- Checks each channel's **RSS feed** for newly posted videos.
- For each new video: downloads audio and transcribes locally (Parakeet on Apple Silicon).
- Runs one or more **prompt-driven outputs** — each becomes a labeled section in the email.
- Sends a well-formatted HTML email with the result and a link to the video.
- Tracks processed videos in a local **SQLite** database to prevent duplicates.

## Summary length adapts to video length

Prompts automatically scale based on transcript length:

| Video length | Body | Bullets | Wrap-up |
|---|---|---|---|
| < ~9 min | ~100 words | 3 | 1 sentence |
| ~9–25 min | ~200 words | 5 | 1–2 sentences |
| ~25+ min | ~300 words | 8 | 2–3 sentences |

## Queue playlists (recommended workflow)

The easiest way to send a video to the app is to add it to one of your YouTube playlists:

- **SUMMARIZE playlist** — add any video to queue it for summarization.
- **TRANSCRIBE playlist** — add any video to queue it for a clean, readable transcript (no summarizing).

## Do I need API keys?

- **YouTube** — no API keys. Uses public RSS feeds.
- **Gmail** — no API key, but you need a [Gmail App Password](https://myaccount.google.com/apppasswords).
- **Ollama** — no keys. Runs locally on your Mac.
- **Hugging Face** — optional free token to avoid download rate limits for Parakeet.

---

## Install (macOS)

### 1. System tools

```bash
brew install yt-dlp ffmpeg gum
```

`gum` powers the interactive setup script. `yt-dlp` + `ffmpeg` handle audio download and conversion.

### 2. (Optional) Local summaries with Ollama

If you want free local summarization (no per-use cost):

```bash
brew install ollama
ollama serve &
ollama pull qwen2.5:14b   # or qwen2.5:7b for 8–16 GB RAM, qwen2.5:32b for 64 GB+
```

### 3. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the setup script

```bash
./scripts/manage.sh
```

Select **Settings** to enter your email credentials, then **Subscribe** to add your first channel.

For a detailed walkthrough, see `SETUP.md`.

---

## Configuration files

| File | Purpose |
|---|---|
| `config/channels.toml` | Sources (channels + queue playlists) and per-feed prompt selection |
| `config/prompts/` | One `.md` file per prompt, each with `short` / `medium` / `long` tier variants |
| `config/transcribe.md` | Transcript cleanup options (filler removal, paragraph breaks, Q&A detection, etc.) |
| `.env` | Email settings, Ollama model, and other secrets (not committed) |

### Per-feed prompt selection

By default, all globally-enabled prompts run for every subscription. To override for a specific feed:

```toml
[[subscriptions]]
name    = "My Channel"
url     = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
prompts = ["default", "glossary"]
```

Leaving `prompts` unset runs all enabled prompts.

### Available prompts

| Key | Label | Default |
|---|---|---|
| `default` | Summary | on |
| `executive_brief` | Executive brief | on |
| `action_checklist` | Action checklist | on |
| `decisions_options` | Key decisions + options | off |
| `tldr_5_things` | TL;DR + things to remember | off |
| `skeptics_review` | Skeptic's review | off |
| `fact_vs_opinion` | Fact vs opinion separation | off |
| `glossary` | Glossary (plain English) | off |
| `outline_timestamps` | Structured outline with timestamps | off |
| `quote_bank` | Quote bank + shareables | off |
| `role_based` | Role-based versions (founder/PM/creator) | off |

Enable or disable them by editing `enabled: true/false` in the prompt file, or use `manage.sh` to set per-feed overrides.

---

## Running

```bash
# Manual run (sends emails)
source .venv/bin/activate
python -m youtube_summarizer run

# Dry run (no emails, no DB writes)
python -m youtube_summarizer run --dry-run

# Or use the management script
./scripts/manage.sh   # → "Run now"
```

## Scheduler (automatic, runs every 15 min)

```bash
# Install (run once from the project directory)
sed "s|__PROJECT_PATH__|$(pwd)|g" launchd/com.youtube-summarizer.plist \
  > ~/Library/LaunchAgents/com.youtube-summarizer.plist
launchctl load ~/Library/LaunchAgents/com.youtube-summarizer.plist

# Reload after config changes
launchctl unload ~/Library/LaunchAgents/com.youtube-summarizer.plist
launchctl load  ~/Library/LaunchAgents/com.youtube-summarizer.plist
```

Logs: `/tmp/youtube-summarizer.out.log` and `/tmp/youtube-summarizer.err.log`

---

## Docs

- `SETUP.md` — step-by-step first-time setup
- `ARCHITECTURE.md` — how everything fits together
- `PROJECT_STATUS.md` — current operational state
- `UNINSTALL.md` — how to remove the app
