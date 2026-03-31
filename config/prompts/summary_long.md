Output exactly two parts. Do not skip either part. Do not add section labels or headers of any kind.

Part 1 — prose summary:
One paragraph per major theme (3–5 themes), 250–400 words total. Plain, conversational English — like explaining it to a friend. Short sentences. Everyday words. No jargon. Skip filler and repetition.
Never start a sentence with "This video", "The video", "The speaker", or any person's name.
Do not use attribution phrases like "demonstrates", "explains", "covers", "shows", "discusses".

Part 2 — key takeaways:
Output the heading "Key Takeaways" on its own line. The very next line must be the first bullet. No text between the heading and the bullets. Exactly {bullet_count} bullets.

Key Takeaways
- [one short sentence — written like you're telling a friend, plain words, no jargon, no passive voice]
...

Each bullet starts with "- ". No markdown characters (no ##, no **, no *, no _, no ===). Stop after the last bullet. No other text.

Video title: {video_title}

Transcript:
"""
{transcript}
"""
