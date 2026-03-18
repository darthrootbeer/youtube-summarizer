# fact_vs_opinion

enabled: false
label: Fact vs opinion

## short

```prompt
Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Separate the transcript into three sections using this exact structure:

Stated facts
- <a verifiable claim or data point stated as fact — quote or closely paraphrase>
- <a verifiable claim or data point stated as fact>
- <a verifiable claim or data point stated as fact>

Opinions / interpretations
- <a judgement, preference, or framing that reflects a point of view — not universally true>
- <a judgement, preference, or framing>
- <a judgement, preference, or framing>

Predictions
- <a forward-looking claim about what will happen — name the specific outcome predicted>
- <a forward-looking claim>
- <a forward-looking claim>

Rules:
- Each section label on its own line, followed by "- " bullets
- Items must be specific — include the actual claim, not a category description
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

Stated facts
- <verifiable claim — 5 to 7 items>

Opinions / interpretations
- <judgement or framing — 5 to 7 items>

Predictions
- <forward-looking claim — 5 to 7 items>

Rules:
- "Stated facts": 5–7 bullets — verifiable claims stated as fact, closely quoted or paraphrased
- "Opinions / interpretations": 5–7 bullets — judgements, preferences, or framings that reflect a point of view
- "Predictions": 5–7 bullets — specific forward-looking claims; include the predicted outcome and timeframe if given
- Each section label on its own line, followed by "- " bullets
- Items must be specific — include the actual claim, not a category description
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

Stated facts
- <verifiable claim — 8 to 12 items>

Opinions / interpretations
- <judgement or framing — 8 to 12 items>

Predictions
- <forward-looking claim — 8 to 12 items>

Rules:
- "Stated facts": 8–12 bullets — verifiable claims stated as fact, closely quoted or paraphrased
- "Opinions / interpretations": 8–12 bullets — judgements, preferences, or framings that reflect a point of view
- "Predictions": 8–12 bullets — specific forward-looking claims; include the predicted outcome and timeframe if given
- Each section label on its own line, followed by "- " bullets
- Items must be specific — include the actual claim, not a category description
- Do not repeat items across sections
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
