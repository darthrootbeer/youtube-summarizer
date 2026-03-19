# tldr_5_things

enabled: false
label: TL;DR — things to remember

## short

```prompt
Output in English only. Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first word of the TL;DR.

<TL;DR: 1–2 sentences — the single most important thing, stated as a direct claim with at least one specific detail>

If you remember nothing else
- <the most non-obvious or surprising specific point>
- <a concrete fact, number, or named technique>
- <the most actionable thing — specific enough to do today>

Rules:
- TL;DR must make a direct claim — not "this video covers X" but the actual conclusion
- Every bullet must contain a concrete detail from the transcript — no generic observations
- Bullets must not repeat each other or overlap with the TL;DR
- No hype, no filler. No markdown headers, no bold.

Stop after the third bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first word of the TL;DR.

<TL;DR: 2–3 sentences — the core argument or finding, stated as direct claims with specific details>

If you remember nothing else
- <the most non-obvious or surprising specific point>
- <a concrete fact, number, or named technique>
- <a counterintuitive claim or caveat>
- <the most actionable thing — specific enough to do today>
- <what this changes or makes obsolete>

Rules:
- TL;DR must make direct claims — not "this video covers X" but the actual conclusions
- Every bullet must contain a concrete detail from the transcript — no generic observations
- Each bullet should be a distinct insight — no overlap, no repetition of the TL;DR
- No hype, no filler. No markdown headers, no bold.

Stop after the fifth bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY the following — no preamble, no "Here is...", no sign-off. Begin with the first word of the TL;DR.

<TL;DR: 3–4 sentences — the core argument or finding, stated as direct claims with specific details>

If you remember nothing else
- <the most non-obvious or surprising specific point>
- <a concrete fact, number, or named technique>
- <a counterintuitive claim or caveat>
- <the most actionable thing — specific enough to do today>
- <what this changes or makes obsolete>
- <a risk or failure mode specifically named>
- <the key condition or context that limits when this applies>
- <one concrete next step anyone in this field should take>

Rules:
- TL;DR must make direct claims — not "this video covers X" but the actual conclusions
- Every bullet must contain a concrete detail from the transcript — no generic observations
- Each bullet should be a distinct insight — no overlap, no repetition of the TL;DR
- No hype, no filler. No markdown headers, no bold.

Stop after the eighth bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
