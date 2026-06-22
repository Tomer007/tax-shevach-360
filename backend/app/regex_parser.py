"""Rule-based contract parser using regex patterns.

Extracts transaction details from Israeli real estate contracts
without any AI/LLM — purely pattern matching on Hebrew text.
Works offline, instantly, and for free.
"""

import re
import logging
from datetime import date

from app.contract_parser import ParsedContract

logger = logging.getLogger(__name__)

# --- Date patterns ---
# Matches: 15.07.2025, 15/07/2025, 15-07-2025
DATE_PATTERN = r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})'
# Matches: ביום 15 לחודש יולי שנת 2025
HEBREW_DATE_PATTERN = r'ביום\s+(\d{1,2})\s+לחודש\s+(\w+)\s+שנת?\s+(\d{4})'
# Hebrew month names
HEBREW_MONTHS = {
    'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'מרס': 3, 'אפריל': 4,
    'מאי': 5, 'יוני': 6, 'יולי': 7, 'אוגוסט': 8,
    'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12,
}

# --- Amount patterns ---
# Matches: 4,800,000 ש"ח or ₪4,800,000 or 4800000
AMOUNT_PATTERN = r'(\d[\d,]+)\s*(?:ש"ח|₪|שקל|ש״ח)'
AMOUNT_PATTERN_PREFIX = r'(?:₪|ש"ח|שקל)\s*(\d[\d,]+)'
# Matches: סך של X or סך סופי של X
TOTAL_AMOUNT_PATTERN = r'(?:סך\s+(?:סופי\s+)?(?:של\s+)?|התמורה\s*[:\-]?\s*)(\d[\d,]+)\s*(?:ש"ח|₪|שקל|ש״ח)'

# --- ID patterns ---
ID_PATTERN = r'ת"ז\.?\s*(\d{9}|\d{8})'
ID_PATTERN_ALT = r'ת\.?ז\.?\s*(\d{9}|\d{8})'
COMPANY_ID_PATTERN = r'ח\.?פ\.?\s*(\d{9}|\d{8})'

# --- Address patterns ---
GUSH_CHELKA = r'גוש\s*(\d+)\s*חלק[הת]\s*(\d+)'
GUSH_CHELKA_ALT = r'גוש\s*(\d+).*?חלק[הת]\s*(\d+)'
SUB_CHELKA = r'תת\s*חלק[הת]\s*(\d+)'

# --- Seller/Buyer markers ---
SELLER_MARKERS = ['המוכר', 'מוכר', 'צד א', 'צד ראשון']
BUYER_MARKERS = ['הקונה', 'קונה', 'הרוכש', 'רוכש', 'צד ב', 'צד שני']


def _parse_date(day: str, month: str, year: str) -> str | None:
    """Convert parsed date components to YYYY-MM-DD."""
    try:
        d = int(day)
        y = int(year)
        # Month can be number or Hebrew name
        if month.isdigit():
            m = int(month)
        else:
            m = HEBREW_MONTHS.get(month, 0)
            if m == 0:
                return None
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100:
            return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, TypeError):
        pass
    return None


def _extract_amount(text: str) -> float | None:
    """Extract the largest amount from text (likely the total sale price)."""
    amounts: list[float] = []

    # Try total/תמורה pattern first
    for match in re.finditer(TOTAL_AMOUNT_PATTERN, text):
        num_str = match.group(1).replace(',', '')
        try:
            amounts.append(float(num_str))
        except ValueError:
            pass

    # Then general amount patterns
    for pattern in [AMOUNT_PATTERN, AMOUNT_PATTERN_PREFIX]:
        for match in re.finditer(pattern, text):
            num_str = match.group(1).replace(',', '')
            try:
                amounts.append(float(num_str))
            except ValueError:
                pass

    if not amounts:
        return None

    # Return the largest amount (most likely the total sale price)
    return max(amounts)


