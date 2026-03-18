# executive_brief

enabled: true
label: Executive brief (5-minute read)

## short

```prompt
Create a concise executive brief for a busy reader.

Rules:
- 80–100 words total
- Do not mention the speaker, presenter, or "this video" — summarize ideas as standalone statements
- No bold/italics markers, no markdown headers, no "Conclusion"
- Output must be English
- One sentence "Why it matters:" followed by the sentence on the same line
- End with a line that says exactly: "Next actions"
- Then exactly 2 bullets (use "- " bullets)
- Do not include "Key Points", "[End ...]", or any bracketed sign-offs

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Create an executive brief for a busy reader.

Rules:
- 120–180 words total
- Do not mention the speaker, presenter, or "this video" — summarize ideas as standalone statements
- No bold/italics markers, no markdown headers, no "Conclusion"
- Output must be English
- One short "Why it matters" paragraph
- End with a line that says exactly: "Next actions"
- Then exactly 3 bullets (use "- " bullets)
- Do not include "Key Points", "[End ...]", or any bracketed sign-offs

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Create a thorough executive brief for a busy reader.

Rules:
- 200–250 words total
- Do not mention the speaker, presenter, or "this video" — summarize ideas as standalone statements
- No bold/italics markers, no markdown headers, no "Conclusion"
- Output must be English
- Two short "Why it matters" paragraphs
- End with a line that says exactly: "Next actions"
- Then exactly 5 bullets (use "- " bullets)
- Do not include "Key Points", "[End ...]", or any bracketed sign-offs

Transcript:
"""
{transcript}
"""
```
