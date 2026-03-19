# Transcribe mode (cleanup prompt)

This file controls transcript cleanup behavior for the transcript section of all emails.

## Cleanup options (deterministic pre-pass, always runs first)

- `remove_fillers`: remove common fillers ("um", "uh", "er", "ah", "kind of", "sort of", "you know", "I mean") and clean up obvious stutters
- `strip_stage_directions`: remove bracketed artifacts like "[music]", "[applause]", "[laughter]"
- `questions_own_paragraph`: add a blank line before and after questions
- `robust_sentence_breaks`: add more paragraph breaks for long run-on text
- `qa_paragraph_breaks`: detect Q&A intro patterns and force paragraph breaks before them
- `split_long_clauses`: split long sentences at natural clause boundaries

### Current settings

remove_fillers: true
strip_stage_directions: true
questions_own_paragraph: true
robust_sentence_breaks: true
qa_paragraph_breaks: true
split_long_clauses: true

---

## LLM cleanup prompt (always runs after deterministic pre-pass)

### clean_readable

enabled: true
label: Transcript

```prompt
Clean this transcript for reading. Output ONLY the cleaned transcript — no preamble, no commentary, no sign-off. Begin with the first word of the cleaned text.

Hard rules — never break these:
- Do NOT summarize, shorten, or cut content. Every spoken idea must remain.
- Do NOT add information not in the original transcript.
- Output must be in English.

What to fix:
- Add missing sentence-ending punctuation (periods, question marks) where the speaker clearly ended a thought
- Fix capitalization: "I", proper nouns (names of people, products, companies), acronyms (AI, API, LLM, GPU, etc.)
- Remove false starts and abandoned clauses (e.g. "I was going to — the point is" becomes "The point is")
- Remove double-word repetitions not already caught ("the the", "is is")
- Add paragraph breaks where the topic or speaker direction shifts — not just on sentence length
- If the content is long enough to have distinct topics, add a short descriptive section header (3–6 words, on its own line, followed by a blank line) where major topic shifts occur; if the content is very short, skip headers

Stop after the last word of the cleaned transcript. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
