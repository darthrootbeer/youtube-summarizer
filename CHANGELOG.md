# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-03-19

### Added
- `youtube_summarizer/glossary.py` — term tracking with 7-day rolling skip and max-3× lifetime cap, persisted to `data/glossary_terms.json`
- `config/prompts/01_opener.md` — new opener prompt: single polished universal takeaway sentence (22px in email)
- `config/prompts/02_summary.md` — new tiered summary prompt: 1/2/3 paragraphs, 3/5/7 bullets, 1–3 walk-away sentences by length
- `config/prompts/09_outline.md` — outline prompt with max 8 section labels, no timestamps

### Changed
- **Email redesign:** flat 5-block layout — opener → summary → glossary → outline → transcript; no more card borders
- **Subject line:** simplified to `[S] {title}` — hashtags stripped from all titles
- **Opener block:** 22px bold with blue left accent border, above summary, independent LLM call
- **Summary block:** 16px/1.5 line-height, grey "SUMMARY" label, tiered 3/5/7 bullets
- **Glossary block:** tracks known terms, skips recently defined ones, shows "No new terms identified" when empty
- **Transcript block:** always shown, 14px, full LLM cleanup (improved paragraph structure, section headers for medium/long)
- `youtube_summarizer/summarizer.py` — added `compact` param and `**extra_vars` to `summarize_with_ollama`; fixed `cleanup_summary` to preserve walk-away text after bullets
- `config/transcribe.md` — improved LLM cleanup prompt: sentence boundaries, capitalization, false starts, topic paragraphs, conditional section headers
- `config/prompts/08_glossary.md` — rewritten to use `{known_terms}` injection for skip-aware term selection

### Removed
- Transcribe-queue mode removed — only subscriptions and summarize queue going forward
- All specialty prompts disabled: `executive_brief`, `action_checklist`, `decisions_options`, `tldr_5_things`, `skeptics_review`, `fact_vs_opinion`, `quote_bank`, `role_based`, `outline_timestamps`

---

## [1.3.0] — 2026-03-18

### Added
- `config/channels.example.toml` — committed placeholder template for new installs
- `manage.sh` auto-copies `channels.example.toml` → `channels.toml` on first run if missing
- `load_channels()` raises a clear error with copy instructions if `channels.toml` is missing

### Changed
- `config/channels.toml` is now gitignored — personal channel/playlist URLs never enter the repo
- SETUP.md: new step 4 documents the manual bootstrap (`cp channels.example.toml channels.toml`)
- CLAUDE.md: updated "What NOT to commit" and channel config sections

---

## [1.2.0] — 2026-03-18

### Added
- Subscriptions listed inline on main menu with prompt summary
- Subscription detail screen — shows URL, per-prompt on/off status, Edit/Remove/Back actions
- `live_status()` header line — shows service state, subscription count, queue presence
- `cmd_show_subscription_detail` and `cmd_main_menu_subs` subcommands in `_config.py`

### Changed
- Arrow-key navigation throughout (via `gum choose`)
- `pick_prompts()` shows `[default: on/off]` per item — no separate legend needed
- Settings: password shows "(Already set)" instead of blank; only overwrites if new value entered
- Replaced all "Back to main menu?" confirms with `pause()` — press Enter to continue
- All Python heredocs use single-quoted `<<'PYEOF'` with `sys.argv` for safe variable passing

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
[2.0.0]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/darthrootbeer/youtube-summarizer/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/darthrootbeer/youtube-summarizer/releases/tag/v1.0.0
