# Setup Guide (macOS)

This is the “do it once” setup so this project can monitor channels and email you summaries.

## 1) Install system tools

Install the two tools this project relies on for audio downloads/transcoding:

```bash
brew install yt-dlp ffmpeg
```

Optional (for local summaries):

```bash
brew install ollama
```

## 2) Create a Gmail App Password (required)

This is a special password that lets an app send mail without using your real Gmail password.

- Open: `https://myaccount.google.com/security`
- Turn on **2‑Step Verification**
- Open: `https://myaccount.google.com/apppasswords`
- Create an App Password for “Mail” (or “Other”)
- Copy the 16‑character password

## 3) Create your `.env`

From the project folder:

```bash
cp .env.example .env
```

Edit `.env` and set:

- `YTS_EMAIL_FROM`: the Gmail address you’re sending from
- `YTS_EMAIL_TO`: where you want the summaries delivered
- `YTS_GMAIL_APP_PASSWORD`: the App Password you generated above
- `YTS_YTDLP_COOKIES_FROM_BROWSER`: set to `"chrome"` (recommended) if YouTube blocks audio downloads
- `YTS_OLLAMA_MODEL`: set this if you want local summaries (example: `"qwen2.5:14b"`)

## 4) Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5) Pick your channels

Edit `config/channels.toml`.

- Use channel URLs in the `.../channel/UC...` format (most reliable).
- Optionally set `prompt = "default"` (or another key you define).

## 6) (Optional) Customize the summary style

Edit `config/prompts.toml`.

- You can add multiple prompt templates under `[prompts]`
- A channel can select a prompt by setting `prompt = "your_key"` in `config/channels.toml`
- Keep the `{transcript}` placeholder in every prompt

## 7) (Optional) Start Ollama for local summaries

If you set `YTS_OLLAMA_MODEL`, start the Ollama server and download the model:

```bash
ollama serve & sleep 2
ollama pull qwen2.5:14b
```

## 8) Run a test

```bash
source .venv/bin/activate
python -m youtube_summarizer run --limit 1
```

You should receive one email.

## Notes / troubleshooting

- **No YouTube API keys needed**: this uses RSS.
- **If YouTube blocks downloads**: set `YTS_YTDLP_COOKIES_FROM_BROWSER="chrome"` in `.env` and try again.
- **If Parakeet warns about Hugging Face rate limits** (optional):
  - Create a token: `https://huggingface.co/settings/tokens`
  - Run with `HF_TOKEN` set in your shell:

```bash
export HF_TOKEN="your_token_here"
python -m youtube_summarizer run --limit 1
```

