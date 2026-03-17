from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


def send_gmail_smtp(
    *,
    email_from: str,
    email_to: str,
    gmail_app_password: str,
    content: EmailContent,
) -> None:
    msg = EmailMessage()
    msg["From"] = email_from
    msg["To"] = email_to
    msg["Subject"] = content.subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    msg.set_content(content.text)
    msg.add_alternative(content.html, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(email_from, gmail_app_password)
        smtp.send_message(msg)

