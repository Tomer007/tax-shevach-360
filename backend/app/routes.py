"""API routes for the calculator."""

from datetime import date

from fastapi import APIRouter, HTTPException

from app.boi_api import convert_to_ils, fetch_exchange_rate
from app.calculator import (
    calculate_days_breakdown,
    calculate_linear_tax,
    calculate_prisa,
    calculate_regular_tax,
    calculate_transaction,
    check_49z_building_rights,
)
from app.cpi_data import get_cpi_for_year, get_indexation_ratio
from app.models import (
    CalculationResult,
    Currency,
    ExemptionCheck,
    TransactionInput,
)

router = APIRouter()


@router.post("/calculate", response_model=CalculationResult)
def calculate(txn: TransactionInput) -> CalculationResult:
    """Calculate capital gains tax for a transaction."""
    try:
        return calculate_transaction(txn)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid input: {e}")
    except ZeroDivisionError as e:
        raise HTTPException(status_code=422, detail=f"Calculation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal calculation error: {type(e).__name__}")


@router.get("/cpi/{year}")
def get_cpi(year: int):
    """Get CPI value for a given year."""
    if year < 1950 or year > 2030:
        raise HTTPException(status_code=400, detail="Year must be between 1950 and 2030")
    return {"year": year, "cpi": get_cpi_for_year(year)}


@router.get("/indexation")
def get_indexation(acquisition_year: int, sale_year: int):
    """Get CPI indexation ratio between two years."""
    if acquisition_year < 1950 or sale_year > 2030:
        raise HTTPException(status_code=400, detail="Invalid year range")
    ratio = get_indexation_ratio(acquisition_year, sale_year)
    return {
        "acquisition_year": acquisition_year,
        "sale_year": sale_year,
        "cpi_acquisition": get_cpi_for_year(acquisition_year),
        "cpi_sale": get_cpi_for_year(sale_year),
        "ratio": ratio,
    }


@router.get("/exchange-rate")
async def get_exchange_rate(currency: Currency, target_date: date):
    """Fetch exchange rate from Bank of Israel."""
    rate = await fetch_exchange_rate(currency, target_date)
    if rate is None:
        raise HTTPException(status_code=404, detail=f"Rate not found for {currency} on {target_date}")
    return {"currency": currency, "date": str(target_date), "rate": rate}


@router.post("/convert-currency")
async def convert_currency(amount: float, currency: Currency, target_date: date):
    """Convert amount to ILS using BOI rate."""
    rate = await fetch_exchange_rate(currency, target_date)
    ils_amount = convert_to_ils(amount, currency, rate)
    return {
        "original_amount": amount,
        "currency": currency,
        "rate": rate,
        "ils_amount": ils_amount,
    }


@router.post("/check-49z")
def check_building_rights(exemption: ExemptionCheck):
    """Check building rights exemption eligibility."""
    return check_49z_building_rights(exemption)


@router.post("/prisa-comparison")
def compare_prisa(
    taxable_shevach: float,
    sale_year: int,
    birth_year: int,
    annual_incomes: dict[int, float] | None = None,
    max_years: list[int] | None = None,
):
    """Compare prisa options (1-4 years)."""
    incomes = annual_incomes or {}
    max_yrs = max_years or []
    results = []
    for years in range(1, 5):
        prisa = calculate_prisa(
            taxable_shevach=taxable_shevach,
            sale_year=sale_year,
            seller_birth_year=birth_year,
            annual_incomes=incomes,
            max_years=max_yrs,
            num_years=years,
        )
        results.append(prisa)
    return {"comparison": results}
