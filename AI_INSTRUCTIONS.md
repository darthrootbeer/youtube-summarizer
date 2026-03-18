# AI Instructions

This repo is intended to be:

- Simple to install on macOS
- Built on existing tools where possible
- Transcript-first (YouTube transcript when available), with a local transcription fallback

When changing email formatting, optimize for:

- Fast scanning (headline + summary block + link)
- Clean typography
- Minimal noise

When changing prompts / summarization behavior:

- Prompt templates live in `config/prompts.toml` under `[prompts]`.
- Channels can select a prompt via `prompt = "some_key"` in `config/channels.toml`.
- Prompts must include `{transcript}`.

