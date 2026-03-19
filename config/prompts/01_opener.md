# opener

enabled: true
label: Opener

## short

```prompt
Output in English only. Output ONLY {sentence_count} sentence(s) — no preamble, no label, no sign-off. Begin immediately with the first word of the content.

Write {sentence_count} polished sentence(s) that give a complete, self-contained picture of this video. Each sentence must carry a distinct, essential idea — together they should let someone fully grasp the context and value of the content without watching. Do not describe what was covered. Do not write "the speaker says" or "this video explains." Write the actual insight, argument, or advice directly, in plain declarative prose.

Stop after sentence {sentence_count}. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY {sentence_count} sentence(s) — no preamble, no label, no sign-off. Begin immediately with the first word of the content.

Write {sentence_count} polished sentence(s) that give a complete, self-contained picture of this video. Each sentence must carry a distinct, essential idea — together they should let someone fully grasp the context and value of the content without watching. Do not describe what was covered. Do not write "the speaker says" or "this video explains." Write the actual insight, argument, or advice directly, in plain declarative prose.

Stop after sentence {sentence_count}. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY {sentence_count} sentence(s) — no preamble, no label, no sign-off. Begin immediately with the first word of the content.

Write {sentence_count} polished sentence(s) that give a complete, self-contained picture of this video. Each sentence must carry a distinct, essential idea — together they should let someone fully grasp the context, core argument, and key implications without watching. Do not describe what was covered. Do not write "the speaker says" or "this video explains." Write the actual insight, argument, or advice directly, in plain declarative prose. Sequence the sentences so the most important idea comes first.

Stop after sentence {sentence_count}. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
