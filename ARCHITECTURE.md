# Architecture

How YouTube Summarizer works — plain language first, then progressively more detail.

---

## What this does

You give the app a list of YouTube channels and/or playlists.

On a schedule (or manually), it:

1. Checks each source for new videos via RSS.
2. Downloads audio and transcribes it locally (Parakeet on Apple Silicon).
3. Runs one or more prompt-driven outputs (summaries and/or clean transcripts).
4. Emails you the result as a formatted HTML message.
5. Records what it processed so you never get duplicates.

---

## Pipeline (happy path)

```
Load config
  ↓
For each source in channels.toml
  ↓
Fetch RSS → parse videos
  ↓
Skip seen videos (SQLite)
  ↓
Bootstrap guard (subscriptions only) → mark historical videos seen, skip them
  ↓
Download audio (yt-dlp) → transcribe (Parakeet)
  ↓
Determine tier (short / medium / long) from transcript length
  ↓
For each prompt assigned to this feed:
  Run Ollama with the tier-appropriate prompt template
  ↓
Render HTML email (Jinja2)
  ↓
Send via Gmail SMTP
  ↓
Mark video as seen (SQLite)
```

---

## Source types

Three source types are configured in `config/channels.toml`, each with distinct behaviour:

| Section | Behaviour | Bootstrap |
|---|---|---|
| `[[subscriptions]]` | New videos only (post-first-run) | Yes — historical videos silently skipped |
| `[summarize_queue]` | Drain playlist to empty | No — always processed |
| `[transcribe_queue]` | Drain playlist to empty | No — always processed |

### Per-feed prompt selection

Every source can specify which prompts to run:

```toml
[[subscriptions]]
name    = "Some Channel"
url     = "https://www.youtube.com/channel/UCxxx"
prompts = ["default", "glossary"]   # run only these two
```

Omitting `prompts` runs all globally-enabled prompts.

---

## Prompt system

### File layout

Each prompt lives in its own file in `config/prompts/`:

```
config/prompts/
  01_default.md
  02_executive_brief.md
  03_action_checklist.md
  04_decisions_options.md
  05_tldr_5_things.md
  06_skeptics_review.md
  07_fact_vs_opinion.md
  08_glossary.md
  09_outline_timestamps.md
  10_quote_bank.md
  11_role_based.md
```

Files are loaded in filename order. The numeric prefix controls the order prompts appear in emails.

### File format

Each file contains:

```markdown
# key_name

enabled: true/false
label: Human-readable label

## short
```prompt
... prompt for short videos ...
{transcript}
```

## medium
```prompt
... prompt for medium videos ...
{transcript}
```

## long
```prompt
... prompt for long videos ...
{transcript}
```
```

### Length-adaptive tiers

Before running any prompt, the transcript length is measured and a tier is selected:

| Tier | Transcript chars | Approx duration | Body words | Bullets | Wrap-up |
|---|---|---|---|---|---|
| short | < 8,000 | < ~9 min | ~100 | 3 | 1 sentence |
| medium | 8,000–22,000 | ~9–25 min | ~200 | 5 | 1–2 sentences |
| long | > 22,000 | ~25+ min | ~300 | 8 | 2–3 sentences |

The correct template variant is selected automatically — no manual configuration needed.

### Output repair

After summarization, the default prompt output is validated:
- Must contain a `Key takeaways` section with the expected number of bullets.
- If malformed, a repair pass re-runs the summary through Ollama with explicit format instructions.
- `_ensure_key_takeaways()` in `run.py` handles this.

---

## Transcript pipeline

Transcription always uses **Parakeet MLX** (local, Apple Silicon). The YouTube transcript API is not used.

### Audio download

`yt-dlp` downloads audio-only (smallest available stream). Cookies from the browser (`YTS_YTDLP_COOKIES_FROM_BROWSER`) can be passed to avoid bot detection.

### Transcription

