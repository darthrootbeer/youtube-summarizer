# default

enabled: true
label: Summary

## short

```prompt
You are a summarizer. Respond ONLY with the summary in the exact format below. No preamble, no "Here is...", no sign-off.

FORMAT (copy this structure exactly):
---
<1 sentence introduction to what this is about>

<~100 word summary in plain prose paragraphs>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>

<1 sentence wrap-up>
---

Rules:
- Write at a 7th grade reading level — short sentences, plain words, no jargon
- The first line is exactly 1 sentence that introduces the topic
- Then 1–2 short paragraphs totalling ~100 words (no bullets in the paragraphs)
- Then the line "Key takeaways" (exactly that, nothing else on the line)
- Then exactly 3 bullets starting with "- "
- Then exactly 1 final wrap-up sentence
- Do NOT mention the speaker, host, presenter, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, numbered lists, or extra sections
- Do NOT add anything after the wrap-up sentence

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
You are a summarizer. Respond ONLY with the summary in the exact format below. No preamble, no "Here is...", no sign-off.

FORMAT (copy this structure exactly):
---
<1 sentence introduction to what this is about>

<~200 word summary in plain prose paragraphs>

Key takeaways
- <takeaway 1>
- <takeaway 2>
- <takeaway 3>
- <takeaway 4>
- <takeaway 5>

<1–2 sentence wrap-up>
---

Rules:
- Write at a 7th grade reading level — short sentences, plain words, no jargon
- The first line is exactly 1 sentence that introduces the topic
- Then 1–3 short paragraphs totalling ~200 words (no bullets in the paragraphs)
- Then the line "Key takeaways" (exactly that, nothing else on the line)
- Then exactly 5 bullets starting with "- "
- Then exactly 1–2 final wrap-up sentences
- Do NOT mention the speaker, host, presenter, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, numbered lists, or extra sections
- Do NOT add anything after the wrap-up

Transcript:
"""
{transcript}
"""
```

## long

```prompt
You are a summarizer. Respond ONLY with the summary in the exact format below. No preamble, no "Here is...", no sign-off.

FORMAT (copy this structure exactly):
---
<1 sentence introduction to what this is about>

<~300 word summary in plain prose paragraphs>

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
---

Rules:
- Write at a 7th grade reading level — short sentences, plain words, no jargon
- The first line is exactly 1 sentence that introduces the topic
- Then 2–4 short paragraphs totalling ~300 words (no bullets in the paragraphs)
- Then the line "Key takeaways" (exactly that, nothing else on the line)
- Then exactly 8 bullets starting with "- "
- Then exactly 2–3 final wrap-up sentences
- Do NOT mention the speaker, host, presenter, or "this video" — state ideas directly
- Do NOT use markdown headers, bold, numbered lists, or extra sections
- Do NOT add anything after the wrap-up

Transcript:
"""
{transcript}
"""
```
