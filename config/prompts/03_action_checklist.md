# action_checklist

enabled: false
label: Action checklist

## short

```prompt
Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Maximum 8 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 1–2 sections using plain text labels ending with ":" on their own line (e.g. "This week:")
- No numbered lists, no markdown headers, no bold
- No repeated advice across items

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Maximum 15 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 2–4 sections using plain text labels ending with ":" on their own line (e.g. "This week:", "This month:")
- No numbered lists, no markdown headers, no bold
- No repeated advice across items

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Maximum 25 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 3–6 sections using plain text labels ending with ":" on their own line (e.g. "This week:", "This month:", "Long term:")
- No numbered lists, no markdown headers, no bold
- No repeated advice across items

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
