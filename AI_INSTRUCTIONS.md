# AI Instructions

This repo is a local macOS app. Keep it simple, local-first, and easy to maintain.

## Principles

- Simple to install on macOS
- Built on existing tools (yt-dlp, ffmpeg, Parakeet, Ollama)
- No API keys required for YouTube (uses RSS)
- Transcript-first: always use Parakeet for transcription (YouTube transcript API is disabled)

## Prompt system

Prompt templates live in `config/prompts/` — one `.md` file per prompt.

Each file has three variants: `## short`, `## medium`, `## long`.
The correct variant is selected automatically based on transcript length.

Every prompt template must include `{transcript}`.

**To add a new prompt:**
1. Create `config/prompts/NN_key_name.md` following the existing file format.
2. Set `enabled: true` or `false`.
3. No code changes needed — the loader picks it up automatically.

## Channel config

`config/channels.toml` — three sections:

```toml
[[subscriptions]]
name    = "Channel Name"
url     = "https://www.youtube.com/channel/UCxxx"
prompts = ["default", "glossary"]   # optional; omit to run all enabled prompts

[summarize_queue]
name    = "My Summarize Playlist"
url     = "https://www.youtube.com/playlist?list=PLxxx"
prompts = ["default"]

[transcribe_queue]
name    = "My Transcribe Playlist"
url     = "https://www.youtube.com/playlist?list=PLxxx"
```

`prompts` is a list of prompt keys. Omit it to run all enabled prompts.
Do not use the old `prompt = "default"` single-string form.

## Email formatting

When changing email layout, optimise for:
- Fast scanning (headline → summary → link)
- Clean typography, no visual clutter
- Works well in Gmail

The HTML template is `youtube_summarizer/templates/email.html.j2`.
Summary text is converted to HTML by `_format_summary_html()` in `run.py`.

## Config loading

`youtube_summarizer/config.py` is the single source of truth for all config parsing:
- `load_channels()` — parses `channels.toml`
- `load_process_prompts()` — reads from `config/prompts/` directory
- `load_transcribe_prompts()` / `load_transcribe_options()` — reads `config/transcribe.md`
- `load_settings()` — reads environment variables

## Management scripts

`scripts/manage.sh` — gum-based TUI for setup and management.
`scripts/_config.py` — Python CLI for all TOML mutations (called by `manage.sh`).

Do not add direct TOML manipulation to the bash script; route all writes through `_config.py`.
