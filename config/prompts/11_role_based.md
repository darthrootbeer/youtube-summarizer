# role_based

enabled: false
label: Role-based versions (founder/PM/creator)

## short

```prompt
Output ONLY role-based takeaways — no preamble, no "Here is...", no sign-off. Begin with the first audience label.

For each of the 3 audiences below, use this exact structure:

Founder:
<1–2 sentences on what this means for them>
- <what to do next>
- <what to do next>

Product manager:
<1–2 sentences on what this means for them>
- <what to do next>
- <what to do next>

Creator:
<1–2 sentences on what this means for them>
- <what to do next>
- <what to do next>

Rules:
- Each audience label exactly as shown, ending with ":"
- Do not repeat the same bullet across audiences
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
<1 short paragraph on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>

Product manager:
<1 short paragraph on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>

Creator:
<1 short paragraph on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>

Rules:
- Each audience label exactly as shown, ending with ":"
- Do not repeat the same bullet across audiences
- No markdown headers, no bold

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
<2 short paragraphs on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>
- <what to do next>

Product manager:
<2 short paragraphs on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>
- <what to do next>

Creator:
<2 short paragraphs on what this means for them>
- <what to do next>
- <what to do next>
- <what to do next>
- <what to do next>

Rules:
- Each audience label exactly as shown, ending with ":"
- Do not repeat the same bullet across audiences
- No markdown headers, no bold

Stop after the last bullet. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
