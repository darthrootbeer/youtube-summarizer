# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-03-18

### Added
- `manage.sh` symlink at repo root for discoverability (points to `scripts/manage.sh`)
- Management script menu table, email subjects table, and known yt-dlp issue added to README

### Changed
- `CLAUDE.md` now consolidates all AI/contributor instructions (merged from `AI_INSTRUCTIONS.md`)
- README Docs section updated — `PROJECT_STATUS.md` removed, `config/prompts/README.md` added

### Removed
- `config/prompts.toml` — superseded by `config/prompts/` directory (loader never reached it)
- `config/process.md` — superseded by `config/prompts/` directory
- `AI_INSTRUCTIONS.md` — content merged into `CLAUDE.md`
- `PROJECT_STATUS.md` — content absorbed into README and ARCHITECTURE
- `.cursorrules` — redundant with `CLAUDE.md`

---

## [1.0.1] — 2026-03-18

### Changed

- Only the `default` (Summary) prompt is enabled globally by default.
  `executive_brief` and `action_checklist` are now `enabled: false` — opt in per feed via `prompts` in `channels.toml`.
- README: clarified two-level prompt selection (global default vs per-feed override).

---

## [1.0.0] — 2026-03-18

First public release.

### Added

- Channel monitoring via YouTube RSS (no API keys)
- Seen-video deduplication via SQLite (`data/state.db`)
- Gmail sending via SMTP + App Password
- macOS launchd scheduler (15-minute poll)
- Parakeet v3 (parakeet-mlx) local transcription — Apple Silicon only
- Ollama-based summarization (`qwen2.5:14b` recommended)
- Queue playlists — SUMMARIZE queue and TRANSCRIBE queue
- Bootstrap guard — subscriptions skip historical videos on first run
- Three-section config: `[[subscriptions]]` / `[summarize_queue]` / `[transcribe_queue]`
- Per-feed prompt selection (`prompts = ["default", "glossary"]` in `channels.toml`)
- 11 prompt types in individual files (`config/prompts/*.md`)
- Length-adaptive tiers — `short` / `medium` / `long` variants per prompt, selected by transcript length
- Transcript cleanup pipeline — filler removal, Q&A paragraph breaks, long clause splitting, capitalisation repair
- Email header: source label, channel name, published date, video URL, thumbnail
- Premium email design — gradient header, accent section cards, depth shadows
- Structured logging with `--debug` flag and `YTS_LOG_LEVEL` env var
- `manage.sh` TUI — subscribe, manage queues, run, status, settings (requires `gum`)
- `scripts/_config.py` — Python CLI for all TOML mutations
- `config/prompts/README.md` — custom prompt authoring guide with qwen2.5:14b tuning tips

---

<!-- Links -->
[1.1.0]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/darthrootbeer/youtube-summarizer/releases/tag/v1.0.0
