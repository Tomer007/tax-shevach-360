"""Contract/document parsing service using OpenAI.

Reads an uploaded document (PDF text or image) and extracts
transaction details to fill the calculator form.
"""

import json
import os

import openai
from openai import OpenAI
from pydantic import BaseModel, Field

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

EXTRACTION_PROMPT = """You are a legal document parser specializing in Israeli real estate contracts (חוזה מכר מקרקעין).

Extract the following transaction details from the document. Return a JSON object with these fields (use null for missing data):

{
  "sale_date": "YYYY-MM-DD",
  "sale_amount": number (in ILS),
  "sale_currency": "ILS" | "USD" | "EUR",
  "sellers": [
    {
      "name": "full name in Hebrew",
      "id_number": "9-digit ID",
      "birth_date": "YYYY-MM-DD" or null,
      "share_percent": number (0-100),
      "is_israeli_resident": true/false
    }
  ],
  "acquisitions": [
    {
      "acquisition_date": "YYYY-MM-DD",
      "acquisition_type": "purchase" | "inheritance" | "gift" | "divorce",
      "amount": number,
      "currency": "ILS" | "USD" | "EUR" | "ILP" | "ILR",
      "share_percent": number
    }
  ],
  "property_address": "full address",
  "block_parcel": "גוש/חלקה if available",
  "notes": "any other relevant information"
}

Rules:
- Dates must be in YYYY-MM-DD format
- Amounts should be numbers without commas or currency symbols
- If the contract mentions the original purchase price, include it in acquisitions
- Identify all sellers/buyers and their ownership shares
- Default share to 100% if only one seller
- If currency is not specified, assume ILS
- Return ONLY valid JSON, no explanations"""


class ParsedContract(BaseModel):
    """Result of contract parsing."""

    sale_date: str | None = None
    sale_amount: float | None = None
    sale_currency: str | None = "ILS"
    sellers: list[dict] = Field(default_factory=list)
    acquisitions: list[dict] = Field(default_factory=list)
    property_address: str | None = None
    block_parcel: str | None = None
    notes: str | None = None
    raw_text: str = Field(default="", exclude=True)  # Excluded from API response
    confidence: str = "low"


def parse_contract_text(text: str) -> ParsedContract:
    """Parse contract text using OpenAI to extract transaction details."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=OPENAI_API_KEY)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract transaction details from this contract:\n\n{text}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=30.0,
        )
    except openai.AuthenticationError:
        raise ValueError("AI service configuration error - invalid API key")
    except openai.RateLimitError:
        raise ValueError("AI service temporarily unavailable - rate limited")
    except openai.APITimeoutError:
        raise ValueError("AI service timed out - please try again")

    content = response.choices[0].message.content or "{}"

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return ParsedContract(confidence="failed")

    # Validate and sanitize numeric fields
    sale_amount = data.get("sale_amount")
    if sale_amount is not None:
        try:
            sale_amount = float(sale_amount)
        except (ValueError, TypeError):
            sale_amount = None

    # Determine confidence based on completeness
    has_sale = data.get("sale_date") and sale_amount
    has_sellers = bool(data.get("sellers"))
    confidence = "high" if (has_sale and has_sellers) else "medium" if has_sale else "low"

    return ParsedContract(
        sale_date=data.get("sale_date"),
        sale_amount=sale_amount,
        sale_currency=data.get("sale_currency") or "ILS",
        sellers=data.get("sellers") or [],
        acquisitions=data.get("acquisitions") or [],
        property_address=data.get("property_address"),
        block_parcel=data.get("block_parcel"),
        notes=data.get("notes"),
        raw_text=text[:200],
        confidence=confidence,
    )
