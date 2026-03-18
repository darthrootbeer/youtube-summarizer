# Transcribe mode (cleanup prompt)

This file controls the **optional AI cleanup** step used by `mode = "transcribe"` sources.

Default behavior is **non-AI cleanup** (safer for accuracy).  
If you enable AI cleanup (`YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`), the enabled prompt below is used.

## How it works

- Each section below is a prompt template.
- Set `enabled: true` to turn it on.
- `{transcript}` is required.

## Prompts

### clean_readable

enabled: true  
label: Clean transcript (readable, no summarizing)

```prompt
Clean up this transcript for reading.

Hard rules:
- Do NOT summarize, shorten, or paraphrase. Keep the same meaning and as much wording as possible.
- Fix obvious punctuation and capitalization.
- Add paragraph breaks to improve readability.
- Do not add headings, bullet lists, or commentary.
- Output must be English.

Transcript:
"""
{transcript}
"""
```

