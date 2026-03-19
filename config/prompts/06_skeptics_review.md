# skeptics_review

enabled: false
label: Skeptic's review

## short

```prompt
Output in English only. Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <specific claim or demonstration from the transcript that holds up to scrutiny>
- <specific claim or demonstration from the transcript that holds up to scrutiny>

Weak points / missing evidence
- <specific claim made that lacks supporting data or reasoning — name the claim>
- <specific gap, assumption, or conflation — be precise>

What would change my mind
- <specific evidence, study, or data point that would validate the weak point above>
- <specific condition or counterexample that would strengthen or refute the argument>

Rules:
- Every bullet must cite or reference a specific claim, tool, number, or assertion from the transcript
- No generic critiques ("more evidence needed", "could be biased") — name exactly what is missing or questionable
- Strong points must be genuinely strong, not faint praise
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <point>
- <point>
- <point>

Weak points / missing evidence
- <point>
- <point>
- <point>

What would change my mind
- <point>
- <point>
- <point>

Rules:
- "Strong points": exactly 3 bullets
- "Weak points / missing evidence": exactly 3 bullets
- "What would change my mind": exactly 3 bullets
- Every bullet must cite or reference a specific claim, tool, number, or assertion from the transcript
- No generic critiques — name exactly what is missing, questionable, or what evidence is needed
- Strong points must be genuinely strong, not faint praise
- "What would change my mind" items must be specific data, studies, or conditions — not "more research"
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY a skeptical review — no preamble, no "Here is...", no sign-off. Begin with the first section label.

Use this exact structure:

Strong points
- <point>
- <point>
- <point>
- <point>
- <point>

Weak points / missing evidence
- <point>
- <point>
- <point>
- <point>
- <point>

What would change my mind
- <point>
- <point>
- <point>
- <point>

Rules:
- "Strong points": exactly 5 bullets
- "Weak points / missing evidence": exactly 5 bullets
- "What would change my mind": exactly 4 bullets
- Every bullet must cite or reference a specific claim, tool, number, or assertion from the transcript
- No generic critiques — name exactly what is missing, questionable, or what evidence is needed
- Strong points must be genuinely strong, not faint praise
- "What would change my mind" items must be specific data, studies, or conditions — not "more research"
- Constructive, not snarky. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
