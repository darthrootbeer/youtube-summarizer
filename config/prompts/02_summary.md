# summary

enabled: true
label: Summary

## short

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off. Begin with the first word of the paragraph.

OUTPUT FORMAT:
<1 paragraph — ~120 words of specific, concrete detail from the transcript>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>

<1 sentence walk-away — polished and universal, sounds like advice worth keeping, not a recap>

Rules:
- Third person only — never use "you", "your", "we", "I", "the host", "the speaker", "this video"
- The paragraph must contain concrete details: specific names, numbers, tools, claims, or examples from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic or write something true of any video on this subject
- Walk-away: polished, universal, memorable — same tone as a timeless piece of advice, not a summary of what was said
- No markdown headers, no bold, no numbered lists
- After the paragraph write exactly the line "Key takeaways" (nothing else on that line)
- Then exactly 3 bullets starting with "- "
- Then exactly 1 walk-away sentence — stop immediately after it

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off. Begin with the first word of paragraph 1.

OUTPUT FORMAT:
<paragraph 1 — ~120 words: what it is about and why it matters, with specific evidence>

<paragraph 2 — ~120 words: how it works, what was demonstrated, or what the evidence shows>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>

<1–2 sentence walk-away — polished and universal, sounds like advice worth keeping>

Rules:
- Third person only — never use "you", "your", "we", "I", "the host", "the speaker", "this video"
- Each paragraph must contain concrete details: specific names, numbers, tools, claims, or examples from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic or write something true of any video on this subject
- Walk-away: polished, universal, memorable — same tone as a timeless piece of advice
- No markdown headers, no bold, no numbered lists
- After paragraph 2 write exactly the line "Key takeaways" (nothing else on that line)
- Then exactly 5 bullets starting with "- "
- Then exactly 1–2 walk-away sentences — stop immediately after them

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the summary below — no preamble, no "Here is...", no sign-off. Begin with the first word of paragraph 1.

OUTPUT FORMAT:
<paragraph 1 — ~120 words: the core argument, situation, or thesis — what this is really about and why it matters>

<paragraph 2 — ~120 words: the key evidence, methodology, or mechanics — how it works or what was shown>

<paragraph 3 — ~120 words: implications, edge cases, caveats, or what to do with this information>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>
- <takeaway 6>
- <takeaway 7>

<2–3 sentence walk-away — polished and universal, sounds like advice worth keeping>

Rules:
- Third person only — never use "you", "your", "we", "I", "the host", "the speaker", "this video"
- Each paragraph must contain concrete details: specific names, numbers, tools, claims, or examples from the transcript — no generic observations
- Every bullet must state a specific fact, recommendation, or non-obvious insight — never restate the topic
- Walk-away: polished, universal, memorable — same tone as a timeless piece of advice
- No markdown headers, no bold, no numbered lists
- After paragraph 3 write exactly the line "Key takeaways" (nothing else on that line)
- Then exactly 7 bullets starting with "- "
- Then exactly 2–3 walk-away sentences — stop immediately after them

Transcript:
"""
{transcript}
"""
```
