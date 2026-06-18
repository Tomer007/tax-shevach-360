"""Authentication and contract upload routes."""

import logging
import fitz  # PyMuPDF

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.auth import (
    CodeNameRequest,
    LoginRequest,
    Token,
    authenticate_user,
    create_access_token,
    get_current_user,
    verify_code_name,
)
from app.contract_parser import ParsedContract, parse_contract_text
from app.email_service import send_contract_result_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/verify-code")
def verify_access_code(request: CodeNameRequest):
    """Verify the access code name (POKER) before allowing login."""
    if not verify_code_name(request.code_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="קוד גישה שגוי",
        )
    return {"valid": True, "message": "קוד גישה תקין"}


@router.post("/auth/login", response_model=Token)
def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
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

    Accepts plain text files (.txt) or PDF text content.
    Requires authentication.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file content
    content = await file.read()
    logger.info(f"Upload: filename={file.filename}, size={len(content)} bytes, content_type={file.content_type}")

    if len(content) > 10_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Extract text based on file type
    filename = file.filename.lower()
    text = ""
    is_pdf = filename.endswith(".pdf") or content[:5] == b"%PDF-"

    if is_pdf:
        # Extract text from PDF using PyMuPDF
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            doc.close()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read PDF file: {str(e)}")
    else:
        # Try as text file
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="Could not read file encoding")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from file")

    logger.info(f"Extracted {len(text)} chars from {file.filename}. First 100: {text[:100]}")

    # Truncate for AI processing
    text_for_parsing = text[:30_000]

    try:
        result = parse_contract_text(text_for_parsing)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {type(e).__name__}")

    # Send email notification with parsed results
    send_contract_result_email(result.model_dump(), file.filename or "unknown")

    return result
