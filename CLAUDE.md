# Claude Code Instructions

This repo is a local macOS app. Keep it simple, local-first, and easy to maintain.
See `AI_INSTRUCTIONS.md` for domain-specific guidelines (prompts, email, config).

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
# Create annotated tag
git tag -a v1.2.3 -m "Release v1.2.3: short description"
git push origin v1.2.3
```

---

## Changelog

**Update `CHANGELOG.md` with every commit that changes behaviour.**
Docs-only or chore commits can be grouped, but any feature, fix, or breaking change needs an entry.

Format:

```markdown
## [1.2.3] — YYYY-MM-DD

### Added
- Short description of new capability

### Changed
- What changed and why (if non-obvious)

### Fixed
- What was broken and how it was fixed

### Removed
- What was removed and why
```

Add a `[x.y.z]: <github compare URL>` link at the bottom of the file for each new version.

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

## What NOT to do

- Do not edit `config/channels.toml` directly with personal URLs — it is tracked by git.
  Personal channel/playlist URLs go in the user's local copy only.
- Do not commit `.env` — it is in `.gitignore` and contains real credentials.
- Do not commit `data/` — it is in `.gitignore` and contains the SQLite state database.
- Do not commit `.claude/` — it is in `.gitignore` and may contain local Claude settings.
- Do not add the hardcoded project path to `launchd/com.youtube-summarizer.plist` —
  it uses `__PROJECT_PATH__` as a placeholder; SETUP.md instructs users to substitute it with `sed`.

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
