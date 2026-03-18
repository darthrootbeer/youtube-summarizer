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

### How prompts are selected

Prompts work at two levels:

**1. Global default (`enabled:` in the prompt file)**

Each prompt file has an `enabled: true/false` field. When a feed has no explicit `prompts` list, all globally-enabled prompts run. Only the Summary prompt is on by default — everything else is opt-in.

**2. Per-feed override (`prompts` in `channels.toml`)**

Add a `prompts` list to any subscription or queue to run exactly those prompts for that feed, regardless of the global `enabled` setting:

```toml
[[subscriptions]]
name    = "My Channel"
url     = "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
prompts = ["default", "executive_brief", "glossary"]
```

Omitting `prompts` falls back to the global defaults. Each channel or playlist gets its own independent list.

### Available prompts

| Key | Label | On by default |
|---|---|---|
| `default` | Summary | yes |
| `executive_brief` | Executive brief | no |
| `action_checklist` | Action checklist | no |
| `decisions_options` | Key decisions + options | no |
| `tldr_5_things` | TL;DR + things to remember | no |
| `skeptics_review` | Skeptic's review | no |
| `fact_vs_opinion` | Fact vs opinion separation | no |
| `glossary` | Glossary (plain English) | no |
| `outline_timestamps` | Structured outline with timestamps | no |
| `quote_bank` | Quote bank + shareables | no |
| `role_based` | Role-based versions (founder/PM/creator) | no |

To change the global default for a prompt, edit `enabled:` in its file under `config/prompts/`. To customise per feed, use the `prompts` list in `channels.toml`.

---

## Management script

The interactive TUI handles all setup and ongoing management:

```bash
./manage.sh   # root symlink — or: ./scripts/manage.sh
```

| Option | What it does |
|---|---|
| Subscribe | Add a channel/playlist, pick per-feed prompts |
| Add summarize queue | Set summarize playlist + prompts |
| Add transcribe queue | Set transcribe playlist + cleanup options |
| Manage subscriptions | List, remove, or edit per-feed prompts |
| Run now | Manual trigger (normal or dry-run) |
| Service status | launchd state, DB stats, recent logs |
| Settings | Guided `.env` setup |

## Running

```bash
# Manual run (sends emails)
source .venv/bin/activate
python -m youtube_summarizer run

# Dry run (no emails, no DB writes)
python -m youtube_summarizer run --dry-run
```

## Email subjects

| Source type | Subject format |
|---|---|
| Subscription | `[YT Summary] [SUB] Channel — Video Title` |
| Summarize queue | `[YT Summary] Video Title` |
| Transcribe queue | `[YT Summary] [TRANSCRIPTION] Video Title` |

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

## Known issues

**yt-dlp "n challenge" errors** — some videos fail with "Requested format is not available".
Workaround: set `YTS_YTDLP_COOKIES_FROM_BROWSER=chrome` in `.env`. Monitoring for an upstream fix.

---

## Docs

- `SETUP.md` — step-by-step first-time setup
- `ARCHITECTURE.md` — how everything fits together
- `config/prompts/README.md` — how to write custom prompts
- `UNINSTALL.md` — how to remove the app
