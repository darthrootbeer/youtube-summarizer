# fact_vs_opinion

enabled: false
label: Fact vs opinion separation

## short

```prompt
Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Separate the transcript into three sections using this exact structure:

Observations
- <what happened / what is — 3 to 5 items>

Interpretations
- <how it is framed / what it implies — 3 to 5 items>

Predictions
- <what might happen next — 3 to 5 items>

Rules:
- Each section label on its own line, followed by "- " bullets
- Do not repeat items across sections
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Separate the transcript into three sections using this exact structure:

Observations
- <what happened / what is — 5 to 8 items>

Interpretations
- <how it is framed / what it implies — 5 to 8 items>

Predictions
- <what might happen next — 5 to 8 items>

Rules:
- Each section label on its own line, followed by "- " bullets
- Do not repeat items across sections
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Separate the transcript into three sections using this exact structure:

Observations
- <what happened / what is — 8 to 12 items>

Interpretations
- <how it is framed / what it implies — 8 to 12 items>

Predictions
- <what might happen next — 8 to 12 items>

Rules:
- Each section label on its own line, followed by "- " bullets
- Do not repeat items across sections
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
