# Project Status

**State:** Fully operational. Running as a macOS launchd service, polling every 15 minutes.

---

## Source routing (`config/channels.toml`)

Three source types, each with its own behaviour:

| Section | Behaviour | Bootstrap | Default prompts |
|---|---|---|---|
| `[[subscriptions]]` | New videos only (post-first-run) | Yes — historical videos silently skipped | All enabled prompts (or per-feed override) |
| `[summarize_queue]` | Drain playlist to empty | No | Configurable via `prompts = [...]` |
| `[transcribe_queue]` | Drain playlist to empty | No | Transcript cleanup only |

### Per-feed prompt selection

Any subscription or queue can specify exactly which prompts to run:

```toml
[[subscriptions]]
name    = "AI News & Strategy Daily | Nate B Jones"
url     = "https://www.youtube.com/channel/UC0C-17n9iuUQPylguM1d-lQ"
prompts = ["default", "glossary"]
```

Omitting `prompts` runs all globally-enabled prompts.

---

## Email subjects

| Source type | Subject format |
|---|---|
| Subscription | `[YT Summary] [SUB] Channel — Video Title` |
| Summarize queue | `[YT Summary] Video Title` |
| Transcribe queue | `[YT Summary] [TRANSCRIPTION] Video Title` |

---

## Email content

Every email includes:
- Source label + channel/playlist name (header)
- Video title (bold, header)
- Channel name
- Published date & time
- Video URL
- One labeled card per enabled prompt
- Transcript source + beta stats footer

---

## Prompt system

### Available prompts (`config/prompts/`)

| Key | Label | Enabled |
|---|---|---|
| `default` | Summary | yes |
| `executive_brief` | Executive brief (5-minute read) | yes |
| `action_checklist` | Action checklist | yes |
| `decisions_options` | Key decisions + options | no |
| `tldr_5_things` | TL;DR + things to remember | no |
| `skeptics_review` | Skeptic's review | no |
| `fact_vs_opinion` | Fact vs opinion separation | no |
| `glossary` | Glossary (plain English) | no |
| `outline_timestamps` | Structured outline with timestamps | no |
| `quote_bank` | Quote bank + shareables | no |
| `role_based` | Role-based versions (founder/PM/creator) | no |

### Length-adaptive tiers

Each prompt has three variants (short / medium / long), selected automatically by transcript length:

| Tier | Chars | Duration | `default` output |
|---|---|---|---|
| short | < 8k | < ~9 min | 100w body, 3 bullets, 1-sentence wrap-up |
| medium | 8k–22k | ~9–25 min | 200w body, 5 bullets, 1–2 sentence wrap-up |
| long | > 22k | ~25+ min | 300w body, 8 bullets, 2–3 sentence wrap-up |

---

## Transcript pipeline

- Always uses **Parakeet MLX** for transcription (local, Apple Silicon).
- YouTube transcript API is never used.
- Audio cached in `data/audio/`, cleaned up after 7 days (`YTS_AUDIO_RETENTION_DAYS`).

### Transcript cleanup (transcribe mode)

Deterministic cleanup runs on all transcribe-mode output:

| Option | Status |
|---|---|
| `remove_fillers` (um, uh, kind of, you know…) | on |
| `questions_own_paragraph` | on |
| `robust_sentence_breaks` | on |
| `qa_paragraph_breaks` | on |
| `split_long_clauses` | on |
| `strip_stage_directions` | off |
| `normalize_numbers` | off |
| `speaker_labels` | off |

Optional AI-assisted cleanup: set `YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`.

---

## Management script

```bash
./scripts/manage.sh
```

| Menu option | What it does |
|---|---|
| Subscribe | Add a channel/playlist, pick per-feed prompts |
| Add transcribe queue | Set transcribe playlist + cleanup options |
| Add summarize queue | Set summarize playlist + prompts |
| Manage subscriptions | List, remove, or edit per-feed prompts |
| Run now | Manual trigger (normal or dry-run) |
| Service status | launchd state, DB stats, recent logs |
| Settings | Guided `.env` setup |

---

## Infrastructure

| Component | Detail |
|---|---|
| Scheduler | `~/Library/LaunchAgents/com.youtube-summarizer.plist` — login launch, 15-min poll |
| State DB | `data/state.db` — SQLite (`seen_videos` + `bootstrapped_channels`) |
| Logs | `/tmp/youtube-summarizer.out.log`, `/tmp/youtube-summarizer.err.log` |
| Reload | `launchctl unload/load ~/Library/LaunchAgents/com.youtube-summarizer.plist` |

---

## Known issue (yt-dlp / YouTube)

`yt-dlp` may fail with "n challenge" errors on some videos even with browser cookies.

- Symptom: "Requested format is not available"
- Workaround: `YTS_YTDLP_COOKIES_FROM_BROWSER=chrome` in `.env`
- Status: monitoring for upstream yt-dlp fix
