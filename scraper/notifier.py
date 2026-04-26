import os
import logging
import smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENTS_FILE = Path(__file__).resolve().parent.parent / "recipients.txt"


def load_recipients() -> list:
    if not RECIPIENTS_FILE.exists():
        raise FileNotFoundError(f"recipients.txt not found at {RECIPIENTS_FILE}.")
    recipients = [
        line.strip()
        for line in RECIPIENTS_FILE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not recipients:
        raise ValueError("recipients.txt contains no email addresses.")
    log.info("Loaded %d recipient(s)", len(recipients))
    return recipients


def build_html(summary: dict, pdf_url: str) -> str:
    key_changes_html = "".join(
        f"<li>{change}</li>\n" for change in (summary.get("key_changes") or [])
    )
    title    = summary.get("title")           or "Untitled Bill"
    date     = summary.get("date")            or "Date unknown"
    endorser = summary.get("endorser")        or "Unknown"
    argument = summary.get("argument")        or "—"
    proposal = summary.get("proposal")        or "—"
    affected = summary.get("who_is_affected") or "—"
    today    = datetime.now().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;color:#222;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 16px;">
  <tr><td align="center">
  <table width="580" cellpadding="0" cellspacing="0" style="max-width:580px;width:100%;background:#ffffff;border:1px solid #e0e0e0;">

    <tr>
      <td style="padding:24px 32px 20px;border-bottom:2px solid #222;">
        <p style="margin:0 0 6px;font-size:11px;color:#666;letter-spacing:1px;text-transform:uppercase;">Kenya Parliament Digest &mdash; {today}</p>
        <h1 style="margin:0;font-size:20px;font-weight:700;color:#111;line-height:1.3;">{title}</h1>
      </td>
    </tr>

    <tr>
      <td style="padding:16px 32px;border-bottom:1px solid #e0e0e0;background:#fafafa;">
        <table cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding-right:32px;">
              <p style="margin:0;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">Date Introduced</p>
              <p style="margin:4px 0 0;font-size:13px;color:#111;font-weight:600;">{date}</p>
            </td>
            <td>
              <p style="margin:0;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">Endorsed By</p>
              <p style="margin:4px 0 0;font-size:13px;color:#111;font-weight:600;">{endorser}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <tr>
      <td style="padding:28px 32px;">
        <p style="margin:0 0 4px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">The Problem</p>
        <p style="margin:0 0 20px;font-size:14px;line-height:1.7;color:#333;">{argument}</p>

        <p style="margin:0 0 4px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">The Proposal</p>
        <p style="margin:0 0 20px;font-size:14px;line-height:1.7;color:#333;">{proposal}</p>

        <p style="margin:0 0 4px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">Who Is Affected</p>
        <p style="margin:0 0 24px;font-size:14px;line-height:1.7;color:#333;">{affected}</p>

        <p style="margin:0 0 10px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">Key Changes</p>
        <ul style="margin:0 0 28px;padding-left:20px;font-size:14px;line-height:1.9;color:#333;">
          {key_changes_html}
        </ul>

        <a href="{pdf_url}" style="display:inline-block;padding:10px 22px;background:#111;color:#fff;font-size:13px;font-weight:600;text-decoration:none;letter-spacing:0.5px;">
          Read Full Bill &rarr;
        </a>
      </td>
    </tr>

    <tr>
      <td style="padding:16px 32px;border-top:1px solid #e0e0e0;background:#fafafa;">
        <p style="margin:0;font-size:11px;color:#aaa;line-height:1.6;">
          This summary was AI-generated from the official gazette PDF. Always verify against the
          <a href="{pdf_url}" style="color:#888;">original document</a>.
          To unsubscribe, remove your email from recipients.txt in the
          <a href="https://github.com/verybrian/parliament-digest" style="color:#888;">project repository</a>.
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
</table>
</body>
</html>"""


def send(summary: dict, pdf_url: str) -> None:
    sender_email    = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        raise ValueError("SENDER_EMAIL and SENDER_PASSWORD environment variables must be set.")

    recipients = load_recipients()
    title      = summary.get("title") or "New Parliamentary Bill"
    subject    = f"Parliament Digest: {title}"
    html_body  = build_html(summary, pdf_url)

    log.info("Connecting to Gmail SMTP...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
        for recipient in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"Parliament Digest <{sender_email}>"
            msg["To"]      = recipient
            msg.attach(MIMEText(html_body, "html"))
            server.sendmail(sender_email, recipient, msg.as_string())
            log.info("Sent to %s", recipient)

    log.info("Done — %d email(s) sent.", len(recipients))