# default

enabled: true
label: Summary

## short

```prompt
You are a summarizer. Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines.

Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence that introduces the topic>

<~100 word summary in plain prose>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>

<1 sentence wrap-up>

Rules:
- 7th grade reading level — short sentences, plain words
- First line: exactly 1 sentence introducing the topic
- Then 1–2 paragraphs totalling ~100 words (no bullets in paragraphs)
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 3 bullets starting with "- "
- Then exactly 1 wrap-up sentence — stop immediately after it
- Do NOT mention the speaker, host, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
You are a summarizer. Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines.

Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence that introduces the topic>

<~200 word summary in plain prose>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>

<1–2 sentence wrap-up>

Rules:
- 7th grade reading level — short sentences, plain words
- First line: exactly 1 sentence introducing the topic
- Then 1–3 paragraphs totalling ~200 words (no bullets in paragraphs)
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 5 bullets starting with "- "
- Then exactly 1–2 wrap-up sentences — stop immediately after them
- Do NOT mention the speaker, host, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```

## long

```prompt
You are a summarizer. Output ONLY the summary below — no preamble, no "Here is...", no sign-off, no delimiter lines.

Begin your response with the first word of the intro sentence.

OUTPUT FORMAT:
<1 sentence that introduces the topic>

<~300 word summary in plain prose>

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
- 7th grade reading level — short sentences, plain words
- First line: exactly 1 sentence introducing the topic
- Then 2–4 paragraphs totalling ~300 words (no bullets in paragraphs)
- Then the exact line "Key takeaways" (nothing else on that line)
- Then exactly 8 bullets starting with "- "
- Then exactly 2–3 wrap-up sentences — stop immediately after them
- Do NOT mention the speaker, host, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, or numbered lists

Transcript:
"""
{transcript}
"""
```
