# outline_timestamps

enabled: false
label: Structured outline with timestamps

## short

```prompt
Create a structured outline with timestamps if they appear or can be inferred.

Rules:
- 3–5 sections max
- Each section: timestamp (or "-"), title, 1 sentence summary
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Create a structured outline with timestamps if they appear or can be inferred.

Rules:
- 6–10 sections max
- Each section: timestamp (or "-"), title, 1 sentence summary
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Create a detailed structured outline with timestamps if they appear or can be inferred.

Rules:
- 10–16 sections max
- Each section: timestamp (or "-"), title, 1 sentence summary
- No markdown headers, no bold

Transcript:
"""
{transcript}
"""
```
