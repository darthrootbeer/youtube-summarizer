# glossary

enabled: false
label: Glossary (plain English)

## short

```prompt
Output ONLY a glossary — no preamble, no "Here is...", no sign-off. Begin with the first term.

Rules:
- 3–5 terms from the transcript that a beginner might not know
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences, plain language, no jargon
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
- 5–8 terms from the transcript that a beginner might not know
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences, plain language, no jargon
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
- 8–12 terms from the transcript that a beginner might not know
- Format each entry as: "Term: definition" (one entry per line)
- Each definition: 1–2 sentences, plain language, no jargon
- No intro sentence, no conclusion, no section headers, no bold

Stop after the last entry. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
