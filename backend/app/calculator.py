"""Core calculation engine for Mas Shevach (Capital Gains Tax).

Implements:
- Per-acquisition and per-deduction CPI indexation
- Currency conversion at acquisition date
- Linear calculation (Linari Mutav) for qualifying residential property
- Period-based tax rate application
- Prisa (spreading) with manual/max mode per year
- Mas Yesaf (surtax) with other income stacking
- Inflationary tax (Section 48a(d)) on pre-1994 amounts
- Partial exemption for sales above ceiling
- Non-resident flat rate
- Building rights (49z) calculation
- Multi-seller split
"""

from datetime import date

from app.boi_api import ILP_TO_ILS, ILR_TO_ILS, fetch_exchange_rate_sync
from app.cpi_data import get_cpi_for_year, get_indexation_ratio
from app.depreciation import calculate_depreciation
from app.models import (
    AcquisitionPart,
    CalculationResult,
    ComparisonRoute,
    Currency,
    Deduction,
    ExemptionCheck,
    PrisaResult,
    PrisaYearResult,
    SellerResult,
    TaxPeriodBreakdown,
    TransactionInput,
)
from app.tax_rates import (
    BUILDING_RIGHTS_49Z_CEILING,
    BUILDING_RIGHTS_NEGLIGIBLE,
    DATE_2001_11_07,
    DATE_2012_01_01,
    DATE_2014_01_01,
    EXEMPTION_49B2_CEILING,
    RATE_LINEAR_POST_2014,
    RATE_NON_RESIDENT,
    calculate_inflationary_tax,
    calculate_mas_yesaf,
    calculate_partial_exemption,
    calculate_tax_on_income,
)


def _convert_to_ils_static(amount: float | None, currency: Currency) -> float:
    """Convert amount to ILS using fixed historical rates (for non-API contexts).

    For ILS: return as-is.
    For ILP/ILR: use fixed conversion.
    For USD/EUR/GBP: return as-is (caller should provide ILS or use API).
    """
    if amount is None:
        return 0.0
    if currency == Currency.ILS:
        return amount
    if currency == Currency.ILP:
        return amount * ILP_TO_ILS
    if currency == Currency.ILR:
        return amount * ILR_TO_ILS
    # For foreign currencies without live rate, treat as ILS (best effort)
    return amount


def _convert_to_ils_with_date(amount: float | None, currency: Currency, acq_date: date) -> float:
    """Convert amount to ILS using Bank of Israel historical rate for the given date.

    Falls back to treating as ILS if rate unavailable.
    """
    if amount is None:
        return 0.0
    if currency == Currency.ILS:
        return amount
    if currency == Currency.ILP:
        return amount * ILP_TO_ILS
    if currency == Currency.ILR:
        return amount * ILR_TO_ILS

    # Fetch historical rate from Bank of Israel
    rate = fetch_exchange_rate_sync(currency, acq_date)
    if rate is not None:
        return amount * rate
    # Fallback: return as-is
    return amount


def _index_acquisition(acq: AcquisitionPart, sale_year: int) -> float:
    """Index a single acquisition part from its own date to sale year."""
    amount_ils = _convert_to_ils_with_date(acq.amount, acq.currency, acq.acquisition_date)
    ratio = get_indexation_ratio(acq.acquisition_date.year, sale_year)
    return amount_ils * ratio


def _index_deduction(ded: Deduction, sale_year: int) -> float:
    """Index a single deduction from its own date to sale year."""
    amount_ils = _convert_to_ils_static(ded.amount, ded.currency)
    ratio = get_indexation_ratio(ded.deduction_date.year, sale_year)
    return amount_ils * ratio


