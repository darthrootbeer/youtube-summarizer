# TODO

## Done
- [x] Channel monitoring via YouTube RSS (no API keys)
- [x] Seen-video tracking via SQLite (`data/state.db`)
- [x] Gmail sending via SMTP + App Password
- [x] macOS launchd scheduler
- [x] Parakeet v3 transcription fallback (parakeet-mlx) + ffmpeg
- [x] Ollama-based summarization
- [x] Playlist queue support (summarize + transcribe playlists)
- [x] Bootstrap guard: subscriptions skip historical videos, only process new ones going forward
- [x] Three-section config: subscriptions / summarize queue / transcribe queue
- [x] Per-source prompt routing: `[SUB]` → all enabled process.md prompts; `[SUMMARY]` → default only; `[TRANSCRIPTION]` → transcribe.md
- [x] Email header: source label + tag, published date, video URL visible

## Backlog
- [ ] Thumbnail in email header
- [ ] Install/uninstall docs for a fresh Mac
- [ ] Re-check yt-dlp n-challenge issue once upstream fixes land (see PROJECT_STATUS.md)
