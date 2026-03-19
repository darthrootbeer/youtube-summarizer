# glossary

enabled: true
label: Glossary

## short

```prompt
Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, for each term output exactly:

**Term**
One sentence definition written at a 7th grade reading level.

Leave one blank line between terms. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, for each term output exactly:

**Term**
One sentence definition written at a 7th grade reading level.

Leave one blank line between terms. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, for each term output exactly:

**Term**
One sentence definition written at a 7th grade reading level.

Leave one blank line between terms. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
