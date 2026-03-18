# quote_bank

enabled: false
label: Quote bank

## short

```prompt
Output ONLY shareable quotes from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Short quotes
- <striking, specific statement under 200 characters — direct quote or minimal rewrite>
- <striking, specific statement under 200 characters>
- <striking, specific statement under 200 characters>

Pull quotes
- <1–2 sentence statement worth highlighting — a strong claim, insight, or counterintuitive point>
- <1–2 sentence statement worth highlighting>

Rules:
- "Short quotes": exactly 3 items
- "Pull quotes": exactly 2 items
- Each section label on its own line, followed by "- " bullets
- Prioritise the bold, counterintuitive, or memorable over the safe and obvious
- Do not invent quotes — use words actually in the transcript, lightly edited only for grammar
- No markdown headers, no bold

Stop after the last pull quote. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY shareable quotes from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Short quotes
- <striking, specific statement under 200 characters — direct quote or minimal rewrite>
...

Pull quotes
- <1–2 sentence statement worth highlighting — a strong claim, insight, or counterintuitive point>
...

Rules:
- "Short quotes": exactly 5 items
- "Pull quotes": exactly 3 items
- Each section label on its own line, followed by "- " bullets
- Prioritise the bold, counterintuitive, or memorable over the safe and obvious
- Do not invent quotes — use words actually in the transcript, lightly edited only for grammar
- No markdown headers, no bold

Stop after the last pull quote. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY shareable quotes from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Short quotes
- <striking, specific statement under 200 characters — direct quote or minimal rewrite>
...

Pull quotes
- <1–2 sentence statement worth highlighting — a strong claim, insight, or counterintuitive point>
...

Rules:
- "Short quotes": exactly 8 items
- "Pull quotes": exactly 5 items
- Each section label on its own line, followed by "- " bullets
- Prioritise the bold, counterintuitive, or memorable over the safe and obvious
- Do not invent quotes — use words actually in the transcript, lightly edited only for grammar
- No markdown headers, no bold

Stop after the last pull quote. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
