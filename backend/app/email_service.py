"""Email notification service.

Sends contract parsing results with the original file attached.
Modern dark-themed HTML email report.
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
    """Send parsed contract results with attachment to the configured email.

    Args:
        parsed_data: Extracted contract data dict
        filename: Original uploaded filename
        file_content: Raw file bytes to attach (optional)

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

    # Sanitize values
    safe_filename = escape(str(filename))
    confidence = parsed_data.get("confidence", "low")
    confidence_he = {"high": "גבוהה ✓", "medium": "בינונית", "low": "נמוכה", "failed": "נכשל ✗"}.get(confidence, confidence)
    confidence_color = {"high": "#34d399", "medium": "#fbbf24", "low": "#f87171", "failed": "#ef4444"}.get(confidence, "#71717a")

    sale_date = parsed_data.get("sale_date") or "—"
    sale_amount = parsed_data.get("sale_amount")
    sale_amount_str = f"₪{sale_amount:,.0f}" if sale_amount else "—"
    sale_currency = parsed_data.get("sale_currency") or "ILS"
    address = parsed_data.get("property_address") or "—"
    block_parcel = parsed_data.get("block_parcel") or "—"
    notes = parsed_data.get("notes") or ""
    sellers = parsed_data.get("sellers") or []
    acquisitions = parsed_data.get("acquisitions") or []

    # Build email
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"מס שבח 360 | חוזה חדש: {safe_filename}"
    msg["From"] = smtp_user
    msg["To"] = notify_email

    # Sellers table rows
    sellers_rows = ""
    for i, s in enumerate(sellers, 1):
        name = escape(str(s.get("name", "—")))
        id_num = escape(str(s.get("id_number", "—")))
        share = s.get("share_percent", "—")
        sellers_rows += f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#e4e4e7;">{i}</td>
          <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#f4f4f5;font-weight:600;">{name}</td>
          <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#a1a1aa;direction:ltr;">{id_num}</td>
          <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#818cf8;font-weight:600;">{share}%</td>
        </tr>"""

    # Acquisitions rows
    acq_rows = ""
    for a in acquisitions:
        acq_date = escape(str(a.get("acquisition_date", "—")))
        acq_type_map = {"purchase": "רכישה", "inheritance": "ירושה", "gift": "מתנה", "divorce": "גירושין"}
        acq_type = acq_type_map.get(str(a.get("acquisition_type", "")), str(a.get("acquisition_type", "—")))
        acq_amount = a.get("amount")
        acq_amount_str = f"₪{acq_amount:,.0f}" if acq_amount else "—"
        acq_rows += f"""
        <tr>
          <td style="padding:8px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#a1a1aa;">{acq_date}</td>
          <td style="padding:8px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#e4e4e7;">{acq_type}</td>
          <td style="padding:8px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#f4f4f5;font-weight:600;">{acq_amount_str}</td>
        </tr>"""

    json_output = json.dumps(parsed_data, ensure_ascii=False, indent=2)

    # HTML email body — dark hi-tech theme
    html_body = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:32px 20px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);border-radius:16px;padding:32px 24px;text-align:center;border:1px solid rgba(99,102,241,0.2);margin-bottom:24px;">
    <h1 style="margin:0 0 8px;font-size:24px;font-weight:800;background:linear-gradient(135deg,#818cf8,#a78bfa,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">מס שבח 360</h1>
    <p style="margin:0;color:#a1a1aa;font-size:14px;">חוזה חדש הועלה למערכת</p>
  </div>

  <!-- Confidence Badge -->
  <div style="background:#1c1c2e;border-radius:12px;padding:16px 20px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:space-between;">
    <span style="color:#71717a;font-size:13px;">רמת ביטחון בחילוץ</span>
    <span style="color:{confidence_color};font-weight:700;font-size:14px;padding:4px 12px;background:rgba(255,255,255,0.04);border-radius:20px;">{confidence_he}</span>
  </div>

  <!-- Main Details Card -->
  <div style="background:#1c1c2e;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);">
    <h2 style="margin:0 0 16px;font-size:15px;font-weight:700;color:#f4f4f5;display:flex;align-items:center;gap:8px;">
      <span style="width:3px;height:14px;background:linear-gradient(180deg,#6366f1,#8b5cf6);border-radius:4px;display:inline-block;"></span>
      פרטי העסקה
    </h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <tr>
        <td style="padding:10px 0;color:#71717a;width:35%;">קובץ</td>
        <td style="padding:10px 0;color:#e4e4e7;font-weight:500;">{safe_filename}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#71717a;">תאריך מכירה</td>
        <td style="padding:10px 0;color:#e4e4e7;font-weight:600;">{escape(sale_date)}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#71717a;">סכום מכירה</td>
        <td style="padding:10px 0;color:#34d399;font-weight:700;font-size:16px;">{escape(sale_amount_str)}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#71717a;">מטבע</td>
        <td style="padding:10px 0;color:#e4e4e7;">{escape(sale_currency)}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#71717a;">כתובת הנכס</td>
        <td style="padding:10px 0;color:#e4e4e7;">{escape(address)}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#71717a;">גוש / חלקה</td>
        <td style="padding:10px 0;color:#e4e4e7;">{escape(block_parcel)}</td>
      </tr>
    </table>
  </div>

  <!-- Sellers -->
  {"" if not sellers else f'''
  <div style="background:#1c1c2e;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);">
    <h2 style="margin:0 0 16px;font-size:15px;font-weight:700;color:#f4f4f5;display:flex;align-items:center;gap:8px;">
      <span style="width:3px;height:14px;background:linear-gradient(180deg,#6366f1,#8b5cf6);border-radius:4px;display:inline-block;"></span>
      מוכרים ({len(sellers)})
    </h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;text-transform:uppercase;">#</th>
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;text-transform:uppercase;">שם</th>
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;text-transform:uppercase;">ת.ז.</th>
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;text-transform:uppercase;">חלק</th>
        </tr>
      </thead>
      <tbody>{sellers_rows}</tbody>
    </table>
  </div>
  '''}

  <!-- Acquisitions -->
  {"" if not acquisitions else f'''
  <div style="background:#1c1c2e;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);">
    <h2 style="margin:0 0 16px;font-size:15px;font-weight:700;color:#f4f4f5;display:flex;align-items:center;gap:8px;">
      <span style="width:3px;height:14px;background:linear-gradient(180deg,#10b981,#059669);border-radius:4px;display:inline-block;"></span>
      היסטוריית רכישה
    </h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;">תאריך</th>
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;">סוג</th>
          <th style="padding:8px 14px;text-align:start;color:#52525b;font-weight:500;font-size:11px;">סכום</th>
        </tr>
      </thead>
      <tbody>{acq_rows}</tbody>
    </table>
  </div>
  '''}

  <!-- Notes -->
  {"" if not notes else f'''
  <div style="background:rgba(99,102,241,0.06);border-radius:12px;padding:16px 20px;margin-bottom:16px;border:1px solid rgba(99,102,241,0.15);">
    <p style="margin:0;color:#a5b4fc;font-size:13px;font-weight:500;">הערות: {escape(notes)}</p>
  </div>
  '''}

  <!-- JSON -->
  <div style="background:#1c1c2e;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);">
    <h2 style="margin:0 0 12px;font-size:13px;font-weight:600;color:#71717a;">JSON מלא (לייבוא למערכת)</h2>
    <pre style="margin:0;background:rgba(0,0,0,0.3);padding:14px;border-radius:8px;font-size:11px;color:#a1a1aa;overflow-x:auto;direction:ltr;font-family:'Courier New',monospace;line-height:1.5;white-space:pre-wrap;">{escape(json_output)}</pre>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding-top:16px;border-top:1px solid rgba(255,255,255,0.04);">
    <p style="margin:0 0 4px;color:#52525b;font-size:11px;">נשלח אוטומטית ממערכת מס שבח 360</p>
    <p style="margin:0;color:#3f3f46;font-size:10px;">הנתונים חולצו ע"י AI ויש לאמתם מול המסמך המקורי</p>
  </div>

</div>
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

JSON:
{json_output}

---
נשלח אוטומטית. יש לאמת הנתונים מול המסמך המקורי.
"""

    # Assemble MIME
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_part)

    # Attach original file if provided
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
