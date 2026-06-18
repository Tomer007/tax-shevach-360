"""Authentication and contract upload routes."""

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
from app.contract_parser import ParsedContract, parse_contract_text
from app.email_service import send_contract_result_email

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10_000_000  # 10MB


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
    _record_attempt(f"code:{client_ip}")

    if not verify_code_name(request.code_name):
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
    _record_attempt(f"login:{client_ip}")

    user = authenticate_user(request.username, request.password)
    if not user:
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

        # If no text extracted, use OpenAI Vision to read from page images
        if not text.strip():
            logger.info(f"No text layer in PDF, using Vision for {file.filename}")
            try:
                import base64
                from app.contract_parser import parse_contract_images
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
                    # Send email notification with attachment
                    user_email = current_user.get("email")
                    email_sent = send_contract_result_email(result.model_dump(), file.filename or "unknown", file_content=content, user_email=user_email)
                    if not email_sent:
                        logger.warning(f"Failed to send email for {file.filename}")
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

    # Send email notification with attachment (non-blocking, failures are logged)
    user_email = current_user.get("email")
    email_sent = send_contract_result_email(result.model_dump(), file.filename or "unknown", file_content=content, user_email=user_email)
    if not email_sent:
        logger.warning(f"Failed to send email notification for {file.filename}")

    return result
