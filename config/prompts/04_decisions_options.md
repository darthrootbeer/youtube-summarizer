# decisions_options

enabled: false
label: Key decisions + options

## short

```prompt
Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off.

Extract 2–3 key decisions. For each decision, use this exact format:

Decision: <what must be decided>
Options: <option A> / <option B>
Tradeoff: <brief tradeoff>
Recommendation: <what to do>

Separate decisions with a blank line. Use plain language. No markdown headers, no bold.

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off.

Extract 3–5 key decisions. For each decision, use this exact format:

Decision: <what must be decided>
Options: <option A> / <option B> / <option C>
Tradeoff: <brief tradeoff>
Recommendation: <what to do>

Separate decisions with a blank line. Use plain language. No markdown headers, no bold.

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the key decisions from the transcript — no preamble, no "Here is...", no sign-off.

Extract 5–8 key decisions. For each decision, use this exact format:

Decision: <what must be decided>
Options: <option A> / <option B> / <option C>
Tradeoff: <brief tradeoff>
Recommendation: <what to do>

Separate decisions with a blank line. Use plain language. No markdown headers, no bold.

Stop after the last "Recommendation:" line. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
