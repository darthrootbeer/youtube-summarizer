# YouTube Summarizer

Monitors a list of YouTube channels and emails you a clean summary when a new video posts.

## How it works (high level)

- Check each channel’s **RSS feed** for newly posted videos.
- For each new video:
  - Try to fetch the **YouTube transcript**.
  - If there’s no transcript, **download audio** and transcribe locally (MacWhisper CLI).
  - Create a summary (prompt-driven; supports per-channel prompt selection).
  - Send a well-formatted email with the summary + a link to the video.
- Track what’s already been processed in a local **SQLite** database so you don’t get duplicates.

## Install (macOS)

### 1) System tools

```bash
brew install yt-dlp ffmpeg
```

### 1b) (Optional) Free local summaries with Ollama

If you want “free” summaries (no per-use token cost), you can run a local model on your Mac.

#### Get your Mac specs (so we pick the right model)

Run:

```bash
system_profiler SPHardwareDataType SPSoftwareDataType | sed -n '1,120p'
```

Look for **Chip** and **Memory**.

#### Recommended Ollama model by RAM (Apple Silicon)

- **8–16 GB RAM**: `qwen2.5:7b` (fastest / lightest)
- **24–32 GB RAM**: `qwen2.5:14b` (recommended balance)
- **64 GB+ RAM**: `qwen2.5:32b` (best local quality)

#### Install + download model

```bash
brew install ollama
ollama serve & sleep 2
ollama pull qwen2.5:14b
```

### 2) Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure channels + email

- Edit `config/channels.toml`
- Optional: edit `config/prompts.toml` (and/or set `prompt = "..."` per channel)
- Copy `.env.example` to `.env` and fill in values (especially Gmail app password)

## Run

Run once (manual):

```bash
source .venv/bin/activate
python -m youtube_summarizer run
```

## Scheduler (automatic runs)

This repo includes a macOS `launchd` job template you can enable later:

- `launchd/com.youtube-summarizer.plist`

We’ll wire it up once we confirm the exact MacWhisper CLI command on your machine.

