# executive_brief

enabled: false
label: Executive brief

## short

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first word of the brief.

Write in third person. No mention of "the speaker", "the host", or "this video". No bold, no markdown headers.

Structure:
<2–3 sentences of specific context — name the topic, the key claim, and why it matters now>

Why it matters: <one sentence on the real-world consequence or opportunity>

Next actions
- <specific action grounded in something said in the transcript>
- <specific action grounded in something said in the transcript>

Rules:
- Every sentence must contain a concrete detail — a name, number, tool, claim, or example from the transcript
- No generic observations that could apply to any video on this subject
- Actions must be specific enough to do without rewatching — not "explore options" or "consider the approach"
- Stop after the second bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first word of the brief.

Write in third person. No mention of "the speaker", "the host", or "this video". No bold, no markdown headers.

Structure:
<paragraph 1 — ~60 words: the situation, what changed, or what the core argument is>

<paragraph 2 — ~60 words: the mechanism, evidence, or how it works>

Why it matters
<one short paragraph on real-world consequence or opportunity>

Next actions
- <specific action>
- <specific action>
- <specific action>

Rules:
- Every sentence must contain a concrete detail — a name, number, tool, claim, or example from the transcript
- No generic observations that could apply to any video on this subject
- Actions must be specific enough to do without rewatching
- Stop after the third bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY an executive brief — no preamble, no "Here is...", no sign-off. Begin with the first word of the brief.

Write in third person. No mention of "the speaker", "the host", or "this video". No bold, no markdown headers.

Structure:
<paragraph 1 — ~70 words: the situation, what changed, or the core thesis>

<paragraph 2 — ~70 words: the mechanism, evidence, or how it works>

<paragraph 3 — ~60 words: caveats, risks, or conditions that limit the conclusion>

Why it matters
<one short paragraph on real-world consequence or opportunity>

Next actions
- <specific action>
- <specific action>
- <specific action>
- <specific action>
- <specific action>

Rules:
- Every sentence must contain a concrete detail — a name, number, tool, claim, or example from the transcript
- No generic observations that could apply to any video on this subject
- Actions must be specific enough to do without rewatching
- Stop after the fifth bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
