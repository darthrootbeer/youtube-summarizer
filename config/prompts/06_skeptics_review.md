# skeptics_review

enabled: false
label: Skeptic's review (what's missing / questionable)

## short

```prompt
Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <point>
- <point>

Weak points / missing evidence
- <point>
- <point>

What would change my mind
- <point>
- <point>

Rules:
- "Strong points": 2–3 bullets
- "Weak points / missing evidence": 2–3 bullets
- "What would change my mind": exactly 2 bullets
- Each section label on its own line, followed by "- " bullets
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <point>
...

Weak points / missing evidence
- <point>
...

What would change my mind
- <point>
- <point>
- <point>

Rules:
- "Strong points": 3–5 bullets
- "Weak points / missing evidence": 3–5 bullets
- "What would change my mind": exactly 3 bullets
- Each section label on its own line, followed by "- " bullets
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <point>
...

Weak points / missing evidence
- <point>
...

What would change my mind
- <point>
- <point>
- <point>
- <point>

Rules:
- "Strong points": 5–7 bullets
- "Weak points / missing evidence": 5–7 bullets
- "What would change my mind": exactly 4 bullets
- Each section label on its own line, followed by "- " bullets
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