def calculate_days_breakdown(acquisition_date: date, sale_date: date) -> TaxPeriodBreakdown:
    """Calculate number of days in each tax period."""
    total_days = (sale_date - acquisition_date).days
    if total_days <= 0:
        return TaxPeriodBreakdown(
            days_total=0,
            days_before_2001_11_07=0,
            days_2001_to_2012=0,
            days_after_2012=0,
            days_to_2014_01_01=0,
            days_after_2014=0,
        )

    # Days before 7.11.2001
    if acquisition_date >= DATE_2001_11_07:
        days_before_2001 = 0
    elif sale_date <= DATE_2001_11_07:
        days_before_2001 = total_days
    else:
        days_before_2001 = (DATE_2001_11_07 - acquisition_date).days

    # Days 7.11.2001 to 31.12.2011
    period_start = max(acquisition_date, DATE_2001_11_07)
    period_end = min(sale_date, DATE_2012_01_01)
    days_2001_to_2012 = max(0, (period_end - period_start).days)

    # Days after 1.1.2012
    if sale_date <= DATE_2012_01_01:
        days_after_2012 = 0
    elif acquisition_date >= DATE_2012_01_01:
        days_after_2012 = total_days
    else:
        days_after_2012 = (sale_date - DATE_2012_01_01).days

    # Days to 1.1.2014 (for linari mutav)
    if acquisition_date >= DATE_2014_01_01:
        days_to_2014 = 0
    elif sale_date <= DATE_2014_01_01:
        days_to_2014 = total_days
    else:
        days_to_2014 = (DATE_2014_01_01 - acquisition_date).days

    # Days after 1.1.2014
    days_after_2014 = total_days - days_to_2014

    return TaxPeriodBreakdown(
        days_total=total_days,
        days_before_2001_11_07=days_before_2001,
        days_2001_to_2012=days_2001_to_2012,
        days_after_2012=days_after_2012,
        days_to_2014_01_01=days_to_2014,
        days_after_2014=days_after_2014,
    )


def calculate_linear_tax(real_shevach: float, breakdown: TaxPeriodBreakdown) -> float:
    """Calculate tax using linear mutav method.

    Portion before 1.1.2014 = exempt (0%)
    Portion after 1.1.2014 = 25%
    """
    if breakdown.days_total <= 0:
        return 0.0

    ratio_after_2014 = breakdown.days_after_2014 / breakdown.days_total
    taxable_shevach = real_shevach * ratio_after_2014
    return taxable_shevach * RATE_LINEAR_POST_2014


def calculate_regular_tax(real_shevach: float, breakdown: TaxPeriodBreakdown) -> float:
    """Calculate tax using regular (non-linear) method with period rates."""
    if breakdown.days_total <= 0:
        return 0.0

    tax = 0.0

    # Before 7.11.2001: marginal rates (simplified to max 47%)
    if breakdown.days_before_2001_11_07 > 0:
        ratio = breakdown.days_before_2001_11_07 / breakdown.days_total
        tax += real_shevach * ratio * 0.47

    # 7.11.2001 - 31.12.2011: 20%
    if breakdown.days_2001_to_2012 > 0:
        ratio = breakdown.days_2001_to_2012 / breakdown.days_total
        tax += real_shevach * ratio * 0.20

    # After 1.1.2012: 25%
    if breakdown.days_after_2012 > 0:
        ratio = breakdown.days_after_2012 / breakdown.days_total
        tax += real_shevach * ratio * 0.25

    return tax


def calculate_non_resident_tax(real_shevach: float) -> float:
    """Calculate flat-rate tax for non-Israeli residents (25% from day one)."""
    return real_shevach * RATE_NON_RESIDENT


def calculate_prisa(
    taxable_shevach: float,
    sale_year: int,
    seller_birth_year: int,
    annual_incomes: dict[int, float],
    max_years: list[int],
    num_years: int,
    base_rate: float = RATE_LINEAR_POST_2014,
) -> PrisaResult:
    """Calculate tax with prisa (spreading) over num_years.

    Per Section 48ב, during prisa the shevach is treated as EARNED income,
    so regular marginal brackets (10%, 14%, 20%...) apply with credit points.

    For each year:
    - If year is in max_years: tax = min(calculated, base_rate * spread amount)
    - Otherwise: use marginal brackets with given income
    """
    if num_years <= 0:
        return PrisaResult(
            years=0,
            year_results=[],
            total_tax=taxable_shevach * base_rate,
            tax_without_prisa=taxable_shevach * base_rate,
            savings=0.0,
        )

    tax_without_prisa = taxable_shevach * base_rate
    spread_per_year = taxable_shevach / num_years
    is_over_60 = (sale_year - seller_birth_year) >= 60

    year_results: list[PrisaYearResult] = []
    total_tax = 0.0

    for i in range(num_years):
        year = sale_year - i  # Current year first, then backwards
        is_max = year in max_years

        if is_max:
            # Max mode: base_rate cap (as if no prisa benefit for this year)
            year_tax = spread_per_year * base_rate
            other_income = 0.0
        else:
            other_income = annual_incomes.get(year, 0.0)
            # Per Section 48ב: during prisa, shevach is treated as earned income
            # Use marginal brackets (is_over_60=True gives full marginal brackets)
            year_tax = calculate_tax_on_income(
                taxable_income=spread_per_year,
                other_income=other_income,
                year=year,
                is_over_60=True,  # Marginal brackets apply to ALL sellers during prisa
            )
            # Cap: never exceed base_rate
            max_tax = spread_per_year * base_rate
            year_tax = min(year_tax, max_tax)

        year_results.append(
            PrisaYearResult(
                year=year,
                spread_amount=spread_per_year,
                other_income=other_income,
                total_taxable=other_income + spread_per_year,
                tax_calculated=year_tax,
                is_max_mode=is_max,
            )
        )
        total_tax += year_tax

    savings = tax_without_prisa - total_tax

    return PrisaResult(
        years=num_years,
        year_results=year_results,
        total_tax=total_tax,
        tax_without_prisa=tax_without_prisa,
        savings=max(0, savings),
    )


