# Claude Code Instructions

This repo is a local macOS app. Keep it simple, local-first, and easy to maintain.

---

## Principles

- Simple to install on macOS
- Built on existing tools (yt-dlp, ffmpeg, Parakeet, Ollama)
- No API keys required for YouTube (uses RSS)
- Transcript-first: always use Parakeet for transcription (YouTube transcript API is disabled)

---

## Prompt system

Prompt templates live in `config/prompts/` — one `.md` file per prompt.

Each file has three variants: `## short`, `## medium`, `## long`.
The correct variant is selected automatically based on transcript length:

| Tier | Transcript chars | Approx duration |
|---|---|---|
| short | < 8,000 | < ~9 min |
| medium | 8,000–22,000 | ~9–25 min |
| long | > 22,000 | ~25+ min |

Every prompt template must include `{transcript}`.

**To add a new prompt:**
1. Create `config/prompts/NN_key_name.md` following the existing file format.
2. Set `enabled: true` or `false`.
3. No code changes needed — the loader picks it up automatically.

See `config/prompts/README.md` for the full authoring guide.

**Key rules when writing prompts for qwen2.5:14b:**
- Open every prompt with: `Output ONLY ... — no preamble, no "Here is...", no sign-off. Begin your response with the first word of the actual content.`
- Show the exact output shape as a concrete template, not just rules in prose
- Use "exactly N" for counts (not "N–M ranges" when precision matters)
- End every prompt with: `Stop after [last element]. Do not add anything else.`
- Name section labels explicitly so the model outputs the right text

---

## Channel config

`config/channels.toml` — three sections:

```toml
[[subscriptions]]
name    = "Channel Name"
url     = "https://www.youtube.com/channel/UCxxx"
prompts = ["default", "glossary"]   # optional; omit to run all enabled prompts

[summarize_queue]
name    = "My Summarize Playlist"
url     = "https://www.youtube.com/playlist?list=PLxxx"
prompts = ["default"]

[transcribe_queue]
name    = "My Transcribe Playlist"
url     = "https://www.youtube.com/playlist?list=PLxxx"
```

`prompts` is a list of prompt keys. Omit it to run all enabled prompts.
Do not use the old `prompt = "default"` single-string form.

---

## Email formatting

When changing email layout, optimise for:
- Fast scanning (headline → thumbnail → summary → link)
- Clean typography, intentional hierarchy, no visual clutter
- Works well in Gmail (supports `<style>` blocks; no CSS Grid/Flexbox needed)

The HTML template is `youtube_summarizer/templates/email.html.j2`.
Summary text is converted to HTML by `_format_summary_html()` in `run.py`.
Thumbnail URL is deterministic: `https://img.youtube.com/vi/{video_id}/hqdefault.jpg`.

---

## Config loading

`youtube_summarizer/config.py` is the single source of truth for all config parsing:
- `load_channels()` — parses `channels.toml`
- `load_process_prompts()` — reads from `config/prompts/` directory
- `load_transcribe_prompts()` / `load_transcribe_options()` — reads `config/transcribe.md`
- `load_settings()` — reads environment variables

---

## Management scripts

`scripts/manage.sh` — gum-based TUI for setup and management. Also reachable as `./manage.sh` (root symlink).
`scripts/_config.py` — Python CLI for all TOML mutations (called by `manage.sh`).

Do not add direct TOML manipulation to the bash script; route all writes through `_config.py`.

---

## Versioning

This project uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`):

| Change type | Bump |
|---|---|
| Breaking change to config format or CLI | `MAJOR` |
| New feature (backward-compatible) | `MINOR` |
| Bug fix, docs, refactor, chore | `PATCH` |

**After every meaningful change**, tag and push:

```bash
git tag -a v1.2.3 -m "Release v1.2.3: short description"
git push origin v1.2.3
```

---

## Changelog

**Update `CHANGELOG.md` with every commit that changes behaviour.**
Docs-only or chore commits can be grouped, but any feature, fix, or breaking change gets an entry.

Format:

```markdown
## [1.2.3] — YYYY-MM-DD

### Added / Changed / Fixed / Removed
- Short description
```

Add a `[x.y.z]: <github compare URL>` link at the bottom for each new version.

---

## Commit discipline

- Commit after every logical unit of work — don't batch unrelated changes.
- Push after every commit (or at the end of a session at minimum).
- Use conventional prefixes: `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Security:`
- Always end commit messages with:
  ```
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```

---

## What NOT to commit

- `.env` — real credentials, always gitignored
- `data/` — SQLite state database, always gitignored
- `.claude/` — local Claude Code settings, always gitignored
- Personal YouTube channel/playlist URLs in `config/channels.toml` — use placeholders in the tracked file
- Hardcoded project paths in `launchd/com.youtube-summarizer.plist` — use `__PROJECT_PATH__` placeholder; SETUP.md has the `sed` install command

---

## Key files

| File | Purpose |
|---|---|
| `youtube_summarizer/run.py` | Main pipeline — fetch, transcribe, summarize, email |
| `youtube_summarizer/config.py` | All config parsing (single source of truth) |
| `youtube_summarizer/templates/email.html.j2` | HTML email template |
| `config/channels.toml` | Sources and per-feed prompt overrides |
| `config/prompts/*.md` | One file per prompt, three tier variants each |
| `config/transcribe.md` | Transcript cleanup options |
| `scripts/manage.sh` | gum-based TUI for setup and management |
| `scripts/_config.py` | Python CLI for TOML read/write (called by manage.sh) |
| `CHANGELOG.md` | Version history — update with every release |
