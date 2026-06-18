"""Email notification service.

Sends contract parsing results with the original file attached.
Clean light-themed HTML email that works in all email clients.
"""

import json
import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

logger = logging.getLogger(__name__)


def send_contract_result_email(
    parsed_data: dict,
    filename: str,
    file_content: bytes | None = None,
) -> bool:
    """Send parsed contract results with attachment to the configured email."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    notify_email = os.environ.get("NOTIFY_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured, skipping email")
        return False

    # Extract and sanitize values
    safe_filename = escape(str(filename))
    confidence = parsed_data.get("confidence", "low")
    confidence_he = {"high": "גבוהה ✓", "medium": "בינונית ⚠", "low": "נמוכה", "failed": "נכשל ✗"}.get(confidence, confidence)
    confidence_color = {"high": "#059669", "medium": "#d97706", "low": "#dc2626", "failed": "#dc2626"}.get(confidence, "#6b7280")

    sale_date = parsed_data.get("sale_date") or "—"
    sale_amount = parsed_data.get("sale_amount")
    sale_amount_str = f"₪{sale_amount:,.0f}" if sale_amount else "—"
    sale_currency = parsed_data.get("sale_currency") or "ILS"
    address = parsed_data.get("property_address") or "—"
    block_parcel = parsed_data.get("block_parcel") or "—"
    notes = parsed_data.get("notes") or ""
    sellers = parsed_data.get("sellers") or []
    acquisitions = parsed_data.get("acquisitions") or []

    # Sellers rows
    sellers_rows = ""
    for i, s in enumerate(sellers, 1):
        name = escape(str(s.get("name", "—")))
        id_num = escape(str(s.get("id_number", "—")))
        share = s.get("share_percent", "—")
        sellers_rows += f"""<tr>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#374151;text-align:center;">{i}</td>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#111827;font-weight:600;">{name}</td>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#6b7280;direction:ltr;">{id_num}</td>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#4f46e5;font-weight:700;text-align:center;">{share}%</td>
        </tr>"""

    # Acquisitions rows
    acq_rows = ""
    for a in acquisitions:
        acq_date = escape(str(a.get("acquisition_date", "—")))
        acq_type_map = {"purchase": "רכישה", "inheritance": "ירושה", "gift": "מתנה", "divorce": "גירושין"}
        acq_type = acq_type_map.get(str(a.get("acquisition_type", "")), str(a.get("acquisition_type", "—")))
        acq_amount = a.get("amount")
        acq_amount_str = f"₪{acq_amount:,.0f}" if acq_amount else "—"
        acq_rows += f"""<tr>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">{acq_date}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#374151;">{acq_type}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#111827;font-weight:600;">{acq_amount_str}</td>
        </tr>"""

    json_output = json.dumps(parsed_data, ensure_ascii=False, indent=2)

    # HTML email — clean light theme (works in all email clients)
    html_body = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:12px 12px 0 0;padding:28px 24px;text-align:center;">
    <h1 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#ffffff;">מס שבח 360</h1>
    <p style="margin:0;color:#e0e7ff;font-size:13px;">חוזה חדש הועלה למערכת</p>
  </td></tr>

  <!-- Body -->
  <tr><td style="background:#ffffff;padding:28px 24px;">

    <!-- Confidence -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
    <tr>
      <td style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;">
        <table role="presentation" width="100%"><tr>
          <td style="color:#6b7280;font-size:13px;">רמת ביטחון בחילוץ</td>
          <td style="text-align:left;"><span style="color:{confidence_color};font-weight:700;font-size:14px;">{confidence_he}</span></td>
        </tr></table>
      </td>
    </tr>
    </table>

    <!-- Transaction Details -->
    <h2 style="margin:0 0 14px;font-size:15px;font-weight:700;color:#111827;border-right:3px solid #4f46e5;padding-right:10px;">פרטי העסקה</h2>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;font-size:14px;">
      <tr><td style="padding:10px 0;color:#6b7280;width:35%;">קובץ</td><td style="padding:10px 0;color:#374151;font-weight:500;">{safe_filename}</td></tr>
      <tr><td style="padding:10px 0;color:#6b7280;border-top:1px solid #f3f4f6;">תאריך מכירה</td><td style="padding:10px 0;color:#111827;font-weight:600;border-top:1px solid #f3f4f6;">{escape(sale_date)}</td></tr>
      <tr><td style="padding:10px 0;color:#6b7280;border-top:1px solid #f3f4f6;">סכום מכירה</td><td style="padding:10px 0;color:#059669;font-weight:700;font-size:18px;border-top:1px solid #f3f4f6;">{escape(sale_amount_str)}</td></tr>
      <tr><td style="padding:10px 0;color:#6b7280;border-top:1px solid #f3f4f6;">מטבע</td><td style="padding:10px 0;color:#374151;border-top:1px solid #f3f4f6;">{escape(sale_currency)}</td></tr>
      <tr><td style="padding:10px 0;color:#6b7280;border-top:1px solid #f3f4f6;">כתובת</td><td style="padding:10px 0;color:#374151;border-top:1px solid #f3f4f6;">{escape(address)}</td></tr>
      <tr><td style="padding:10px 0;color:#6b7280;border-top:1px solid #f3f4f6;">גוש / חלקה</td><td style="padding:10px 0;color:#374151;border-top:1px solid #f3f4f6;">{escape(block_parcel)}</td></tr>
    </table>

    {"" if not sellers else f'''
    <!-- Sellers -->
    <h2 style="margin:0 0 14px;font-size:15px;font-weight:700;color:#111827;border-right:3px solid #4f46e5;padding-right:10px;">מוכרים ({len(sellers)})</h2>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <thead><tr style="background:#f9fafb;">
        <th style="padding:10px 12px;text-align:center;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">#</th>
        <th style="padding:10px 12px;text-align:right;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">שם</th>
        <th style="padding:10px 12px;text-align:right;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">ת.ז.</th>
        <th style="padding:10px 12px;text-align:center;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">חלק</th>
      </tr></thead>
      <tbody>{sellers_rows}</tbody>
    </table>
    '''}

    {"" if not acquisitions else f'''
    <!-- Acquisitions -->
    <h2 style="margin:0 0 14px;font-size:15px;font-weight:700;color:#111827;border-right:3px solid #059669;padding-right:10px;">היסטוריית רכישה</h2>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <thead><tr style="background:#f9fafb;">
        <th style="padding:10px 12px;text-align:right;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">תאריך</th>
        <th style="padding:10px 12px;text-align:right;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">סוג</th>
        <th style="padding:10px 12px;text-align:right;color:#6b7280;font-weight:500;font-size:12px;border-bottom:1px solid #e5e7eb;">סכום</th>
      </tr></thead>
      <tbody>{acq_rows}</tbody>
    </table>
    '''}

    {"" if not notes else f'''
    <!-- Notes -->
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
      <p style="margin:0;color:#1e40af;font-size:13px;"><strong>הערות:</strong> {escape(notes)}</p>
    </div>
    '''}

    <!-- JSON -->
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px;">
      <p style="margin:0 0 8px;font-size:12px;font-weight:600;color:#6b7280;">JSON (לייבוא למערכת)</p>
      <pre style="margin:0;background:#ffffff;border:1px solid #e5e7eb;padding:12px;border-radius:6px;font-size:11px;color:#374151;overflow-x:auto;direction:ltr;font-family:Consolas,'Courier New',monospace;line-height:1.5;white-space:pre-wrap;">{escape(json_output)}</pre>
    </div>

  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#f9fafb;border-radius:0 0 12px 12px;padding:16px 24px;text-align:center;border-top:1px solid #e5e7eb;">
    <p style="margin:0 0 4px;color:#9ca3af;font-size:11px;">נשלח אוטומטית ממערכת מס שבח 360</p>
    <p style="margin:0;color:#d1d5db;font-size:10px;">הנתונים חולצו ע״י AI ויש לאמתם מול המסמך המקורי</p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    # Plain text fallback
    text_body = f"""מס שבח 360 — חוזה חדש הועלה

קובץ: {filename}
רמת ביטחון: {confidence_he}

פרטי עסקה:
- תאריך מכירה: {sale_date}
- סכום: {sale_amount_str} ({sale_currency})
- כתובת: {address}
- גוש/חלקה: {block_parcel}

מוכרים:
{chr(10).join(f"  {i+1}. {s.get('name','?')} (ת.ז. {s.get('id_number','?')}) - {s.get('share_percent','?')}%" for i, s in enumerate(sellers))}

{f"הערות: {notes}" if notes else ""}

JSON:
{json_output}

---
נשלח אוטומטית. יש לאמת הנתונים מול המסמך המקורי.
"""

    # Assemble MIME
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"מס שבח 360 | חוזה חדש: {safe_filename}"
    msg["From"] = smtp_user
    msg["To"] = notify_email

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_part)

    # Attach original file
    if file_content:
        attachment = MIMEApplication(file_content)
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(attachment)

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
