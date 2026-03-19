# action_checklist

enabled: false
label: Action checklist

## short

```prompt
Output in English only. Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Exactly 6–8 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 1–2 sections using plain text labels ending with ":" on their own line (e.g. "This week:")
- Every action must be specific to this transcript — name the tool, technique, number, or concept involved
- No generic advice that could apply to any video on this topic (no "research further", "explore options", "consider your approach")
- Each action must be doable without rewatching — enough context to act on immediately
- No repeated advice across items. No markdown headers, no bold.

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Exactly 10–15 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 2–4 sections using plain text labels ending with ":" on their own line (e.g. "This week:", "This month:")
- Every action must be specific to this transcript — name the tool, technique, number, or concept involved
- No generic advice that could apply to any video on this topic
- Each action must be doable without rewatching — enough context to act on immediately
- Prioritise actions by when they should happen — immediate first, longer-term last
- No repeated advice across items. No markdown headers, no bold.

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY an action checklist — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Rules:
- Exactly 18–25 action items total
- Each item MUST start with exactly "- ☐ " (dash, space, the ☐ character, space) — copy that character exactly
- Group into 3–6 sections using plain text labels ending with ":" on their own line (e.g. "This week:", "This month:", "Long term:")
- Every action must be specific to this transcript — name the tool, technique, number, or concept involved
- No generic advice that could apply to any video on this topic
- Each action must be doable without rewatching — enough context to act on immediately
- Prioritise actions by when they should happen — immediate first, longer-term last
- No repeated advice across items. No markdown headers, no bold.

Stop after the last action item. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
