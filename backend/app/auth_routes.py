"""Authentication and contract upload routes."""

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

    # Decode text
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Try latin-1 as fallback
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read file encoding")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    if len(text) > 50_000:
        raise HTTPException(status_code=400, detail="File too large (max 50KB text)")

    try:
        result = parse_contract_text(text)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {type(e).__name__}")

    return result
