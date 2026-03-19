# decisions_options

enabled: false
label: Key decisions + options

## short

```prompt
Output in English only. Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first "Decision:" line.

Extract exactly 2–3 key decisions actually discussed in the transcript. For each, use this exact format:

Decision: <the specific choice that must be made — name the actual thing>
Options: <option A as named or described in the transcript> / <option B>
Tradeoff: <concrete cost or risk of each side — use specifics, not generalities>
Recommendation: <what the transcript suggests, with the reason>

Separate decisions with a blank line. No markdown headers, no bold.

Rules:
- Only extract decisions genuinely present in the transcript — do not invent or extrapolate
- Every field must contain specifics — tool names, numbers, conditions — not abstract descriptions
- Tradeoff must name what you actually give up, not just "pros and cons exist"

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first "Decision:" line.

Extract exactly 3–5 key decisions actually discussed in the transcript. For each, use this exact format:

Decision: <the specific choice that must be made — name the actual thing>
Options: <option A as named in the transcript> / <option B> / <option C if applicable>
Tradeoff: <concrete cost or risk of each side — use specifics, not generalities>
Recommendation: <what the transcript suggests, with the reason>

Separate decisions with a blank line. No markdown headers, no bold.

Rules:
- Only extract decisions genuinely present in the transcript — do not invent or extrapolate
- Every field must contain specifics — tool names, numbers, conditions — not abstract descriptions
- Tradeoff must name what you actually give up, not just "pros and cons exist"
- Order decisions from most consequential to least

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off. Begin with the first "Decision:" line.

Extract exactly 5–8 key decisions actually discussed in the transcript. For each, use this exact format:

Decision: <the specific choice that must be made — name the actual thing>
Options: <option A as named in the transcript> / <option B> / <option C if applicable>
Tradeoff: <concrete cost or risk of each side — use specifics, not generalities>
Recommendation: <what the transcript suggests, with the reason>

Separate decisions with a blank line. No markdown headers, no bold.

Rules:
- Only extract decisions genuinely present in the transcript — do not invent or extrapolate
- Every field must contain specifics — tool names, numbers, conditions — not abstract descriptions
- Tradeoff must name what you actually give up, not just "pros and cons exist"
- Order decisions from most consequential to least

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
