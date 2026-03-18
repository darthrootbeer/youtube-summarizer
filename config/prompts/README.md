# Custom Prompts

Each file in this directory is one prompt. The app picks them up automatically — no code changes needed.

---

## File naming

```
NN_key_name.md
```

- `NN` — two-digit number that controls sort order (01, 02, … 11)
- `key_name` — the prompt's key, used in `channels.toml` to reference it

Examples: `01_default.md`, `08_glossary.md`, `12_my_custom.md`

---

## File format

Every prompt file follows the same structure:

```
# key_name

enabled: true
label: Human-readable label shown in the email

## short

```prompt
Your prompt text here. Must include {transcript}.
```

## medium

```prompt
Your prompt text here. Must include {transcript}.
```

## long

```prompt
Your prompt text here. Must include {transcript}.
```
```

### Fields

| Field | Required | Description |
|---|---|---|
| `enabled` | yes | `true` to run by default; `false` to opt-in only via `channels.toml` |
| `label` | yes | Section heading shown in the email |
| `## short / medium / long` | yes | Three tier variants (see below) |
| `{transcript}` | yes | Replaced with the video transcript at runtime |

---

## Tiers (short / medium / long)

The app automatically selects the right tier based on transcript length:

| Tier | Transcript length | Rough video length |
|---|---|---|
| `short` | < 8,000 characters | ~0–9 minutes |
| `medium` | 8,000–22,000 characters | ~9–25 minutes |
| `long` | > 22,000 characters | ~25+ minutes |

Write each tier to match the amount of content available:

- **short** — tight, distilled, fewest bullets / words
- **medium** — standard depth, balanced
- **long** — comprehensive, more bullets / words, covers more ground

If a tier is missing, the app falls back to `medium`, then to whatever tier exists.

---

## Writing prompts for qwen2.5:14b

The app uses Ollama locally. These techniques produce the most reliable output:

**1. Open with a hard output directive**
```
Output ONLY the requested content — no preamble, no "Here is...", no sign-off.
Begin your response with the first word of the actual content.
```

**2. Show the exact output shape, not just rules**

Instead of describing the format in prose, show it as a concrete template:
```
OUTPUT FORMAT:
<one sentence intro>

<prose paragraphs>

Key takeaways
- <takeaway>
- <takeaway>

<wrap-up sentence>
```

**3. Use "exactly N" for counts**

The model respects hard counts better than ranges when precision matters:
```
Then exactly 5 bullets starting with "- "
```

**4. Add a hard stop**
```
Stop immediately after the last bullet. Do not add anything else.
```

**5. Name section labels explicitly**

If your output has sections, tell the model the exact label text to use:
```
Output the exact line "Next actions" followed by exactly 3 "- " bullets.
```

---

## Enabling a prompt for all feeds

Set `enabled: true` in the file. It will run on every video that doesn't have an explicit `prompts` list in `channels.toml`.

---

## Enabling a prompt for one feed only

Set `enabled: false` in the file, then reference it by key in `channels.toml`:

```toml
[[subscriptions]]
name    = "My Channel"
url     = "https://www.youtube.com/channel/UCxxxxxx"
prompts = ["default", "glossary"]
```

Only the listed prompts run for that feed. All other feeds are unaffected.

---

## Complete worked example

`config/prompts/12_one_big_idea.md`:

```markdown
# one_big_idea

enabled: false
label: The one big idea

## short

```prompt
Output ONLY the following — no preamble, no sign-off. Begin with the first word.

In exactly 2–3 sentences, state the single most important idea from this transcript
in plain language a 12-year-old could understand.

Then output the exact line "Why it matters" followed by exactly 1 sentence.

Stop after that sentence. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the following — no preamble, no sign-off. Begin with the first word.

In exactly 1 short paragraph (4–6 sentences), state the single most important idea
from this transcript in plain language.

Then output the exact line "Why it matters" followed by exactly 2 sentences.

Then output the exact line "What to do" followed by exactly 2 "- " bullets.

Stop after the second bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the following — no preamble, no sign-off. Begin with the first word.

In exactly 2 short paragraphs, state the single most important idea from this
transcript and explain why it is significant.

Then output the exact line "Why it matters" followed by exactly 3 sentences.

Then output the exact line "What to do" followed by exactly 3 "- " bullets.

Stop after the third bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
```

To activate it for a specific channel:

```toml
[[subscriptions]]
name    = "Big Ideas Podcast"
url     = "https://www.youtube.com/channel/UCxxxxxx"
prompts = ["default", "one_big_idea"]
```

---

## Available variables

| Variable | Description |
|---|---|
| `{transcript}` | The cleaned video transcript (always required) |

Additional variables may be added in future. Check `youtube_summarizer/run.py` → `_summarize_video()` for the current list.