def check_49z_building_rights(exemption: ExemptionCheck) -> dict:
    """Calculate building rights exemption under Section 49z."""
    if not exemption.has_building_rights:
        return {"applicable": False, "exempt_amount": 0.0, "taxable_amount": 0.0}

    rights_value = exemption.building_rights_value
    apt_value = exemption.apartment_value_without_rights

    if rights_value <= BUILDING_RIGHTS_NEGLIGIBLE:
        return {
            "applicable": True,
            "exempt_amount": rights_value,
            "taxable_amount": 0.0,
            "reason": "negligible_rights",
        }

    if apt_value <= BUILDING_RIGHTS_49Z_CEILING:
        exempt = min(rights_value, BUILDING_RIGHTS_49Z_CEILING - apt_value)
        taxable = max(0, rights_value - exempt)
        return {
            "applicable": True,
            "exempt_amount": exempt,
            "taxable_amount": taxable,
            "reason": "double_exemption",
        }

    return {
        "applicable": True,
        "exempt_amount": 0.0,
        "taxable_amount": rights_value,
        "reason": "above_ceiling",
    }


def calculate_transaction(txn: TransactionInput) -> CalculationResult:
    """Main entry point: calculate complete tax for a transaction."""
    seller_results: list[SellerResult] = []
    sale_year = txn.sale_date.year
    sale_amount = txn.sale_amount

    # Use earliest acquisition date for period breakdown
    earliest_acquisition = min(a.acquisition_date for a in txn.acquisitions)
    breakdown = calculate_days_breakdown(earliest_acquisition, txn.sale_date)

    # --- FIX #2: Per-acquisition indexation ---
    # Each acquisition is indexed from its own date
    acquisition_indexed = sum(_index_acquisition(a, sale_year) for a in txn.acquisitions)
    total_acquisition_ils = sum(
        _convert_to_ils_with_date(a.amount, a.currency, a.acquisition_date) for a in txn.acquisitions
    )

    # --- FIX #1: Per-deduction indexation ---
    deductions_indexed = sum(_index_deduction(d, sale_year) for d in txn.deductions)

    # Betterment levy (deductible, indexed from sale year = ratio 1.0)
    betterment_indexed = txn.betterment_levy

    total_cost_indexed = acquisition_indexed + deductions_indexed + betterment_indexed

    # --- FIX #4: Depreciation reduces cost directly (not re-indexed) ---
    depreciation_amount = calculate_depreciation(txn.depreciation, total_acquisition_ils)
    # Depreciation reduces cost basis (increases shevach) - NOT multiplied by indexation
    total_cost_indexed -= depreciation_amount

    # CPI data for reporting (use weighted average for display)
    cpi_sale = get_cpi_for_year(sale_year)
    cpi_acq = get_cpi_for_year(earliest_acquisition.year)
    indexation_ratio = get_indexation_ratio(earliest_acquisition.year, sale_year)

    # Shevach calculation
    shevach_mekarkein = sale_amount - total_cost_indexed
    if shevach_mekarkein < 0:
        shevach_mekarkein = 0.0

    # Inflationary amount (sum of per-acquisition inflationary gains)
    inflationary = 0.0
    for acq in txn.acquisitions:
        acq_ils = _convert_to_ils_with_date(acq.amount, acq.currency, acq.acquisition_date)
        ratio = get_indexation_ratio(acq.acquisition_date.year, sale_year)
        if ratio > 1:
            inflationary += acq_ils * (ratio - 1)

    # Real shevach
    real_shevach = shevach_mekarkein - inflationary
    if real_shevach < 0:
        real_shevach = 0.0

    # --- FIX #7: Inflationary tax on pre-1994 portion ---
    tax_inflationary = calculate_inflationary_tax(inflationary, earliest_acquisition)

    # Linear split
    shevach_to_2014 = 0.0
    shevach_after_2014 = 0.0
    if breakdown.days_total > 0:
        ratio_to_2014 = breakdown.days_to_2014_01_01 / breakdown.days_total
        shevach_to_2014 = real_shevach * ratio_to_2014
        shevach_after_2014 = real_shevach * (1 - ratio_to_2014)

    # --- FIX #14: Partial exemption ---
    is_exempt = False
    partial_exemption_ratio = 0.0
    if txn.exemption.is_single_apartment and txn.exemption.ownership_months >= 18:
        if sale_amount <= EXEMPTION_49B2_CEILING:
            is_exempt = True
        else:
            # Partial exemption: exempt_ratio = ceiling / sale_amount
            partial_exemption_ratio = calculate_partial_exemption(sale_amount, EXEMPTION_49B2_CEILING)

    # --- FIX #5: Linear qualification check ---
    # Linear mutav (תיקון 76) requires: residential property AND acquired before 1.1.2014
    is_linear_eligible = txn.is_residential and earliest_acquisition < DATE_2014_01_01

    # Route taxes
    if is_linear_eligible:
        tax_linear = calculate_linear_tax(real_shevach, breakdown)
    else:
        tax_linear = calculate_regular_tax(real_shevach, breakdown)  # Fallback to regular

    tax_regular = calculate_regular_tax(real_shevach, breakdown)

    # Per-seller calculation
    for seller in txn.sellers:
        share = seller.share_percent / 100.0
        seller_real_shevach = real_shevach * share
        seller_shevach_after_2014 = shevach_after_2014 * share

        # --- FIX #15: Non-resident tax ---
        if not seller.is_israeli_resident:
            # Non-residents get 25% flat, but can still use linear for pre-2014 acquisitions
            seller_tax_non_resident = calculate_non_resident_tax(seller_real_shevach)
            if is_linear_eligible:
                seller_tax_linear = min(tax_linear * share, seller_tax_non_resident)
            else:
                seller_tax_linear = seller_tax_non_resident
            seller_tax_regular = seller_tax_non_resident
        else:
            seller_tax_linear = tax_linear * share
            seller_tax_regular = tax_regular * share

        # --- FIX #9: Prisa on both linear and regular routes ---
        seller_birth_year = seller.birth_date.year if seller.birth_date else sale_year - 45  # Default age ~45 if unknown
        best_prisa: PrisaResult | None = None
        prisa_comparison: list[PrisaResult] = []

        if seller.is_israeli_resident:
            for years in range(1, 5):
                # Linear prisa (on post-2014 portion)
                prisa_linear = calculate_prisa(
                    taxable_shevach=seller_shevach_after_2014,
                    sale_year=sale_year,
                    seller_birth_year=seller_birth_year,
                    annual_incomes=seller.annual_incomes,
                    max_years=seller.prisa_max_years,
                    num_years=years,
                    base_rate=RATE_LINEAR_POST_2014,
                )
                prisa_comparison.append(prisa_linear)
                if best_prisa is None or prisa_linear.total_tax < best_prisa.total_tax:
                    best_prisa = prisa_linear

        seller_tax_prisa = best_prisa.total_tax if best_prisa else seller_tax_linear

        # Use requested prisa years if specified
        if txn.prisa_years > 0 and seller.is_israeli_resident:
            requested_prisa = calculate_prisa(
                taxable_shevach=seller_shevach_after_2014,
                sale_year=sale_year,
                seller_birth_year=seller_birth_year,
                annual_incomes=seller.annual_incomes,
                max_years=seller.prisa_max_years,
                num_years=txn.prisa_years,
                base_rate=RATE_LINEAR_POST_2014,
            )
            seller_tax_prisa = requested_prisa.total_tax

        # --- FIX #6: Mas Yesaf with other income ---
        # Use the seller's income from sale year for stacking
        seller_other_income = seller.annual_incomes.get(sale_year, 0.0)
        mas_yesaf = calculate_mas_yesaf(
            real_shevach=seller_real_shevach,
            sale_year=sale_year,
            is_exempt=is_exempt,
            sale_amount=sale_amount * share,
            other_annual_income=seller_other_income,
        )

        # Inflationary tax per seller
        seller_tax_inflationary = tax_inflationary * share

        # Best route
        if is_exempt:
            total_tax = mas_yesaf + seller_tax_inflationary
            recommended = "exempt_49b2"
        elif not seller.is_israeli_resident:
            total_tax = seller_tax_linear + mas_yesaf + seller_tax_inflationary
            recommended = "non_resident_flat"
        elif not is_linear_eligible:
            # No linear option - compare regular vs prisa on regular
            total_tax = seller_tax_regular + mas_yesaf + seller_tax_inflationary
            recommended = "regular"
        elif seller_tax_prisa < seller_tax_linear:
            total_tax = seller_tax_prisa + mas_yesaf + seller_tax_inflationary
            recommended = "linear_with_prisa"
        elif seller_tax_linear <= seller_tax_regular:
            total_tax = seller_tax_linear + mas_yesaf + seller_tax_inflationary
            recommended = "linear"
        else:
            total_tax = seller_tax_regular + mas_yesaf + seller_tax_inflationary
            recommended = "regular"

        seller_results.append(
            SellerResult(
                seller_name=seller.name,
                share_percent=seller.share_percent,
                sale_amount_ils=sale_amount * share,
                acquisition_amount_ils_indexed=acquisition_indexed * share,
                deductions_total_indexed=deductions_indexed * share,
                total_cost_indexed=total_cost_indexed * share,
                shevach_mekarkein=shevach_mekarkein * share,
                inflationary_amount=inflationary * share,
                real_shevach=seller_real_shevach,
                period_breakdown=breakdown,
                shevach_to_2014=shevach_to_2014 * share,
                shevach_after_2014=shevach_after_2014 * share,
                tax_linear=seller_tax_linear,
                tax_regular=seller_tax_regular,
                tax_with_prisa=seller_tax_prisa,
                tax_inflationary=seller_tax_inflationary,
                mas_yesaf=mas_yesaf,
                total_tax=total_tax,
                recommended_route=recommended,
                prisa_result=best_prisa,
                depreciation_amount=depreciation_amount * share,
                partial_exemption_amount=partial_exemption_ratio * seller_real_shevach,
                cpi_acquisition=cpi_acq,
                cpi_sale=cpi_sale,
                indexation_ratio=indexation_ratio,
            )
        )

    # Route comparison (full transaction)
    routes: list[ComparisonRoute] = []
    full_tax_linear = sum(s.tax_linear for s in seller_results)
    full_tax_regular = sum(s.tax_regular for s in seller_results)
    full_tax_best = sum(s.total_tax for s in seller_results)

    if is_linear_eligible:
        routes.append(
            ComparisonRoute(
                route_name="linear_mutav",
                tax_amount=full_tax_linear,
                effective_rate=full_tax_linear / sale_amount * 100 if sale_amount > 0 else 0,
                savings_vs_regular=full_tax_regular - full_tax_linear,
            )
        )
    routes.append(
        ComparisonRoute(
            route_name="regular",
            tax_amount=full_tax_regular,
            effective_rate=full_tax_regular / sale_amount * 100 if sale_amount > 0 else 0,
            savings_vs_regular=0.0,
        )
    )
    if is_exempt:
        routes.append(
            ComparisonRoute(
                route_name="exempt_49b2",
                tax_amount=0.0,
                effective_rate=0.0,
                savings_vs_regular=full_tax_regular,
            )
        )

    return CalculationResult(
        seller_results=seller_results,
        full_shevach_mekarkein=shevach_mekarkein,
        full_inflationary=inflationary,
        full_real_shevach=real_shevach,
        full_tax=full_tax_best,
        route_comparison=routes,
        prisa_comparison=prisa_comparison if len(txn.sellers) == 1 else [],
    )
