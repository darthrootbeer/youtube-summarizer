# Project Status

**State:** Initial scaffold working locally (transcript-first via YouTube; MacWhisper fallback is pluggable).

## What’s in place

- Channel monitoring via YouTube RSS (no API keys)
- “Seen videos” tracking via SQLite (`data/state.db`)
- Gmail sending via SMTP + App Password
- Manual run command: `python -m youtube_summarizer run`
- macOS scheduler template: `launchd/com.youtube-summarizer.plist`

## Next key decision

- Define the summarization approach and quality bar (tone, length, structure)