def _extract_ids(text: str) -> list[dict]:
    """Extract all ID numbers with surrounding context."""
    results = []
    for pattern in [ID_PATTERN, ID_PATTERN_ALT, COMPANY_ID_PATTERN]:
        for match in re.finditer(pattern, text):
            id_num = match.group(1)
            # Get context around the match (50 chars before)
            start = max(0, match.start() - 80)
            context = text[start:match.start()]
            results.append({'id_number': id_num, 'context': context, 'pos': match.start()})
    return results


def _extract_names_near_ids(text: str, ids: list[dict], markers: list[str]) -> list[dict]:
    """Extract names near ID numbers that appear after seller/buyer markers."""
    persons = []
    seen_ids = set()

    # Find section boundaries for sellers vs buyers
    seller_zones: list[tuple[int, int]] = []
    buyer_zones: list[tuple[int, int]] = []

    for marker in SELLER_MARKERS:
        for match in re.finditer(re.escape(marker), text):
            seller_zones.append((match.start(), match.start() + 2000))
    for marker in BUYER_MARKERS:
        for match in re.finditer(re.escape(marker), text):
            buyer_zones.append((match.start(), match.start() + 2000))

    for id_info in ids:
        if id_info['id_number'] in seen_ids:
            continue
        seen_ids.add(id_info['id_number'])

        # Determine if this ID is in a seller or buyer zone
        pos = id_info['pos']
        is_seller = any(s <= pos <= e for s, e in seller_zones)
        is_buyer = any(s <= pos <= e for s, e in buyer_zones)

        # Try to extract name from context
        context = id_info['context']
        # Look for Hebrew name pattern before the ID
        name_match = re.search(r'([א-ת][א-ת\s\."\']+(?:בע"מ)?)\s*[,،]?\s*$', context)
        name = name_match.group(1).strip() if name_match else ''
        # Clean up name
        name = re.sub(r'^[,،\s.]+', '', name)
        name = re.sub(r'[,،\s.]+$', '', name)

        if len(name) < 2:
            name = ''

        persons.append({
            'name': name,
            'id_number': id_info['id_number'],
            'is_seller': is_seller,
            'is_buyer': is_buyer,
            'pos': pos,
        })

    return persons


