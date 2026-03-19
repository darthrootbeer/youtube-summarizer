# default

enabled: false
label: Summary

## short

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines. Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence naming the specific topic, argument, or finding>

<paragraph of ~100 words>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>

<1 sentence wrap-up>

Rules:
- Write in third person — never use "you", "your", "we", "I", "the host", or "the speaker"
- First sentence names the specific subject — never open with "During", "In this video", "In an engaging", or any meta-description of the format
- The paragraph must contain concrete details: specific names, numbers, tools, claims, or examples pulled directly from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic or write something true of any video on this subject
- Prioritise the surprising, counterintuitive, or actionable over the obvious
- Clear, direct prose — no jargon padding, no throat-clearing phrases
- After the intro sentence write exactly 1 prose paragraph (~100 words, no bullets)
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 3 bullets starting with "- "
- Then exactly 1 wrap-up sentence — stop immediately after it
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines. Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence naming the specific topic, argument, or finding>

<paragraph 1 — ~100 words>

<paragraph 2 — ~100 words>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>

<1–2 sentence wrap-up>

Rules:
- Write in third person — never use "you", "your", "we", "I", "the host", or "the speaker"
- First sentence names the specific subject — never open with "During", "In this video", "In an engaging", or any meta-description of the format
- Each paragraph must contain concrete details: specific names, numbers, tools, claims, or examples pulled directly from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic or write something true of any video on this subject
- Paragraph 1: what the content is about and why it matters — the core argument or situation
- Paragraph 2: how it works, what was demonstrated, or what the evidence/reasoning is
- Prioritise the surprising, counterintuitive, or actionable over the obvious
- Clear, direct prose — no jargon padding, no throat-clearing phrases
- After the intro sentence write exactly 2 prose paragraphs (~100 words each, no bullets)
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 5 bullets starting with "- "
- Then exactly 1–2 wrap-up sentences — stop immediately after them
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines. Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence naming the specific topic, argument, or finding>

<paragraph 1 — ~100 words>

<paragraph 2 — ~100 words>

<paragraph 3 — ~100 words>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>
- <takeaway 6>
- <takeaway 7>
- <takeaway 8>

<2–3 sentence wrap-up>

Rules:
- Write in third person — never use "you", "your", "we", "I", "the host", or "the speaker"
- First sentence names the specific subject — never open with "During", "In this video", "In an engaging", or any meta-description of the format
- Each paragraph must contain concrete details: specific names, numbers, tools, claims, or examples pulled directly from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic or write something true of any video on this subject
- Paragraph 1: the core argument, situation, or thesis — what this is really about and why it matters
- Paragraph 2: the key evidence, methodology, or mechanics — how it works or what was shown
- Paragraph 3: implications, edge cases, caveats, or what to do with this information
- Prioritise the surprising, counterintuitive, or actionable over the obvious
- Clear, direct prose — no jargon padding, no throat-clearing phrases
- After the intro sentence write exactly 3 prose paragraphs (~100 words each, no bullets) — do NOT jump straight to Key takeaways
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 8 bullets starting with "- "
- Then exactly 2–3 wrap-up sentences — stop immediately after them
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```
