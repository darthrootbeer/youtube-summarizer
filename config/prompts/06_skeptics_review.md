# skeptics_review

enabled: false
label: Skeptic's review (what's missing / questionable)

## short

```prompt
Write a skeptical review of the transcript.

Rules:
- Section "Strong points" with 2–3 "- " bullets
- Section "Weak points / missing evidence" with 2–3 "- " bullets
- End with "What would change my mind" and exactly 2 "- " bullets
- Keep it constructive, not snarky
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Write a skeptical review of the transcript.

Rules:
- Section "Strong points" with 3–5 "- " bullets
- Section "Weak points / missing evidence" with 3–5 "- " bullets
- End with "What would change my mind" and exactly 3 "- " bullets
- Keep it constructive, not snarky
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Write a skeptical review of the transcript.

Rules:
- Section "Strong points" with 5–7 "- " bullets
- Section "Weak points / missing evidence" with 5–7 "- " bullets
- End with "What would change my mind" and exactly 4 "- " bullets
- Keep it constructive, not snarky
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```
