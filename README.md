# YouTube Summarizer

Monitors a list of YouTube channels and emails you a clean summary when a new video posts.

## How it works (high level)

- Check each channel’s **RSS feed** for newly posted videos.
- For each new video:
  - Try to fetch the **YouTube transcript**.
  - If there’s no transcript, **download audio** and transcribe locally (Parakeet on Apple Silicon by default).
  - Create one or more outputs (prompt-driven; can include multiple sections per email).
  - Send a well-formatted email with the summary + a link to the video.
- Track what’s already been processed in a local **SQLite** database so you don’t get duplicates.

## “Queue” playlists (recommended workflow)

The easiest way to “send a video to the app” is to use YouTube playlists as queues:

- **SUMMARIZE playlist**: add any video to this playlist, and the app will summarize it using your configured prompts.
- **TRANSCRIBE playlist**: add any video to this playlist, and the app will send you a cleaned, readable transcript (no summarizing).

Configure these playlists in `config/channels.toml`.

## Do I need API keys?

- **YouTube**: **No API keys needed.** This project uses public YouTube RSS feeds.
- **Gmail**: No “API key”, but you **do** need a **Gmail App Password** (required for sending email via SMTP).
- **Ollama**: No keys needed (it runs locally on your Mac).
- **Hugging Face (optional)**: If you use Parakeet transcription, a free Hugging Face account/token can help avoid rate limits when downloading models.

## Install (macOS)

### 1) System tools

```bash
brew install yt-dlp ffmpeg
```

### 1a) Gmail App Password (required for sending email)

You’ll generate this in your Google Account. It’s a special password that lets an app send email without giving it your real Gmail password.

- Go to Google Account → Security: `https://myaccount.google.com/security`
- Turn on **2‑Step Verification** (if it’s not already on)
- Go to **App passwords**: `https://myaccount.google.com/apppasswords`
- Create one for “Mail” (or “Other”), copy the 16‑character password
- Paste it into `YTS_GMAIL_APP_PASSWORD` in your `.env`

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
- Optional: edit `config/process.md` (which prompts/sections to run for summarize mode)
- Optional: edit `config/transcribe.md` (AI cleanup prompt for transcribe mode)
- Copy `.env.example` to `.env` and fill in values (especially Gmail app password)

### 3b) (Optional) Avoid Hugging Face download rate limits

If Parakeet prints a warning about unauthenticated Hugging Face requests, you can create a free token:

- Create a token: `https://huggingface.co/settings/tokens`
- Then run your job with `HF_TOKEN` set (example):

```bash
export HF_TOKEN="your_token_here"
python -m youtube_summarizer run --limit 1
```

## Run

Run once (manual):

```bash
source .venv/bin/activate
python -m youtube_summarizer run
```

## Configuration quick reference

- `config/channels.toml`
  - `mode = "summarize"`: multi-section summary email (uses `config/process.md`)
  - `mode = "transcribe"`: transcript-only email (no summarizing)
- `config/process.md`
  - defines which summarization prompts are enabled (each enabled prompt becomes a section in the email)
- `config/transcribe.md`
  - defines the optional AI cleanup prompt for transcripts (used only if enabled via env)

## First-run checklist (recommended)

If you want a clean “follow this once and you’re done” setup guide, see `SETUP.md`.

## Scheduler (automatic runs)

This repo includes a macOS `launchd` job template you can enable later:

- `launchd/com.youtube-summarizer.plist`

We’ll wire it up once we confirm the exact MacWhisper CLI command on your machine.

