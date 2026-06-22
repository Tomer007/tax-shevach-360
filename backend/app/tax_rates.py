"""Tax rates and brackets for Israeli capital gains tax.

Tax rates by period:
- Before 7.11.2001: Marginal tax rates (up to 47%)
- 7.11.2001 - 31.12.2011: 20%
- 1.1.2012 - 31.12.2013: 25%
- Linear (qualifying residential): Exempt on portion before 1.1.2014, 25% on remainder
- Mas Yesaf (surtax): 3% above threshold + 2% additional from 2025 on capital income
"""

from datetime import date

# Key dates
DATE_2001_11_07 = date(2001, 11, 7)
DATE_2012_01_01 = date(2012, 1, 1)
DATE_2014_01_01 = date(2014, 1, 1)
DATE_2007_02_01 = date(2007, 2, 1)  # Depreciation for exempt track starts here

# Fixed tax rates by period
RATE_BEFORE_2001 = 0.47  # Marginal (simplified max)
RATE_2001_TO_2012 = 0.20
RATE_2012_TO_2014 = 0.25
RATE_LINEAR_POST_2014 = 0.25

# Mas Yesaf (surtax) thresholds
MAS_YESAF_THRESHOLD_2024 = 721_560
MAS_YESAF_THRESHOLD_2025 = 721_560  # Frozen 2025-2027
MAS_YESAF_RATE_BASE = 0.03
MAS_YESAF_RATE_ADDITIONAL_2025 = 0.02  # Additional 2% from 2025 on capital income

# Exemption thresholds (2024 values, updated annually by CPI)
EXEMPTION_49B2_CEILING = 5_008_000  # Full exemption ceiling for single apartment (2024)
BUILDING_RIGHTS_49Z_CEILING = 2_428_100  # Double exemption ceiling
BUILDING_RIGHTS_NEGLIGIBLE = 100_000  # Negligible building rights (Hora'at Biztua 6/98)

# Inflationary tax on pre-1994 inflationary amount
DATE_1994_01_01 = date(1994, 1, 1)
RATE_INFLATIONARY_PRE_1994 = 0.10

# Non-resident flat rate
RATE_NON_RESIDENT = 0.25

# Credit point value (annual, per point)
CREDIT_POINT_VALUES: dict[int, float] = {
    2020: 2628 * 12,
    2021: 2628 * 12,
    2022: 2748 * 12,
    2023: 2820 * 12,
    2024: 2904 * 12,
    2025: 2904 * 12,  # Frozen
    2026: 2904 * 12,
}

# Base credit points per resident
BASE_CREDIT_POINTS = 2.25


# Income tax brackets (2024-2027, frozen)
def get_tax_brackets(year: int, is_over_60: bool = False) -> list[tuple[float, float, float]]:
    """Get income tax brackets for a given year.

    Returns list of (lower_bound, upper_bound, rate).
    For ages 60+, the first bracket starts at 10% (Section 121(b)).
    """
    # 2024-2027 brackets (frozen)
    if is_over_60:
        return [
            (0, 84_120, 0.10),
            (84_120, 120_720, 0.14),
            (120_720, 193_800, 0.20),
            (193_800, 269_280, 0.31),
            (269_280, 560_280, 0.35),
            (560_280, 721_560, 0.47),
            (721_560, float("inf"), 0.50),
        ]
    else:
        return [
            (0, 84_120, 0.31),  # Passive income minimum is 31%
            (84_120, 120_720, 0.31),
            (120_720, 193_800, 0.31),
            (193_800, 269_280, 0.31),
            (269_280, 560_280, 0.35),
            (560_280, 721_560, 0.47),
            (721_560, float("inf"), 0.50),
        ]


def get_marginal_tax_brackets(year: int) -> list[tuple[float, float, float]]:
    """Get full marginal income tax brackets (for earned income / age 60+).

    Returns list of (lower_bound, upper_bound, rate).
    """
    return [
        (0, 84_120, 0.10),
        (84_120, 120_720, 0.14),
        (120_720, 193_800, 0.20),
        (193_800, 269_280, 0.31),
        (269_280, 560_280, 0.35),
        (560_280, 721_560, 0.47),
        (721_560, float("inf"), 0.50),
    ]


