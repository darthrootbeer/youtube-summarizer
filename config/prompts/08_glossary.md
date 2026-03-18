# glossary

enabled: false
label: Glossary

## short

```prompt
Output ONLY a glossary — no preamble, no "Here is...", no sign-off. Begin with the first term.

Rules:
- Exactly 3–5 terms used in the transcript that a newcomer to this topic might not know
- Prioritise terms that are specific to this content — not generic technical words any dictionary would cover
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences — explain what it means AND why it matters in this specific context
- No intro sentence, no conclusion, no section headers, no bold

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY a glossary — no preamble, no "Here is...", no sign-off. Begin with the first term.

Rules:
- Exactly 5–8 terms used in the transcript that a newcomer to this topic might not know
- Prioritise terms that are specific to this content — not generic technical words any dictionary would cover
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences — explain what it means AND why it matters in this specific context
- Include any named tools, frameworks, people, or proprietary concepts that appear
- No intro sentence, no conclusion, no section headers, no bold

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY a glossary — no preamble, no "Here is...", no sign-off. Begin with the first term.

Rules:
- Exactly 8–14 terms used in the transcript that a newcomer to this topic might not know
- Prioritise terms that are specific to this content — not generic technical words any dictionary would cover
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences — explain what it means AND why it matters in this specific context
- Include named tools, frameworks, people, organisations, or proprietary concepts that appear
- Order alphabetically
- No intro sentence, no conclusion, no section headers, no bold

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
