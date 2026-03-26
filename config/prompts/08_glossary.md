# glossary

enabled: false
label: Glossary

## short

```prompt
Output in English only. Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, format each entry exactly like this example:

**NotebookLM**
Google's AI-powered research tool that lets you upload documents and ask questions about them.

One blank line between entries. Bold the term name. Definition on the next line. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## medium

```prompt
Output in English only. Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, format each entry exactly like this example:

**NotebookLM**
Google's AI-powered research tool that lets you upload documents and ask questions about them.

One blank line between entries. Bold the term name. Definition on the next line. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```

## long

```prompt
Output in English only. Output ONLY the glossary — no preamble, no intro sentence, no sign-off. Begin with the first term or the exact phrase "No new terms identified."

Identify terms from this transcript that a general audience would benefit from having defined. Include technical terms, acronyms, proper nouns used as concepts, or field-specific jargon. Skip common everyday words.

Do NOT define any of these terms — they have been defined recently: {known_terms}

If there are no new terms to define after excluding the above, output exactly:
No new terms identified.

Otherwise, format each entry exactly like this example:

**NotebookLM**
Google's AI-powered research tool that lets you upload documents and ask questions about them.

One blank line between entries. Bold the term name. Definition on the next line. Stop after the last definition. Do not add anything else.

Transcript:
"""
{transcript}
"""
```
