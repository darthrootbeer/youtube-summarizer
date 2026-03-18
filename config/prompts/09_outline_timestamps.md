# outline_timestamps

enabled: false
label: Structured outline

## short

```prompt
Output ONLY a structured outline — no preamble, no "Here is...", no sign-off. Begin with the first entry.

Rules:
- Exactly 3–5 sections that represent the major topic shifts in the transcript
- Format each entry on its own line as: [MM:SS] Title — one sentence summary of what is covered
- If no timestamp can be inferred from the transcript, use [-] instead
- Title: 2–5 words, specific enough to distinguish this section from others
- Summary sentence: state the key point made in that section — not just the topic
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
- Exactly 6–10 sections that represent the major topic shifts in the transcript
- Format each entry on its own line as: [MM:SS] Title — one sentence summary of what is covered
- If no timestamp can be inferred from the transcript, use [-] instead
- Title: 2–5 words, specific enough to distinguish this section from others
- Summary sentence: state the key point or finding in that section — not just the topic
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
- Exactly 10–16 sections that represent the major topic shifts in the transcript
- Format each entry on its own line as: [MM:SS] Title — one sentence summary of what is covered
- If no timestamp can be inferred from the transcript, use [-] instead
- Title: 2–5 words, specific enough to distinguish this section from others
- Summary sentence: state the key point or finding in that section — not just the topic
- No markdown headers, no bold, no sub-bullets

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
