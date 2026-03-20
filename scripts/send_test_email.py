#!/usr/bin/env python3
"""Send a test email using the real template and real SMTP credentials."""
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

from youtube_summarizer.config import load_settings, repo_root
from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
from youtube_summarizer.run import _format_summary_html, _load_dotenv_if_present

from jinja2 import Environment, FileSystemLoader

_load_dotenv_if_present(repo_root() / ".env")
settings = load_settings()

if not settings.email_from or not settings.gmail_app_password:
    print("ERROR: YTS_EMAIL_FROM and YTS_GMAIL_APP_PASSWORD must be set in .env")
    sys.exit(1)

# ── Fake content ──────────────────────────────────────────────────────────────

SUMMARY = """\
AI models are getting dramatically cheaper and more capable at the same time, \
creating a rare moment where startups can build things that were impossible a year ago.

The cost per token for frontier models has dropped 10x in 18 months. \
This compression is driven by hardware improvements, better quantization, and \
fierce competition between providers. For builders, this means the unit economics \
of AI-powered products are finally viable at scale.

The bigger shift is at the architecture layer. Long context windows and improved \
reasoning mean models can now handle entire codebases or legal documents in a single \
pass — collapsing workflows that previously required complex pipelines.

Key takeaways
- Token costs have fallen 10x in 18 months and are still dropping
- Long context windows eliminate most retrieval-augmented generation pipelines
- Reasoning models can now handle tasks that required human review loops
- The competitive moat is shifting from model quality to distribution and data
- Startups that move now have a 12–18 month window before incumbents catch up

The builders who win this cycle will be the ones who treat cost curves as a \
product feature, not just an ops concern.
"""

CHECKLIST = """\
This week:
- ☐ Audit your current LLM spend and model tier — you're probably overpaying
- ☐ Test a long-context pass on your most complex pipeline step
- ☐ Identify one human review loop that a reasoning model could replace

Next month:
- ☐ Prototype a single-pass architecture for your heaviest RAG workflow
- ☐ Set a token-cost benchmark to track as models improve
- ☐ Talk to three customers about what they'd pay for 10x faster turnaround
"""

sections = [
    {"label": "Summary",          "html": _format_summary_html(SUMMARY)},
    {"label": "Action checklist", "html": _format_summary_html(CHECKLIST)},
]

# ── Render ────────────────────────────────────────────────────────────────────

root = repo_root()
env = Environment(loader=FileSystemLoader(str(root / "youtube_summarizer" / "templates")))
template = env.get_template("email.html.j2")

render_ctx = dict(
    subject="[TEST] YouTube Summarizer — template preview",
    source_label="Subscription",
    source_name="Y Combinator",
    video_title="The AI Cost Curve Is Collapsing — What Founders Need to Know",
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    sections=sections,
    transcript_source="parakeet-mlx",
    published_at=None,
    published_at_display="Mar 18, 2026 · 9:00 AM",
    beta_stats=None,
)

html = template.render(**render_ctx)
text = "Test email — view in an HTML-capable client."

# ── Send ──────────────────────────────────────────────────────────────────────

to_addr = settings.email_to or settings.email_from
print(f"Sending test email to {to_addr} ...")

send_gmail_smtp(
    email_from=settings.email_from,
    email_to=to_addr,
    gmail_app_password=settings.gmail_app_password,
    content=EmailContent(subject=render_ctx["subject"], text=text, html=html),
)

print("Sent. Check your inbox.")