Parakeet (`mlx-community/parakeet-tdt-0.6b-v3` by default) runs on-device. Audio files are cached in `data/audio/` and cleaned up after `YTS_AUDIO_RETENTION_DAYS` (default: 7).

---

## Transcript cleanup (transcribe mode)

When a source is in **transcribe mode**, the raw Parakeet output goes through deterministic cleanup before emailing. No LLM is involved by default (optional AI cleanup can be enabled via `YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`).

### Cleanup options (configured in `config/transcribe.md`)

| Option | What it does |
|---|---|
| `remove_fillers` | Strips um, uh, kind of, you know, sort of, I mean; removes double-word stutters; capitalises after filler removal |
| `questions_own_paragraph` | Forces a blank line before/after lines ending in `?` |
| `robust_sentence_breaks` | Adds paragraph breaks at sentence boundaries (~1,000 char chunks) |
| `qa_paragraph_breaks` | Detects "First question", "[Name] writes," patterns and forces breaks |
| `split_long_clauses` | Splits compound sentences at `, and` / `, but` when both clauses are substantial |
| `strip_stage_directions` | Removes `[music]`, `[applause]`, etc. |
| `normalize_numbers` | Converts spoken numbers to digits (off by default) |
| `speaker_labels` | Attempts speaker labels (high hallucination risk, off by default) |

---

## Email rendering

Summary text (paragraphs + `- ` bullets) is converted to HTML by `_format_summary_html()` in `run.py`:

- Blank-line-separated chunks → `<p>` tags
- `- ` or `* ` lines → `<ul><li>` list
- `Key takeaways` line → small uppercase section header
- Text after the bullet block → `<p>` wrap-up paragraph

Each enabled prompt produces one labeled card in the email. Cards are separated by a thin divider.

---

## State tracking

SQLite database at `data/state.db`:

| Table | Purpose |
|---|---|
| `seen_videos` | One row per processed video id; prevents duplicate sends |
| `bootstrapped_channels` | One row per subscription URL; marks that historical videos have been skipped |

---

## Key files

### Orchestration

- `youtube_summarizer/run.py` — main loop: loads config, iterates sources, drives transcript + summarize + email pipeline
- `youtube_summarizer/__main__.py` — CLI entry point (`run` and `watch` subcommands, `--dry-run`, `--debug`)

### Config loading

- `youtube_summarizer/config.py` — parses `channels.toml`, `config/prompts/*.md`, `transcribe.md`, `.env`

### Data fetching

- `youtube_summarizer/youtube.py` — RSS feed fetch + parse; yt-dlp playlist enumeration fallback

### Summarization

- `youtube_summarizer/summarizer.py` — calls `ollama run`; `cleanup_summary()` strips markdown artefacts

### Transcription

- `youtube_summarizer/transcriber.py` — Parakeet MLX and whisper.cpp backends

### Email

- `youtube_summarizer/emailer.py` — Gmail SMTP send
- `youtube_summarizer/templates/email.html.j2` — Jinja2 HTML template

### Database

- `youtube_summarizer/db.py` — `seen_videos` + `bootstrapped_channels` helpers

### Management scripts

- `scripts/manage.sh` — interactive TUI (requires `gum`) for setup and management
- `scripts/_config.py` — Python helper for all `channels.toml` / `transcribe.md` read/write operations

---

## Running

```bash
# Once
python -m youtube_summarizer run [--dry-run] [--limit N] [--debug]

# Continuous polling (used by launchd)
python -m youtube_summarizer watch [--poll-seconds 900] [--limit 10]
```

### launchd service

`~/Library/LaunchAgents/com.youtube-summarizer.plist` — runs `watch` at login, polls every 15 minutes.

Logs: `/tmp/youtube-summarizer.out.log`, `/tmp/youtube-summarizer.err.log`

---

## What's intentionally not here

- A hosted server or API (this is a local Mac app)
- A cloud summarization provider (Ollama is local)
- YouTube Data API (RSS avoids API keys entirely)
- Multi-user support
