# fact_vs_opinion

enabled: false
label: Fact vs opinion separation

## short

```prompt
Separate the transcript into:
- Observations (what happened / what is)
- Interpretations (how the speaker frames it)
- Predictions (what might happen next)

Keep each list to 3–5 items. Avoid repeating items across lists.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Separate the transcript into:
- Observations (what happened / what is)
- Interpretations (how the speaker frames it)
- Predictions (what might happen next)

Keep each list to 5–8 items. Avoid repeating items across lists.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Separate the transcript into:
- Observations (what happened / what is)
- Interpretations (how the speaker frames it)
- Predictions (what might happen next)

Keep each list to 8–12 items. Avoid repeating items across lists.

Transcript:
"""
{transcript}
"""
```
