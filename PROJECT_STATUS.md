# Project Status

**State:** Fully operational. Running as a macOS launchd service, polling every 15 minutes.

## What's in place

### Source routing (`config/channels.toml`)
Three distinct source types, each with its own behaviour and prompt:

| Section | Behaviour | Prompt |
|---|---|---|
| `[[subscriptions]]` | New videos only (bootstrap on first run) | `config/process.md` — all enabled prompts |
| `[summarize_queue]` | Drain playlist to empty | `config/process.md` — `default` prompt only |
| `[transcribe_queue]` | Drain playlist to empty | `config/transcribe.md` — clean transcript, no summarizing |

### Email subjects
- `[YT Summary] [SUB] Channel Name — Video Title`
- `[YT Summary] [SUMMARY] Playlist Name — Video Title`
- `[YT Summary] [TRANSCRIPTION] Playlist Name — Video Title`

### Email content (all videos)
- Source label + channel/playlist name
- Video title
- Published date & time (UTC)
- Video URL (plain text + link)
- Content sections (summary or transcript)
- Transcript source + beta stats

### Prompts (`config/process.md`)
Three prompts currently enabled for subscriptions:
- `default` — 200 word summary + 3 key takeaways
- `executive_brief` — 120–180 word brief + Next actions
- `action_checklist` — grouped bullet checklist

Summarize queue uses only `default`.

### Transcribe prompt (`config/transcribe.md`)
- Deterministic cleanup (remove fillers, fix punctuation, paragraph breaks) — always runs
- Optional Ollama-based cleanup — set `YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`

### Bootstrap guard
On the first run for any subscription channel, all current RSS videos (up to 30) are silently
marked as seen without emailing. Only videos published after that point are processed.
Queue playlists are NOT bootstrapped — they are always drained to empty.

## Known issue (yt-dlp / YouTube)

- `yt-dlp` may fail with "n challenge" errors on some videos even with browser cookies.
- Symptom: Deno provider errors → "Requested format is not available".
- Workaround: `YTS_YTDLP_COOKIES_FROM_BROWSER=chrome` (set in `.env`).
- Next step: re-check once upstream yt-dlp / EJS fixes land.

## Infrastructure

- Scheduler: `~/Library/LaunchAgents/com.youtube-summarizer.plist` (runs at login, polls every 15 min)
- State DB: `data/state.db` (SQLite — seen videos + bootstrapped channels)
- Logs: `/tmp/youtube-summarizer.out.log` and `/tmp/youtube-summarizer.err.log`
- Reload: `launchctl unload/load ~/Library/LaunchAgents/com.youtube-summarizer.plist`