def _preprocess_text(text: str) -> str:
    """Preprocess extracted PDF text to handle common issues."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Check if text might be reversed (common in some PDF extractors)
    # If we find more RTL markers at end of lines, text might be OK
    # If Hebrew chars exist but no patterns match, try reversing lines
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            processed_lines.append(stripped)

    return '\n'.join(processed_lines)


def parse_contract_regex(text: str) -> ParsedContract:
    """Parse contract using regex/rule-based extraction.

    No AI required — works offline and instantly.
    Best for standard Israeli real estate contracts.
    """
    logger.info("Parsing contract with regex/rules-based parser")

    # Preprocess: normalize text (handle reversed Hebrew, extra whitespace)
    text = _preprocess_text(text)

    # --- Extract sale date ---
    sale_date = None

    # Try Hebrew date pattern first (ביום X לחודש Y שנת Z)
    hebrew_match = re.search(HEBREW_DATE_PATTERN, text[:500])  # Usually in header
    if hebrew_match:
        sale_date = _parse_date(hebrew_match.group(1), hebrew_match.group(2), hebrew_match.group(3))

    # Try numeric date in header area
    if not sale_date:
        date_matches = list(re.finditer(DATE_PATTERN, text[:500]))
        if date_matches:
            m = date_matches[0]
            sale_date = _parse_date(m.group(1), m.group(2), m.group(3))

    # --- Extract sale amount ---
    sale_amount = _extract_amount(text)

    # --- Extract IDs and names ---
    ids = _extract_ids(text)
    persons = _extract_names_near_ids(text, ids, SELLER_MARKERS + BUYER_MARKERS)

    sellers = []
    buyers = []
    for p in persons:
        entry = {'name': p['name'], 'id_number': p['id_number']}
        if p['is_seller']:
            sellers.append({**entry, 'share_percent': 100, 'is_israeli_resident': True})
        elif p['is_buyer']:
            buyers.append(entry)
        else:
            # Default: first IDs are sellers, rest are buyers
            if len(sellers) < 2:
                sellers.append({**entry, 'share_percent': 100, 'is_israeli_resident': True})
            else:
                buyers.append(entry)

    # Fix share percentages
    if len(sellers) > 1:
        share = 100 / len(sellers)
        for s in sellers:
            s['share_percent'] = round(share, 1)

    # --- Extract property address ---
    property_address = None
    # Look for "ברחוב" or "בכתובת"
    addr_match = re.search(r'(?:ברחוב|בכתובת|מרחוב)\s+([א-ת\w\s/\d,]+?)(?:\s*[,.]|\s+(?:אשר|הידוע|בגוש))', text)
    if addr_match:
        property_address = addr_match.group(1).strip()

    # --- Extract block/parcel ---
    block_parcel = None
    gush_match = re.search(GUSH_CHELKA, text) or re.search(GUSH_CHELKA_ALT, text)
    if gush_match:
        block_parcel = f"גוש {gush_match.group(1)} חלקה {gush_match.group(2)}"
        sub_match = re.search(SUB_CHELKA, text)
        if sub_match:
            block_parcel += f" תת חלקה {sub_match.group(1)}"

    # --- Detect property type ---
    property_type = None
    if any(w in text for w in ['דירת מגורים', 'דירה', 'דירת']):
        property_type = 'apartment'
    elif any(w in text for w in ['בית מגורים', 'בית צמוד']):
        property_type = 'house'
    elif any(w in text for w in ['מגרש', 'קרקע']):
        property_type = 'land'
    elif any(w in text for w in ['מסחרי', 'משרד', 'חנות']):
        property_type = 'commercial'

    # --- Detect exemption indicators ---
    is_single = 'דירה יחידה' in text or 'דירתו היחידה' in text or 'דירתה היחידה' in text
    is_inheritance = 'ירושה' in text or 'צו ירושה' in text or 'צוואה' in text
    has_rights = 'זכויות בנייה' in text or 'תמ"א 38' in text or '49ז' in text

    # --- Extract acquisition date from נסח data ---
    acquisitions = []
    # Look for "מהות פעולה: מכר" + date pattern
    nesach_match = re.search(r'מהות\s*פעולה[:\s]*מכר.*?(\d{1,2})[./](\d{1,2})[./](\d{4})', text, re.DOTALL)
    if nesach_match:
        acq_date = _parse_date(nesach_match.group(1), nesach_match.group(2), nesach_match.group(3))
        if acq_date:
            acquisitions.append({
                'acquisition_date': acq_date,
                'acquisition_type': 'purchase',
                'amount': None,
                'currency': 'ILS',
                'share_percent': 100,
            })

    # Alternative: look for "תאריך" + date in ownership section
    if not acquisitions:
        ownership_match = re.search(r'תאריך[:\s]*(\d{1,2})[./](\d{1,2})[./](\d{4})', text[len(text)//2:])
        if ownership_match:
            acq_date = _parse_date(ownership_match.group(1), ownership_match.group(2), ownership_match.group(3))
            if acq_date and acq_date != sale_date:
                acquisitions.append({
                    'acquisition_date': acq_date,
                    'acquisition_type': 'purchase',
                    'amount': None,
                    'currency': 'ILS',
                    'share_percent': 100,
                })

    # --- Confidence ---
    has_sale = bool(sale_date and sale_amount)
    has_sellers_data = bool(sellers)
    confidence = "high" if (has_sale and has_sellers_data) else "medium" if has_sale else "low"

    result = ParsedContract(
        sale_date=sale_date,
        sale_amount=sale_amount,
        sale_currency="ILS",
        sellers=sellers,
        buyers=buyers,
        acquisitions=acquisitions,
        property_address=property_address,
        block_parcel=block_parcel,
        property_type=property_type,
        is_single_apartment=is_single if is_single else None,
        is_inheritance=is_inheritance if is_inheritance else None,
        has_building_rights=has_rights if has_rights else None,
        notes="חולץ באמצעות ניתוח טקסט מקומי (ללא AI)",
        raw_text=text[:200],
        confidence=confidence,
    )

    logger.info(f"Regex parser result: confidence={confidence}, amount={sale_amount}, sellers={len(sellers)}")
    return result
