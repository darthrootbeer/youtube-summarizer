# role_based

enabled: false
label: Role-based takeaways

## short

```prompt
Output ONLY role-based takeaways — no preamble, no "Here is...", no sign-off. Begin with the first audience label.

For each of the 3 audiences below, use this exact structure:

Founder:
<1–2 sentences on the specific business or product implication — name the opportunity, risk, or decision>
- <concrete next action specific to a founder, grounded in something from the transcript>
- <concrete next action>

Product manager:
<1–2 sentences on the specific product or prioritisation implication>
- <concrete next action specific to a PM, grounded in something from the transcript>
- <concrete next action>

Creator:
<1–2 sentences on the specific content or distribution implication>
- <concrete next action specific to a creator, grounded in something from the transcript>
- <concrete next action>

Rules:
- Each audience label exactly as shown, ending with ":"
- Each section must give meaningfully different advice — if the same action applies to all three, omit it and find what is unique to each role
- Every action must be specific: name the tool, platform, metric, or approach from the transcript
- No generic advice like "stay updated" or "consider your strategy"
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY role-based takeaways — no preamble, no "Here is...", no sign-off. Begin with the first audience label.

For each of the 3 audiences below, use this exact structure:

Founder:
<1 short paragraph on the specific business implication — name the opportunity, risk, or competitive angle>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Product manager:
<1 short paragraph on the specific product or roadmap implication>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Creator:
<1 short paragraph on the specific content, audience, or monetisation implication>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Rules:
- Each audience label exactly as shown, ending with ":"
- Each section must give meaningfully different advice — no recycled bullets across audiences
- Every action must be specific: name the tool, platform, metric, or approach from the transcript
- No generic advice. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY role-based takeaways — no preamble, no "Here is...", no sign-off. Begin with the first audience label.

For each of the 3 audiences below, use this exact structure:

Founder:
<paragraph 1 — the strategic implication: opportunity, threat, or competitive shift>
<paragraph 2 — what to do about it and why now>
- <concrete next action>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Product manager:
<paragraph 1 — the product or prioritisation implication>
<paragraph 2 — how this affects roadmap, metrics, or user behaviour>
- <concrete next action>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Creator:
<paragraph 1 — the content, distribution, or audience implication>
<paragraph 2 — how to apply this to workflow or growth>
- <concrete next action>
- <concrete next action>
- <concrete next action>
- <concrete next action>

Rules:
- Each audience label exactly as shown, ending with ":"
- Each section must give meaningfully different advice — no recycled content across audiences
- Every action must be specific: name the tool, platform, metric, or approach from the transcript
- No generic advice. No markdown headers, no bold.

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
