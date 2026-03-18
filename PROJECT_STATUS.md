# Project Status

**State:** Initial scaffold working locally (transcript-first via YouTube; MacWhisper fallback is pluggable). YouTube `yt-dlp` metadata/channel detection is currently blocked by upstream EJS “n challenge” issues.

## What’s in place

- Channel monitoring via YouTube RSS (no API keys)
- “Seen videos” tracking via SQLite (`data/state.db`)
- Gmail sending via SMTP + App Password
- Manual run command: `python -m youtube_summarizer run`
- macOS scheduler template: `launchd/com.youtube-summarizer.plist`

## Known integration issue (yt-dlp / YouTube)

- `yt-dlp` with EJS (external JS runtime) is failing `n challenge` solving on at least some videos, even when cookies are passed from a logged-in browser.
- Symptoms:
  - Commands like `yt-dlp --cookies-from-browser chrome --print channel_id "https://www.youtube.com/watch?v=QT7W_uHjqWE"` warn about Deno provider errors and “n challenge solving failed”.
  - yt-dlp falls back to “Only images are available for download” and then errors with “Requested format is not available”.
- Environment:
  - macOS 14 (Darwin 24.6.0)
  - `yt-dlp` installed via Homebrew (see `brew list --versions yt-dlp` for exact version)
  - Node.js present (`node -v` -> v25.8.1), but yt-dlp is still preferring the Deno provider and failing inside `$deno$stdin.js`.
- Attempts so far:
  - Verified video plays normally when logged-in in both Safari and Chrome.
  - Switched to Chrome cookies via `--cookies-from-browser chrome`.
  - Tried to force Node provider; env var `YT_DLP_JS_PROVIDER=node` had no effect (provider still logged as `"deno"`).
  - Using `--print channel_id` still hits the formats error; likely metadata extraction is currently coupled to successful challenge solving for this player.
- Next steps for a future pass:
  - Re-check once upstream yt-dlp / EJS issues around Deno provider and “n challenge” are resolved.
  - Revisit using `--js-runtimes` or config-based JS runtime selection to force Node or another supported runtime once the recommended pattern stabilizes.
  - Explore `--ignore-no-formats-error --skip-download` plus `--print channel_id` / `-j` to see if pure-metadata paths can bypass format availability entirely once the challenge bug is fixed.

## Next key decision

- Define the summarization approach and quality bar (tone, length, structure)

