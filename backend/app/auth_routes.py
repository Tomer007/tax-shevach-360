"""Authentication and contract upload routes."""

import base64
import hashlib
import json
import logging
import os

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status

from app.auth import (
    CodeNameRequest,
    LoginRequest,
    Token,
    _check_rate_limit,
    _record_attempt,
    authenticate_user,
    create_access_token,
    get_current_user,
    verify_code_name,
)
from app.contract_parser import ParsedContract, parse_contract_text, parse_contract_images
from app.email_service import send_contract_result_email
from app.models import TransactionInput

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10_000_000  # 10MB

# Simple in-memory cache for parsed contracts (keyed by file content hash)
_parse_cache: dict[str, ParsedContract] = {}
MAX_CACHE_SIZE = 50


def _get_client_ip(request: Request) -> str:
    """Get client IP for rate limiting."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/auth/verify-code")
def verify_access_code(request: CodeNameRequest, raw_request: Request):
    """Verify the access code name (POKER) before allowing contract upload."""
    client_ip = _get_client_ip(raw_request)
    if not _check_rate_limit(f"code:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="יותר מדי ניסיונות. נסה שוב בעוד מספר דקות.",
        )

    if not verify_code_name(request.code_name):
        _record_attempt(f"code:{client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="קוד גישה שגוי",
        )
    return {"valid": True, "message": "קוד גישה תקין"}


@router.post("/auth/login", response_model=Token)
def login(request: LoginRequest, raw_request: Request):
    """Authenticate user and return JWT token."""
    client_ip = _get_client_ip(raw_request)
    if not _check_rate_limit(f"login:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="יותר מדי ניסיונות כניסה. נסה שוב בעוד 5 דקות.",
        )

    user = authenticate_user(request.username, request.password)
    if not user:
        _record_attempt(f"login:{client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="שם משתמש או סיסמה שגויים",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "username": current_user["username"],
        "full_name": current_user["full_name"],
    }


@router.post("/upload-contract", response_model=ParsedContract)
async def upload_contract(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a contract document and extract transaction details using AI.

    Accepts PDF or text files. Requires authentication.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file extension
    filename = file.filename.lower()
    ext = os.path.splitext(filename)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"סוג קובץ לא נתמך. נתמכים: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read file content
    content = await file.read()
    logger.info(f"Upload: filename={file.filename}, size={len(content)} bytes, user={current_user['username']}")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="הקובץ גדול מדי (מקסימום 10MB)")

    # Check cache — if same file was already parsed, return cached result
    file_hash = hashlib.sha256(content).hexdigest()
    if file_hash in _parse_cache:
        logger.info(f"Cache hit for {file.filename} (hash={file_hash[:12]})")
        return _parse_cache[file_hash]

    # Extract text based on file type
    text = ""
    is_pdf = ext == ".pdf" or content[:5] == b"%PDF-"

    if is_pdf:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            doc.close()
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise HTTPException(status_code=400, detail="לא ניתן לקרוא את קובץ ה-PDF")

        # Check if text is useful: has enough Hebrew chars and contract-related keywords
        hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
        has_key_terms = any(term in text for term in ['תמורה', 'מכר', 'מוכר', 'קונה', 'חוזה', 'ש"ח', 'שקל'])
        text_quality_ok = hebrew_chars > 100 and has_key_terms

        # If no text extracted OR text quality is poor, use OpenAI Vision
        if not text.strip() or not text_quality_ok:
            logger.info(f"{'No text layer' if not text.strip() else 'Poor text quality'} in PDF, using Vision for {file.filename}")
            try:


                doc = fitz.open(stream=content, filetype="pdf")
                images_b64: list[str] = []
                for page_num in range(min(len(doc), 8)):  # First 8 pages
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    images_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
                doc.close()

                if images_b64:
                    result = parse_contract_images(images_b64)
                    # Log extracted fields as pretty JSON for debugging

                    logger.warning(
                        f"\n{'='*60}\n"
                        f"PARSED CONTRACT (Vision) [{file.filename}]\n"
                        f"{'='*60}\n"
                        f"{json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str)}\n"
                        f"{'='*60}"
                    )
                    # Send email notification with attachment
                    user_email = current_user.get("email")
                    email_sent = send_contract_result_email(result.model_dump(), file.filename or "unknown", file_content=content, user_email=user_email)
                    if not email_sent:
                        logger.warning(f"Failed to send email for {file.filename}")
                    # Cache result
                    if len(_parse_cache) >= MAX_CACHE_SIZE:
                        _parse_cache.pop(next(iter(_parse_cache)))
                    _parse_cache[file_hash] = result
                    return result
            except ValueError as e:
                raise HTTPException(status_code=503, detail=str(e))
            except Exception as e:
                logger.error(f"Vision parsing error: {type(e).__name__}: {e}")
                raise HTTPException(status_code=500, detail="שגיאה בקריאת החוזה באמצעות AI")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="לא ניתן לקרוא את קידוד הקובץ")

    if not text.strip():
        raise HTTPException(status_code=400, detail="לא ניתן לחלץ טקסט מהקובץ")

    # Truncate for AI processing (first 30K chars is enough)
    text_for_parsing = text[:30_000]

    try:
        result = parse_contract_text(text_for_parsing)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Contract parsing error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="שגיאה בניתוח החוזה. נסה שוב.")

    # If text-based parsing got low confidence on a PDF, retry with Vision for better results
    if is_pdf and result.confidence == "low" and not result.sale_amount:
        logger.info(f"Low confidence text parse for {file.filename}, retrying with Vision")
        try:


            doc = fitz.open(stream=content, filetype="pdf")
            images_b64: list[str] = []
            for page_num in range(min(len(doc), 8)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
            doc.close()

            if images_b64:
                vision_result = parse_contract_images(images_b64)
                # Use vision result only if it's better (has sale_amount)
                if vision_result.sale_amount:
                    result = vision_result
                    logger.info(f"Vision retry succeeded for {file.filename}")
        except Exception as e:
            logger.warning(f"Vision retry failed for {file.filename}: {e}")
            # Keep original text-based result

    # Log extracted fields as pretty JSON for debugging

    logger.warning(
        f"\n{'='*60}\n"
        f"PARSED CONTRACT [{file.filename}]\n"
        f"{'='*60}\n"
        f"{json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str)}\n"
        f"{'='*60}"
    )

    # Send email notification with attachment (non-blocking, failures are logged)
    user_email = current_user.get("email")
    email_sent = send_contract_result_email(result.model_dump(), file.filename or "unknown", file_content=content, user_email=user_email)
    if not email_sent:
        logger.warning(f"Failed to send email notification for {file.filename}")

    # Store in cache
    if len(_parse_cache) >= MAX_CACHE_SIZE:
        # Evict oldest entry
        _parse_cache.pop(next(iter(_parse_cache)))
    _parse_cache[file_hash] = result

    return result


@router.post("/calculate-and-notify")
def calculate_and_notify(
    txn: TransactionInput,
    current_user: dict = Depends(get_current_user),
):
    """Calculate tax and send results email to the user."""
    from app.calculator import calculate_transaction

    try:
        result = calculate_transaction(txn)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid input: {e}")
    except Exception as e:
        logger.error(f"Calculation error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"שגיאה בחישוב: {type(e).__name__}: {e}")

    # Send email with results
    user_email = current_user.get("email")
    _send_calculation_email(result.model_dump(), current_user, user_email)

    return result


def _send_calculation_email(result_data: dict, user: dict, user_email: str | None) -> None:
    """Send calculation results email."""

    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from html import escape

    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    notify_email = os.environ.get("NOTIFY_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        return

    recipients = [notify_email]
    if user_email and user_email not in recipients:
        recipients.append(user_email)

    # Format results
    sellers = result_data.get("seller_results", [])
    full_tax = result_data.get("full_tax", 0)
    full_shevach = result_data.get("full_real_shevach", 0)
    routes = result_data.get("route_comparison", [])

    best_route = min(routes, key=lambda r: r["tax_amount"]) if routes else {}
    best_name_map = {"linear_mutav": "ליניארי מוטב", "regular": "רגיל", "linear_with_prisa": "ליניארי + פריסה", "exempt_49b2": "פטור"}
    best_name = best_name_map.get(best_route.get("route_name", ""), best_route.get("route_name", ""))

    # Build sellers summary
    sellers_html = ""
    for s in sellers:
        name = escape(str(s.get("seller_name", "—")))
        share = s.get("share_percent", 0)
        tax = s.get("total_tax", 0)
        rec = best_name_map.get(s.get("recommended_route", ""), s.get("recommended_route", ""))
        sellers_html += f"""<tr>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;color:#111827;font-weight:600;">{name}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;color:#6b7280;">{share}%</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;color:#059669;font-weight:700;">₪{tax:,.0f}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;color:#4f46e5;font-weight:600;">{rec}</td>
        </tr>"""

    routes_html = ""
    for r in routes:
        rname = best_name_map.get(r.get("route_name", ""), r.get("route_name", ""))
        tax = r.get("tax_amount", 0)
        rate = r.get("effective_rate", 0)
        is_best = r.get("tax_amount") == best_route.get("tax_amount")
        style = "background:#eff6ff;border:1px solid #bfdbfe;" if is_best else "border:1px solid #e5e7eb;"
        routes_html += f"""<tr>
          <td style="padding:10px 14px;{style}color:#111827;font-weight:{'700' if is_best else '500'};">{rname}{'  ⭐' if is_best else ''}</td>
          <td style="padding:10px 14px;{style}color:#059669;font-weight:700;">₪{tax:,.0f}</td>
          <td style="padding:10px 14px;{style}color:#6b7280;">{rate:.2f}%</td>
        </tr>"""

    html_body = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
  <tr><td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:12px 12px 0 0;padding:24px;text-align:center;">
    <h1 style="margin:0 0 4px;font-size:20px;font-weight:800;color:#fff;">מס שבח 360 — תוצאות חישוב</h1>
    <p style="margin:0;color:#e0e7ff;font-size:12px;">חושב ע"י {escape(user.get('full_name', ''))}</p>
  </td></tr>
  <tr><td style="background:#fff;padding:24px;">

    <table role="presentation" width="100%" style="margin-bottom:20px;border-collapse:collapse;">
      <tr>
        <td style="background:#f0fdf4;border-radius:8px;padding:16px;text-align:center;width:50%;">
          <p style="margin:0 0 4px;font-size:11px;color:#6b7280;text-transform:uppercase;">שבח ריאלי</p>
          <p style="margin:0;font-size:20px;font-weight:700;color:#111827;">₪{full_shevach:,.0f}</p>
        </td>
        <td style="width:12px;"></td>
        <td style="background:#eff6ff;border-radius:8px;padding:16px;text-align:center;width:50%;">
          <p style="margin:0 0 4px;font-size:11px;color:#6b7280;text-transform:uppercase;">מס לתשלום</p>
          <p style="margin:0;font-size:20px;font-weight:700;color:#059669;">₪{full_tax:,.0f}</p>
        </td>
      </tr>
    </table>

    <h2 style="margin:0 0 12px;font-size:14px;font-weight:700;color:#111827;border-right:3px solid #4f46e5;padding-right:10px;">השוואת מסלולים</h2>
    <table role="presentation" width="100%" style="margin-bottom:20px;border-collapse:collapse;font-size:13px;">
      <thead><tr style="background:#f9fafb;">
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">מסלול</th>
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">מס</th>
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">שיעור</th>
      </tr></thead>
      <tbody>{routes_html}</tbody>
    </table>

    <h2 style="margin:0 0 12px;font-size:14px;font-weight:700;color:#111827;border-right:3px solid #059669;padding-right:10px;">פירוט לפי מוכר</h2>
    <table role="presentation" width="100%" style="margin-bottom:16px;border-collapse:collapse;font-size:13px;">
      <thead><tr style="background:#f9fafb;">
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">שם</th>
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">חלק</th>
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">מס</th>
        <th style="padding:8px 14px;text-align:right;color:#6b7280;font-weight:500;">מסלול</th>
      </tr></thead>
      <tbody>{sellers_html}</tbody>
    </table>

  </td></tr>
  <tr><td style="background:#f9fafb;border-radius:0 0 12px 12px;padding:14px 24px;text-align:center;border-top:1px solid #e5e7eb;">
    <p style="margin:0;color:#9ca3af;font-size:10px;">נשלח אוטומטית ממערכת מס שבח 360 | הנתונים להערכה בלבד</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    text_body = f"מס שבח 360 — תוצאות חישוב\n\nשבח ריאלי: ₪{full_shevach:,.0f}\nמס לתשלום: ₪{full_tax:,.0f}\nמסלול מומלץ: {best_name}\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"מס שבח 360 | תוצאות חישוב: ₪{full_tax:,.0f} מס"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Calculation email sent to {recipients}")
    except Exception as e:
        logger.error(f"Calculation email failed: {e}")