def calculate_tax_on_income(
    taxable_income: float,
    other_income: float = 0.0,
    year: int = 2024,
    is_over_60: bool = False,
    credit_points: float = BASE_CREDIT_POINTS,
) -> float:
    """Calculate income tax on taxable_income given other_income already taxed.

    The shevach is 'stacked' on top of other_income for bracket purposes.
    """
    if taxable_income <= 0:
        return 0.0

    brackets = get_marginal_tax_brackets(year) if is_over_60 else get_tax_brackets(year)

    # Tax on (other_income + taxable_income) minus tax on other_income
    tax_total = _calc_brackets(other_income + taxable_income, brackets)
    tax_other = _calc_brackets(other_income, brackets)
    tax_on_shevach = tax_total - tax_other

    # Apply credit points only for over-60 (earned income brackets)
    # For passive income (under 60), credit points are not applied on shevach
    if is_over_60 and other_income == 0:
        annual_credit = CREDIT_POINT_VALUES.get(year, 2904 * 12) * credit_points
        tax_on_shevach = max(0, tax_on_shevach - annual_credit)

    return max(0, tax_on_shevach)


def _calc_brackets(income: float, brackets: list[tuple[float, float, float]]) -> float:
    """Calculate total tax for given income using bracket list."""
    if income <= 0:
        return 0.0

    tax = 0.0
    for lower, upper, rate in brackets:
        if income <= lower:
            break
        taxable_in_bracket = min(income, upper) - lower
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate

    return tax


def calculate_mas_yesaf(
    real_shevach: float,
    sale_year: int,
    is_exempt: bool = False,
    sale_amount: float = 0.0,
    other_annual_income: float = 0.0,
) -> float:
    """Calculate Mas Yesaf (surtax).

    - 3% on total income above threshold (salary + shevach combined)
    - Additional 2% from 2025 on capital gains portion
    - Exempt residential under 5M with full exemption: no surtax
    """
    if is_exempt and sale_amount <= 5_000_000:
        return 0.0

    threshold = MAS_YESAF_THRESHOLD_2025 if sale_year >= 2025 else MAS_YESAF_THRESHOLD_2024

    # The threshold applies to total income (other + shevach)
    total_income = other_annual_income + real_shevach
    if total_income <= threshold:
        return 0.0

    # Tax the shevach portion that exceeds the threshold after other income
    # If other_income already exceeds threshold, all shevach is taxable
    taxable_base = max(0, total_income - threshold)
    # But only the shevach portion (not the other income) pays here
    taxable = min(real_shevach, taxable_base)

    yesaf = taxable * MAS_YESAF_RATE_BASE

    if sale_year >= 2025:
        yesaf += taxable * MAS_YESAF_RATE_ADDITIONAL_2025

    return yesaf


def calculate_inflationary_tax(
    inflationary_amount: float,
    acquisition_date: date,
) -> float:
    """Calculate tax on inflationary amount (Section 48a(d)).

    Inflationary gain accrued before 1.1.1994 is taxed at 10%.
    Inflationary gain after 1.1.1994 is exempt.
    """
    if inflationary_amount <= 0:
        return 0.0

    if acquisition_date >= DATE_1994_01_01:
        # All inflationary amount is post-1994 = exempt
        return 0.0

    # All inflationary gain is pre-1994 (simplified: if acquired before 1994)
    return inflationary_amount * RATE_INFLATIONARY_PRE_1994


def calculate_partial_exemption(sale_amount: float, ceiling: float) -> float:
    """Calculate partial exemption ratio when sale exceeds ceiling.

    Formula per Section 49א(א1): the exempt portion of shevach is
    (ceiling / sale_amount). Returns the RATIO to multiply by shevach.
    """
    if sale_amount <= ceiling:
        return 1.0  # Fully exempt (ratio = 100%)

    # Partial: exempt ratio = ceiling / sale_amount
    return ceiling / sale_amount
