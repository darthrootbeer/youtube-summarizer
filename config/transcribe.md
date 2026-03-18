# Transcribe mode (cleanup prompt)

This file controls transcript cleanup behavior used by `mode = "transcribe"` sources.

Default behavior is **non-AI cleanup** (safer for accuracy).  
If you enable AI cleanup (`YTS_TRANSCRIPT_CLEAN_WITH_OLLAMA=1`), the enabled prompt below is used.

## Cleanup options (deterministic, recommended)

These options apply even when AI cleanup is OFF.

- `remove_fillers`: remove common fillers (“um”, “uh”, “er”, “ah”) and clean up obvious stutters
- `questions_own_paragraph`: add a blank line before and after questions (good for interviews / Q&A)
- `robust_sentence_breaks`: add more paragraph breaks for long run-on text *without changing wording*

### Current settings

remove_fillers: true  
questions_own_paragraph: true  
robust_sentence_breaks: true  

---

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

---

## Extra options (off by default)

These are included for future experimentation:

- `strip_stage_directions`: remove bracketed artifacts like “[music]”, “[applause]”
- `normalize_numbers`: normalize “twenty one” ↔ “21” (can reduce accuracy if overdone)
- `speaker_labels`: attempt to add “Speaker 1 / Speaker 2” (high risk of hallucination)

strip_stage_directions: false  
normalize_numbers: false  
speaker_labels: false  

