# Process (Ollama prompts)

This file defines **what “jobs” we run on each transcript** before emailing it.

It’s meant to be human-readable and easy to edit.

## How it works

- Each section below is a **prompt** (an instruction set) we can run against the transcript.
- Set `enabled: true` to turn it on.
- If **multiple prompts are enabled**, the email will include **multiple clearly-labeled sections**, separated by a horizontal divider.
- The `{transcript}` placeholder is required in every prompt.

## Prompts

### default

enabled: true  
label: Summary

```prompt
You are a summarizer. Respond ONLY with the summary in the exact format below. No preamble, no “Here is...”, no sign-off.

FORMAT (copy this structure exactly):
---
<1 sentence introduction to what this is about>

<~{word_target} word summary in plain prose paragraphs>

Key takeaways
- <takeaway 1>
... exactly {bullet_count} bullets ...

<{wrapup_instruction}>
---

Rules:
- Write at a 7th grade reading level throughout — short sentences, plain words, no jargon
- The first line is exactly 1 sentence that introduces the topic
- Then 1–3 short paragraphs totalling ~{word_target} words (no bullets in the paragraphs)
- Then the line “Key takeaways” (exactly that, nothing else on the line)
- Then exactly {bullet_count} bullets starting with “- “
- Then exactly {wrapup_instruction} after the last bullet
- Do NOT mention the speaker, host, presenter, or “this video” — state ideas directly
- Do NOT use markdown headers, bold, numbered lists, or extra sections
- Do NOT add anything after the wrap-up

Transcript:
“””
{transcript}
“””
```

### executive_brief

enabled: true
label: Executive brief (5-minute read)

```prompt
Create an executive brief for a busy reader.

Rules:
- 120–180 words
- Do not mention the speaker, presenter, or “this video” — just summarize the ideas as standalone statements.
- No bold/italics markers (no **like this**, no _like this_)
- No markdown headers, no "Conclusion"
- Output must be English.
- One short "Why it matters" paragraph
- End with a line that says exactly: "Next actions"
- Then exactly 3 bullets (use "- " bullets)
- Do not include "Key Points", "[End ...]", or any bracketed sign-offs.

Transcript:
"""
{transcript}
"""
```

### action_checklist

enabled: true
label: Action checklist

```prompt
Turn this transcript into an action checklist someone could follow.

Rules:
- Keep it under 15 bullets total
- Use ONLY "- " bullets (no numbered lists)
- Group into 2–4 short sections, using plain text section labels like "This week:" (no markdown headers)
- Avoid repeating the same advice in multiple bullets

Transcript:
"""
{transcript}
"""
```

---

The prompts below are included for the product’s future, but are **off by default**.

### decisions_options

enabled: false  
label: Key decisions + options

```prompt
Extract the key decisions implied by the transcript.

Output:
- 3–7 decisions max
- For each: decision, options (2–3), tradeoffs, recommendation
- Use plain language and be concise

Transcript:
"""
{transcript}
"""
```

### tldr_5_things

enabled: false  
label: TL;DR + 5 things to remember

```prompt
Write:
1) A TL;DR of 2–3 sentences
2) "If you only remember 5 things" with exactly 5 "- " bullets

Avoid repetition and avoid hype.

Transcript:
"""
{transcript}
"""
```

### skeptics_review

enabled: false  
label: Skeptic’s review (what’s missing / questionable)

```prompt
Write a skeptical review of the transcript.

Rules:
- Separate "Strong points" and "Weak points / missing evidence"
- Keep it constructive, not snarky
- End with 3 bullets: "What would change my mind"

Transcript:
"""
{transcript}
"""
```

### fact_vs_opinion

enabled: false  
label: Fact vs opinion separation

```prompt
Separate the transcript into:
- Observations (what happened / what is)
- Interpretations (how the speaker frames it)
- Predictions (what might happen next)

Keep each list short and avoid repeating items across lists.

Transcript:
"""
{transcript}
"""
```

### glossary

enabled: false  
label: Glossary (plain English)

```prompt
Create a short glossary for a beginner.

Rules:
- 8–15 terms max
- Each definition 1–2 sentences
- Plain language, no jargon in the definition

Transcript:
"""
{transcript}
"""
```

### outline_timestamps

enabled: false  
label: Structured outline with timestamps

```prompt
Create a structured outline with timestamps if they appear or can be inferred.

Rules:
- 6–12 sections max
- Each section: timestamp (or "—"), title, 1 sentence summary

Transcript:
"""
{transcript}
"""
```

### quote_bank

enabled: false  
label: Quote bank + shareables

```prompt
Extract shareable quotes.

Output:
- 5 short "tweet-length" lines
- 3 longer pull quotes (1–2 sentences)

Do not invent quotes; only rewrite lightly for clarity.

Transcript:
"""
{transcript}
"""
```

### role_based

enabled: false  
label: Role-based versions (founder/PM/creator)

```prompt
Rewrite the key takeaways for 3 audiences:
- Founder
- Product manager
- Creator

Each audience gets:
- 1 short paragraph
- 3 bullets ("What to do next")

Avoid repeating the same bullet across audiences.

Transcript:
"""
{transcript}
"""
```

