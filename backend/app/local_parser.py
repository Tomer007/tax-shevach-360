"""Local LLM contract parser using Ollama.

Uses a locally-running Llama model via Ollama for contract extraction.
No API keys needed — runs entirely on the local machine.
Supports structured JSON output via Pydantic schema.
"""

import json
import logging
import os

try:
    import ollama
    OLLAMA_INSTALLED = True
except ImportError:
    OLLAMA_INSTALLED = False

from app.contract_parser import EXTRACTION_PROMPT, ParsedContract

logger = logging.getLogger(__name__)

# Default model — user can override via env var
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    if not OLLAMA_INSTALLED:
        return False
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list()
        return True
    except Exception:
        return False


def parse_contract_text_local(text: str) -> ParsedContract:
    """Parse contract text using local Ollama model.

    Uses structured output (JSON mode) for reliable extraction.
    Falls back gracefully if Ollama is not running.
    """
    if not OLLAMA_INSTALLED:
        raise ValueError("חבילת ollama לא מותקנת. יש להתקין: pip install ollama")

    try:
        client = ollama.Client(host=OLLAMA_HOST)
    except Exception as e:
        raise ValueError(f"לא ניתן להתחבר ל-Ollama: {e}")

    model = OLLAMA_MODEL
    logger.info(f"Parsing contract with local model: {model}")

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract transaction details from this contract:\n\n{text}"},
            ],
            format="json",
            options={
                "temperature": 0.1,
                "num_predict": 4000,
            },
        )
    except ollama.ResponseError as e:
        if "not found" in str(e).lower():
            raise ValueError(f"המודל '{model}' לא נמצא. יש להריץ: ollama pull {model}")
        raise ValueError(f"שגיאה במודל המקומי: {e}")
    except Exception as e:
        raise ValueError(f"שגיאה בהתחברות ל-Ollama: {e}")

    content = response.message.content or "{}"

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"Local model returned invalid JSON: {content[:200]}")
        return ParsedContract(confidence="failed")

    # Validate and sanitize (same logic as OpenAI parser)
    sale_amount = data.get("sale_amount")
    if sale_amount is not None:
        try:
            sale_amount = float(sale_amount)
        except (ValueError, TypeError):
            sale_amount = None

    has_sale = data.get("sale_date") and sale_amount
    has_sellers = bool(data.get("sellers"))
    confidence = "high" if (has_sale and has_sellers) else "medium" if has_sale else "low"

    return ParsedContract(
        sale_date=data.get("sale_date"),
        sale_amount=sale_amount,
        sale_currency=data.get("sale_currency") or "ILS",
        sellers=data.get("sellers") or [],
        buyers=data.get("buyers") or [],
        acquisitions=data.get("acquisitions") or [],
        property_address=data.get("property_address"),
        block_parcel=data.get("block_parcel"),
        property_type=data.get("property_type"),
        payment_schedule=data.get("payment_schedule"),
        notes=data.get("notes"),
        is_single_apartment=data.get("is_single_apartment"),
        is_inheritance=data.get("is_inheritance"),
        has_building_rights=data.get("has_building_rights"),
        building_rights_value=data.get("building_rights_value"),
        ownership_months=data.get("ownership_months"),
        raw_text=text[:200],
        confidence=confidence,
    )


def parse_contract_images_local(images_b64: list[str]) -> ParsedContract:
    """Parse contract from images using local Ollama vision model.

    Requires a vision-capable model like llava or llama3.2-vision.
    """
    if not OLLAMA_INSTALLED:
        raise ValueError("חבילת ollama לא מותקנת. יש להתקין: pip install ollama")

    try:
        client = ollama.Client(host=OLLAMA_HOST)
    except Exception as e:
        raise ValueError(f"לא ניתן להתחבר ל-Ollama: {e}")

    # Use vision model
    vision_model = os.environ.get("OLLAMA_VISION_MODEL", "llama3.2-vision")
    logger.info(f"Parsing contract images with local vision model: {vision_model}")

    try:
        response = client.chat(
            model=vision_model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": "Extract transaction details from this Israeli real estate contract (חוזה מכר). The pages are shown as images.",
                    "images": images_b64,
                },
            ],
            format="json",
            options={
                "temperature": 0.1,
                "num_predict": 4000,
            },
        )
    except ollama.ResponseError as e:
        if "not found" in str(e).lower():
            raise ValueError(f"המודל '{vision_model}' לא נמצא. יש להריץ: ollama pull {vision_model}")
        raise ValueError(f"שגיאה במודל המקומי: {e}")
    except Exception as e:
        raise ValueError(f"שגיאה בהתחברות ל-Ollama: {e}")

    content = response.message.content or "{}"

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"Local vision model returned invalid JSON: {content[:200]}")
        return ParsedContract(confidence="failed")

    sale_amount = data.get("sale_amount")
    if sale_amount is not None:
        try:
            sale_amount = float(sale_amount)
        except (ValueError, TypeError):
            sale_amount = None

    has_sale = data.get("sale_date") and sale_amount
    has_sellers = bool(data.get("sellers"))
    confidence = "high" if (has_sale and has_sellers) else "medium" if has_sale else "low"

    return ParsedContract(
        sale_date=data.get("sale_date"),
        sale_amount=sale_amount,
        sale_currency=data.get("sale_currency") or "ILS",
        sellers=data.get("sellers") or [],
        buyers=data.get("buyers") or [],
        acquisitions=data.get("acquisitions") or [],
        property_address=data.get("property_address"),
        block_parcel=data.get("block_parcel"),
        property_type=data.get("property_type"),
        payment_schedule=data.get("payment_schedule"),
        notes=data.get("notes"),
        is_single_apartment=data.get("is_single_apartment"),
        is_inheritance=data.get("is_inheritance"),
        has_building_rights=data.get("has_building_rights"),
        building_rights_value=data.get("building_rights_value"),
        ownership_months=data.get("ownership_months"),
        raw_text="[parsed from images via local Vision model]",
        confidence=confidence,
    )
