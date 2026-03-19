# opener

enabled: true
label: Opener

## short

```prompt
Output ONLY one sentence — no preamble, no label, no sign-off. Begin immediately with the sentence.

Distill this transcript into a single polished, universal takeaway. Write it as the one idea worth remembering — not a description of what was discussed, not "the speaker says," not a personal reflection. Boil the content down to its underlying advice or insight, combining all examples into one coherent, memorable sentence that stands alone.

Stop after the sentence. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY one sentence — no preamble, no label, no sign-off. Begin immediately with the sentence.

Distill this transcript into a single polished, universal takeaway. Write it as the one idea worth remembering — not a description of what was discussed, not "the speaker says," not a personal reflection. Boil the content down to its underlying advice or insight, combining all examples and threads into one coherent, memorable sentence that stands alone without context.

Stop after the sentence. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY one sentence — no preamble, no label, no sign-off. Begin immediately with the sentence.

Distill this transcript into a single polished, universal takeaway. Write it as the one idea worth remembering across the entire content — not a description, not a list, not "the speaker argues." Synthesize the core thesis and its most important implication into one coherent, memorable sentence that stands alone without context.

Stop after the sentence. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
