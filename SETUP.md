# Setup Guide (macOS)

One-time setup to get YouTube Summarizer running on your Mac.

---

## 1. Install system tools

```bash
brew install yt-dlp ffmpeg gum
```

- `yt-dlp` + `ffmpeg` — audio download and conversion
- `gum` — powers the interactive management script

### (Optional) Local summarization with Ollama

If you want free on-device summaries (no per-use cost):

```bash
brew install ollama
ollama serve &
ollama pull qwen2.5:14b
```

**Pick a model for your RAM:**
- 8–16 GB → `qwen2.5:7b`
- 24–32 GB → `qwen2.5:14b` (recommended)
- 64 GB+ → `qwen2.5:32b`

---

## 2. Create a Gmail App Password

This is a 16-character password that lets the app send mail without your real Gmail password.

1. Go to **Google Account → Security**: `https://myaccount.google.com/security`
2. Enable **2-Step Verification** (if not already on)
3. Go to **App Passwords**: `https://myaccount.google.com/apppasswords`
4. Create one — name it "YouTube Summarizer" or anything you like
5. Copy the 16-character password (you'll enter it in the next step)

---

## 3. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Create your personal config

`config/channels.toml` is gitignored so your real channel URLs stay private. Bootstrap it from the example:

```bash
cp config/channels.example.toml config/channels.toml
```

`manage.sh` also does this automatically on first run if the file is missing.

---

## 5. Run the setup script

```bash
./scripts/manage.sh
```

From the main menu, choose **Settings** and enter:

- `YTS_EMAIL_FROM` — your Gmail address
- `YTS_EMAIL_TO` — where summaries should be delivered
- Gmail App Password — the 16-character password from step 2
- Ollama model — e.g. `qwen2.5:14b` (leave blank if not using Ollama)

---

## 6. Add your channels and queues

Still inside `manage.sh`:

### Subscribe to a channel or playlist

Choose **Subscribe to channel or playlist**, paste a YouTube URL, and follow the prompts. The script will:

- Auto-detect the channel or playlist name via yt-dlp
- Show you all available prompts with descriptions
- Let you pick which prompts run for that feed (or leave all unselected to run all enabled prompts)

### Set up queue playlists (recommended)

Create two private playlists in your YouTube account — one for summarize, one for transcribe. Then use **Add summarize queue** and **Add transcribe queue** to register them.

Once configured, you can add any YouTube video to these playlists from the YouTube app or website and the summarizer will pick it up on the next run.

---

## 7. Test it

Either from `manage.sh` → **Run now → Dry run** (preview without sending), or directly:

```bash
source .venv/bin/activate
python -m youtube_summarizer run --dry-run --limit 1
```

Remove `--dry-run` to send a real email.

---

## 8. Enable the scheduler (optional but recommended)

To run automatically every 15 minutes, install the launchd service:

```bash
# Substitute your actual project path and install the plist
sed "s|__PROJECT_PATH__|$(pwd)|g" launchd/com.youtube-summarizer.plist \
  > ~/Library/LaunchAgents/com.youtube-summarizer.plist

launchctl load ~/Library/LaunchAgents/com.youtube-summarizer.plist
```

To reload after a config change:

```bash
launchctl unload ~/Library/LaunchAgents/com.youtube-summarizer.plist
launchctl load  ~/Library/LaunchAgents/com.youtube-summarizer.plist
```

Logs: `/tmp/youtube-summarizer.out.log` and `/tmp/youtube-summarizer.err.log`

---

## Troubleshooting

**No YouTube API keys needed** — this uses RSS, not the YouTube Data API.

**YouTube blocks audio downloads:**
Set `YTS_YTDLP_COOKIES_FROM_BROWSER="chrome"` in `.env` and try again.

**Parakeet warns about Hugging Face rate limits (optional fix):**
1. Create a free token: `https://huggingface.co/settings/tokens`
2. Add to `.env`: `HF_TOKEN="your_token_here"`

**Ollama isn't responding:**
Make sure `ollama serve` is running. The launchd service doesn't start Ollama automatically.

**Want debug output:**
```bash
python -m youtube_summarizer run --debug --limit 1
```
Or set `YTS_LOG_LEVEL=DEBUG` in `.env`.
