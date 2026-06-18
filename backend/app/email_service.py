"""Email notification service.

Sends contract parsing results to the configured email address.
"""

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

logger = logging.getLogger(__name__)


def send_contract_result_email(parsed_data: dict, filename: str) -> bool:
    """Send parsed contract results as JSON to the configured email.

    Returns True if sent successfully, False otherwise.
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    notify_email = os.environ.get("NOTIFY_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured, skipping email")
        return False

    # Sanitize user-derived values for HTML
    safe_filename = escape(str(filename))
    safe_address = escape(str(parsed_data.get("property_address") or "—"))
    safe_block = escape(str(parsed_data.get("block_parcel") or "—"))
    safe_confidence = escape(str(parsed_data.get("confidence", "N/A")))

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"מס שבח 360 — חוזה חדש: {safe_filename}"
    msg["From"] = smtp_user
    msg["To"] = notify_email

    # Plain text version
    json_output = json.dumps(parsed_data, ensure_ascii=False, indent=2)
    text_body = f"חוזה חדש הועלה למערכת מס שבח 360.\n\nקובץ: {filename}\n\nתוצאות:\n{json_output}"

    # HTML version (all values escaped)
    sellers_html = ""
    for s in parsed_data.get("sellers", []):
        name = escape(str(s.get("name", "?")))
        share = escape(str(s.get("share_percent", "?")))
        sellers_html += f"<li>{name} ({share}%)</li>"

    html_body = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6366f1;">מס שבח 360 — חוזה חדש</h2>
        <p>קובץ: <strong>{safe_filename}</strong></p>
        <p>רמת ביטחון: <strong>{safe_confidence}</strong></p>
        <hr style="border: 1px solid #e4e4e7;">
        <h3>פרטים שחולצו:</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding: 6px; color: #71717a;">תאריך מכירה:</td><td style="padding: 6px;"><strong>{escape(str(parsed_data.get('sale_date') or '—'))}</strong></td></tr>
            <tr><td style="padding: 6px; color: #71717a;">סכום:</td><td style="padding: 6px;"><strong>{escape(str(parsed_data.get('sale_amount') or '—'))} {escape(str(parsed_data.get('sale_currency') or 'ILS'))}</strong></td></tr>
            <tr><td style="padding: 6px; color: #71717a;">כתובת:</td><td style="padding: 6px;"><strong>{safe_address}</strong></td></tr>
            <tr><td style="padding: 6px; color: #71717a;">גוש/חלקה:</td><td style="padding: 6px;"><strong>{safe_block}</strong></td></tr>
        </table>
        <h3>מוכרים:</h3>
        <ul>{sellers_html}</ul>
        <hr style="border: 1px solid #e4e4e7;">
        <details>
            <summary style="cursor: pointer; color: #6366f1;">JSON מלא</summary>
            <pre style="background: #f4f4f5; padding: 12px; border-radius: 8px; font-size: 12px; overflow-x: auto; direction: ltr;">{escape(json_output)}</pre>
        </details>
        <p style="color: #a1a1aa; font-size: 12px; margin-top: 20px;">נשלח אוטומטית ממערכת מס שבח 360</p>
    </div>
    """

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email sent for contract: {filename}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {type(e).__name__}: {e}")
        return False
