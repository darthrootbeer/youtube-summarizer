# TODO

## Done

- [x] Channel monitoring via YouTube RSS (no API keys)
- [x] Seen-video tracking via SQLite (`data/state.db`)
- [x] Gmail sending via SMTP + App Password
- [x] macOS launchd scheduler (15-min poll)
- [x] Parakeet v3 transcription (parakeet-mlx, Apple Silicon)
- [x] Ollama-based summarization (local, no API cost)
- [x] Queue playlists — summarize queue + transcribe queue
- [x] Bootstrap guard — subscriptions skip historical videos on first run
- [x] Three-section config: `[[subscriptions]]` / `[summarize_queue]` / `[transcribe_queue]`
- [x] Per-feed prompt selection (`prompts = ["default", "glossary"]`)
- [x] 11 prompt types in individual files (`config/prompts/*.md`)
- [x] Length-adaptive tiers — short / medium / long variants per prompt
- [x] Transcript cleanup — filler removal, Q&A breaks, clause splitting, capitalization repair
- [x] Email header: source label, channel name, published date, video URL
- [x] Structured logging with `--debug` flag and `YTS_LOG_LEVEL`
- [x] `manage.sh` TUI — subscribe, manage queues, run, status, settings (requires `gum`)
- [x] `scripts/_config.py` — Python helper for all TOML read/write
- [x] action_checklist uses ☐ checkbox emoji for action items
- [x] Thumbnail in email header (hqdefault.jpg, deterministic URL, no extra network call)
- [x] Email redesign — premium newsletter look (gradient header, accent cards, depth shadows)
- [x] Prompt fine-tuning for qwen2.5:14b (output-only directives, format examples, hard stops)
- [x] `config/prompts/README.md` — custom prompt authoring guide
- [x] Repo sanitized for public release (no personal URLs/paths in tracked files)

## Backlog

- [ ] Re-check yt-dlp n-challenge issue once upstream fixes land (see PROJECT_STATUS.md)
- [ ] `manage.sh` — restart service after config changes
