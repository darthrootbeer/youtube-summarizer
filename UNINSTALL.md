# Uninstall (macOS)

## Remove the app folder

- Delete the project folder you cloned (example: `~/projects/youtube-summarizer`)

## Remove the scheduler (if you enabled it)

- Unload it (if loaded): `launchctl unload ~/Library/LaunchAgents/com.youtube-summarizer.plist`
- Delete the plist: `rm ~/Library/LaunchAgents/com.youtube-summarizer.plist`

## Optional: remove Homebrew tools

- `brew uninstall yt-dlp ffmpeg`

