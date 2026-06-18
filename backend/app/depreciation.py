"""Depreciation (Pachot) calculation module.

Rules:
- 1989 Regulations: 2% of FULL value (including land) - default for residential
- 1941 Regulations: Various rates on BUILDING portion only (2/3 of value by default)
- Rental tax track affects applicability:
  - Marginal: Full depreciation
  - 10% flat: Deemed depreciation (Section 122c)
  - Exempt: Only from 1.2.2007 (Hora'at Biztua 5/2007, Viman ruling)
  - Exempt + Chen ruling (2024): Zero depreciation
"""

from datetime import date

from app.models import (
    DepreciationInput,
    DepreciationRate,
    RentalPeriod,
    RentalTaxTrack,
)

# Depreciation rate mappings
RATE_VALUES: dict[DepreciationRate, float] = {
    DepreciationRate.RATE_2_FULL: 0.02,
    DepreciationRate.RATE_1_5_BUILDING: 0.015,
    DepreciationRate.RATE_2_BUILDING: 0.02,
    DepreciationRate.RATE_4_BUILDING: 0.04,
    DepreciationRate.RATE_6_5_BUILDING: 0.065,
    DepreciationRate.RATE_4_TIAUMIM: 0.04,
}

# Whether rate applies to full value or building only
APPLIES_TO_FULL: dict[DepreciationRate, bool] = {
    DepreciationRate.RATE_2_FULL: True,
    DepreciationRate.RATE_1_5_BUILDING: False,
    DepreciationRate.RATE_2_BUILDING: False,
    DepreciationRate.RATE_4_BUILDING: False,
    DepreciationRate.RATE_6_5_BUILDING: False,
    DepreciationRate.RATE_4_TIAUMIM: False,
}

# Date from which exempt track incurs depreciation
EXEMPT_DEPRECIATION_START = date(2007, 2, 1)


def calculate_depreciation(
    dep_input: DepreciationInput,
    acquisition_amount: float,
) -> float:
    """Calculate total depreciation amount.

    Args:
        dep_input: Depreciation configuration
        acquisition_amount: Original acquisition cost (in ILS)

    Returns:
        Total depreciation amount to deduct from cost basis (increases shevach)
    """
    if dep_input.mode == "manual":
        return dep_input.manual_amount

    # Auto calculation
    total_depreciation = 0.0

    for period in dep_input.rental_periods:
        period_dep = _calculate_period_depreciation(
            period=period,
            acquisition_amount=acquisition_amount,
            land_ratio=dep_input.land_ratio,
        )
        total_depreciation += period_dep

    return total_depreciation


def _calculate_period_depreciation(
    period: RentalPeriod,
    acquisition_amount: float,
    land_ratio: float,
) -> float:
    """Calculate depreciation for a single rental period."""
    # Chen ruling (2024): zero depreciation for exempt track
    if period.tax_track == RentalTaxTrack.EXEMPT_CHEN:
        return 0.0

    # Determine effective period
    effective_start = period.start_date
    effective_end = period.end_date

    # Exempt track: only from 1.2.2007
    if period.tax_track == RentalTaxTrack.EXEMPT:
        if effective_end < EXEMPT_DEPRECIATION_START:
            return 0.0
        if effective_start < EXEMPT_DEPRECIATION_START:
            effective_start = EXEMPT_DEPRECIATION_START

    # Calculate years (can be fractional)
    days = (effective_end - effective_start).days
    if days <= 0:
        return 0.0
    years = days / 365.25

    # Get rate and base
    rate = RATE_VALUES[period.depreciation_rate]
    applies_full = APPLIES_TO_FULL[period.depreciation_rate]

    if applies_full:
        base = acquisition_amount
    else:
        building_ratio = 1.0 - land_ratio
        base = acquisition_amount * building_ratio

    depreciation = base * rate * years

    # Cap: depreciation cannot exceed the base value
    max_depreciation = base
    if depreciation > max_depreciation:
        return max_depreciation
    return depreciation
