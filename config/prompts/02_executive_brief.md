# executive_brief

enabled: false
label: Executive brief (5-minute read)

## short

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first sentence of the brief.

Write 80–100 words total. Summarize ideas as standalone statements (no mention of speaker, presenter, or "this video"). No bold, no markdown headers, no "Conclusion" or "Summary" label.

Structure:
- Open with 1–3 sentences of context
- Then output the exact line "Why it matters:" followed immediately (on the same line) by one sentence
- Then output the exact line "Next actions"
- Then exactly 2 bullets using "- "

Stop after the second bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first sentence of the brief.

Write 120–180 words total. Summarize ideas as standalone statements (no mention of speaker, presenter, or "this video"). No bold, no markdown headers, no "Conclusion" or "Summary" label.

Structure:
- Open with 1–2 short paragraphs of context
- Then output the exact line "Why it matters" on its own line
- Then one short paragraph explaining why this matters
- Then output the exact line "Next actions"
- Then exactly 3 bullets using "- "

Stop after the third bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first sentence of the brief.

Write 200–250 words total. Summarize ideas as standalone statements (no mention of speaker, presenter, or "this video"). No bold, no markdown headers, no "Conclusion" or "Summary" label.

Structure:
- Open with 2–3 short paragraphs of context
- Then output the exact line "Why it matters" on its own line
- Then two short paragraphs explaining why this matters
- Then output the exact line "Next actions"
- Then exactly 5 bullets using "- "

Stop after the fifth bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
