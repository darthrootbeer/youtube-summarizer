# Uninstall (macOS)

## 1. Stop and remove the scheduler

```bash
launchctl unload ~/Library/LaunchAgents/com.youtube-summarizer.plist
rm ~/Library/LaunchAgents/com.youtube-summarizer.plist
```

## 2. Delete the project folder

```bash
rm -rf ~/projects/youtube-summarizer   # adjust path if different
```

This removes everything: code, config, SQLite database, audio cache, and virtual environment.

## 3. (Optional) Remove Homebrew tools

Only if you don't use these elsewhere:

```bash
brew uninstall yt-dlp ffmpeg gum
brew uninstall ollama   # if you installed it for this project
```

## 4. (Optional) Remove Ollama models

```bash
ollama rm qwen2.5:14b   # or whichever model you pulled
```

## 5. (Optional) Revoke the Gmail App Password

Go to `https://myaccount.google.com/apppasswords` and delete the password you created for this app.
