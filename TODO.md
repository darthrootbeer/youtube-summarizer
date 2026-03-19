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
- [x] Thumbnail in email header (maxresdefault.jpg, deterministic URL, no extra network call)
- [x] Email redesign — flat 5-block layout: opener → summary → glossary → outline → transcript
- [x] Prompt fine-tuning for qwen2.5:14b (output-only directives, format examples, hard stops)
- [x] `config/prompts/README.md` — custom prompt authoring guide
- [x] Repo sanitized for public release (no personal URLs/paths in tracked files)
- [x] Glossary term tracking — 7-day rolling skip, max 3× lifetime, persisted to `data/glossary_terms.json`
- [x] Video duration in email meta strip (via yt-dlp metadata, ffprobe fallback)
- [x] Avg CPU % in debug stats (resource.getrusage delta across per-video processing window)
- [x] Video description + chapters injected as LLM context block before all prompts
- [x] Creator chapters used as outline (with clickable timestamp links); LLM outline is fallback only
- [x] Hallucination guards — transcript cleanup and glossary validate output before accepting

## Backlog

### Output quality

- [ ] **Use duration as primary summary tier signal** — replace transcript char-count tier boundaries (8k/22k) with video duration (already in `meta_duration_s`). Speaking pace varies; a dense 7-min tutorial and a slow 7-min chat produce wildly different char counts. Transcript chars become the fallback only.
- [ ] **Increase transcript compaction tail** — `_compact_transcript()` keeps 14k head + 2.5k tail. For podcasts/interviews the key content is often in the middle. Raise tail to 5k and add a `truncated=true` flag to debug stats when compaction fires.
- [ ] **Short video outline guard** — `_outline_point_count()` returns 3 for videos < 5 min, but a 60-second clip has no structure. Skip outline entirely if `video_duration_s < 120`.
- [ ] **Video description links block** — extract URLs and structured content from the yt-dlp `description` field (already fetched). Render as an email block between Summary and Glossary: linked URLs, timestamp links, named people or resources. `meta.get("description")` is already available.

### Reliability

- [ ] **LLM retry on timeout** — `_run_llm()` and `_summarize()` immediately fall back on any exception. Add one retry with a short delay before falling back; most Ollama timeouts are transient.
- [ ] **Log fallback decisions in debug stats** — when hallucination guards or fallbacks fire, record which section triggered and why in `beta_stats.qa_notes` so it's visible in the email artifact without digging through logs.
- [ ] **Parallel RSS fetches** — 14 channels means 14 sequential HTTP requests before anything processes. Use `ThreadPoolExecutor` to fetch all feeds concurrently; should cut poll startup time by ~10×.
- [ ] **Deleted/unavailable video handling** — when yt-dlp fails with a 404/unavailable error, log a clear warning and continue. Currently the error propagates and may block the rest of the batch.

### Technical debt

- [ ] **Magic numbers → named constants** — `14000`/`2500` (compaction), `8000`/`22000` (tier boundaries), `600`/`120` (timeouts), `4000` (glossary max length), `52` (chapter title max) are all inline. Move to named constants at the top of `run.py`.
- [ ] **Channel name auto-update uses regex on raw TOML** — `_best_effort_update_channel_name_in_config()` rewrites `channels.toml` with string regex. Fragile on edge-case TOML syntax. Rewrite using `tomllib` parse + serialise round-trip via `_config.py`.
- [ ] **`manage.sh` — restart service after config changes** — currently requires manual `launchctl` after editing channels or settings via the TUI.

### Lower priority

- [ ] **Glossary definition length guard** — if any single glossary definition block exceeds ~300 chars, reject the entire glossary output as hallucinated (model echoed the transcript). Currently only the total length (4000 chars) is checked.
- [ ] **Re-check yt-dlp n-challenge issue** — once upstream fixes land (see PROJECT_STATUS.md).
