# outline_timestamps

enabled: false
label: Structured outline with timestamps

## short

```prompt
Output ONLY a structured outline — no preamble, no "Here is...", no sign-off. Begin with the first entry.

Rules:
- 3–5 sections max
- Format each entry on its own line as: [MM:SS] Title — one sentence summary
- If no timestamp can be inferred, use [-] instead
- No markdown headers, no bold, no sub-bullets

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY a structured outline — no preamble, no "Here is...", no sign-off. Begin with the first entry.

Rules:
- 6–10 sections max
- Format each entry on its own line as: [MM:SS] Title — one sentence summary
- If no timestamp can be inferred, use [-] instead
- No markdown headers, no bold, no sub-bullets

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY a structured outline — no preamble, no "Here is...", no sign-off. Begin with the first entry.

Rules:
- 10–16 sections max
- Format each entry on its own line as: [MM:SS] Title — one sentence summary
- If no timestamp can be inferred, use [-] instead
- No markdown headers, no bold, no sub-bullets

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
