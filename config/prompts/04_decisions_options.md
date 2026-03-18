# decisions_options

enabled: false
label: Key decisions + options

## short

```prompt
Extract the key decisions implied by the transcript.

Output:
- 2–3 decisions max
- For each: decision, 2 options, tradeoffs, recommendation
- Use plain language and be concise
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Extract the key decisions implied by the transcript.

Output:
- 3–5 decisions max
- For each: decision, 2–3 options, tradeoffs, recommendation
- Use plain language and be concise
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Extract the key decisions implied by the transcript.

Output:
- 5–8 decisions max
- For each: decision, 2–3 options, tradeoffs, recommendation
- Use plain language and be concise
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```
