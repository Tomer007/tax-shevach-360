"""Bank of Israel API client for exchange rates and CPI data.

Fetches live data from edge.boi.gov.il for:
- Exchange rates (USD, EUR, GBP to ILS)
- CPI monthly data

Historical currency conversions:
- ILP (Israeli Lira) before Feb 1980: 1 ILP = 0.000001 ILS
- ILR (Old Israeli Shekel) 1980-1985: 1 ILR = 0.001 ILS
"""

from datetime import date, timedelta

import httpx

from app.models import Currency

# BOI API base URL
BOI_BASE_URL = "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STAT"

# Currency conversion constants for historical currencies
ILP_TO_ILS = 0.000001  # Israeli Lira to New Shekel
ILR_TO_ILS = 0.001  # Old Shekel to New Shekel

# Exchange rate series codes
EXCHANGE_RATE_SERIES = {
    Currency.USD: "EXR/RER_USD_ILS",
    Currency.EUR: "EXR/RER_EUR_ILS",
    Currency.GBP: "EXR/RER_GBP_ILS",
}

# Timeout for API calls (seconds)
API_TIMEOUT = 4.0


async def fetch_exchange_rate(currency: Currency, target_date: date) -> float | None:
    """Fetch exchange rate from Bank of Israel API.

    Searches ±7 days if exact date not available (weekends, holidays).
    Returns rate in ILS per 1 unit of foreign currency, or None if unavailable.
    """
    # Historical currencies - fixed conversion
    if currency == Currency.ILP:
        return ILP_TO_ILS
    if currency == Currency.ILR:
        return ILR_TO_ILS
    if currency == Currency.ILS:
        return 1.0

    series = EXCHANGE_RATE_SERIES.get(currency)
    if not series:
        return None

    # Try exact date first, then ±7 days
    for offset in range(8):
        for sign in [0, -1, 1] if offset == 0 else [-1, 1]:
            check_date = target_date + timedelta(days=offset * sign)
            rate = await _fetch_rate_for_date(series, check_date)
            if rate is not None:
                return rate

    return None


async def _fetch_rate_for_date(series: str, target_date: date) -> float | None:
    """Fetch a single rate for a specific date."""
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"{BOI_BASE_URL}/{series}?startperiod={date_str}&endperiod={date_str}&format=csv"

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code == 200:
                lines = response.text.strip().split("\n")
                if len(lines) >= 2:
                    # CSV format: last column is the value
                    value_str = lines[-1].split(",")[-1].strip()
                    return float(value_str)
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, IndexError):
        pass

    return None


def convert_to_ils(amount: float, currency: Currency, rate: float | None) -> float:
    """Convert an amount to ILS using the given rate.

    For ILS, returns amount unchanged.
    For historical currencies (ILP, ILR), uses fixed conversion.
    """
    if currency == Currency.ILS:
        return amount
    if currency == Currency.ILP:
        return amount * ILP_TO_ILS
    if currency == Currency.ILR:
        return amount * ILR_TO_ILS
    if rate is None:
        # Fallback: return amount as-is (assume ILS)
        return amount
    return amount * rate
