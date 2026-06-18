"""FastAPI application for Mas Shevach 360."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load .env file

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.calculator import calculate_transaction
from app.models import CalculationResult, TransactionInput
from app.routes import router
from app.auth_routes import router as auth_router

app = FastAPI(
    title="Mas Shevach 360",
    description="Israeli Capital Gains Tax Calculator API",
    version="1.0.0",
)

# CORS: restricted by default, configurable via env var
# In production (Render): set CORS_ORIGINS=https://mas-shevach-360.onrender.com
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mas-shevach-360"}


# Serve frontend static files in production
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve the SPA index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
