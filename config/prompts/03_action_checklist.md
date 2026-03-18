# action_checklist

enabled: true
label: Action checklist

## short

```prompt
Turn this transcript into a short action checklist someone could follow.

Rules:
- Maximum 8 action items total
- Each item must start with "- ☐ " (dash, space, checkbox, space)
- Group into 1–2 short sections using plain text labels ending with ":" (e.g. "This week:")
- Avoid repeating the same advice in multiple items
- No numbered lists, no markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Turn this transcript into an action checklist someone could follow.

Rules:
- Maximum 15 action items total
- Each item must start with "- ☐ " (dash, space, checkbox, space)
- Group into 2–4 short sections using plain text labels ending with ":" (e.g. "This week:")
- Avoid repeating the same advice in multiple items
- No numbered lists, no markdown headers, no bold

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Turn this transcript into a comprehensive action checklist someone could follow.

Rules:
- Maximum 25 action items total
- Each item must start with "- ☐ " (dash, space, checkbox, space)
- Group into 3–6 short sections using plain text labels ending with ":" (e.g. "This week:", "Long term:")
- Avoid repeating the same advice in multiple items
- No numbered lists, no markdown headers, no bold

Transcript:
"""
{transcript}
"""
```
