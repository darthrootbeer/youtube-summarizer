# quote_bank

enabled: false
label: Quote bank + shareables

## short

```prompt
Output ONLY shareable quotes from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Short quotes
- <tweet-length quote, under 280 characters>
- <tweet-length quote, under 280 characters>
- <tweet-length quote, under 280 characters>

Pull quotes
- <1–2 sentence pull quote>
- <1–2 sentence pull quote>

Rules:
- "Short quotes": exactly 3 items
- "Pull quotes": exactly 2 items
- Each section label on its own line, followed by "- " bullets
- Do not invent quotes — only lightly rewrite for clarity
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
- <tweet-length quote, under 280 characters>
...

Pull quotes
- <1–2 sentence pull quote>
...

Rules:
- "Short quotes": exactly 5 items
- "Pull quotes": exactly 3 items
- Each section label on its own line, followed by "- " bullets
- Do not invent quotes — only lightly rewrite for clarity
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
- <tweet-length quote, under 280 characters>
...

Pull quotes
- <1–2 sentence pull quote>
...

Rules:
- "Short quotes": exactly 8 items
- "Pull quotes": exactly 5 items
- Each section label on its own line, followed by "- " bullets
- Do not invent quotes — only lightly rewrite for clarity
- No markdown headers, no bold

Stop after the last pull quote. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
