"""Pydantic models for the Mas Shevach calculator."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    """Supported currencies."""

    ILS = "ILS"  # New Israeli Shekel
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    ILP = "ILP"  # Israeli Lira (before Feb 1980)
    ILR = "ILR"  # Old Israeli Shekel (1980-1985)


class AcquisitionType(str, Enum):
    """How the property was acquired."""

    PURCHASE = "purchase"
    INHERITANCE = "inheritance"
    GIFT = "gift"
    DIVORCE = "divorce"


class RentalTaxTrack(str, Enum):
    """Tax track for rental income."""

    MARGINAL = "marginal"  # Full marginal tax - full depreciation
    FLAT_10 = "flat_10"  # 10% flat - deemed depreciation (122c)
    EXEMPT = "exempt"  # Exempt - depreciation from 1.2.2007 only
    EXEMPT_CHEN = "exempt_chen"  # Exempt + Psa"d Chen (2024) - zero depreciation


class DepreciationRate(str, Enum):
    """Depreciation rate options."""

    RATE_2_FULL = "2_full"  # 2% of full value (1989 regulations, default for residential)
    RATE_1_5_BUILDING = "1.5_building"  # 1.5% of building (2/3) - pure stone
    RATE_2_BUILDING = "2_building"  # 2% of building (2/3) - pure reinforced concrete
    RATE_4_BUILDING = "4_building"  # 4% of building (2/3) - concrete + blocks (most common)
    RATE_6_5_BUILDING = "6.5_building"  # 6.5% of building (2/3) - old/poor construction
    RATE_4_TIAUMIM = "4_tiaumim"  # 4% of building - Tiaumim law (1985)


class Seller(BaseModel):
    """Seller information."""

    name: str
    id_number: str
    birth_date: date
    share_percent: float = Field(ge=0, le=100, description="Ownership share %")
    is_israeli_resident: bool = True
    marital_status: str = "single"
    # Income data for prisa (spreading)
    annual_incomes: dict[int, float] = Field(
        default_factory=dict,
        description="Annual income by year for prisa calculation",
    )
    # Per-year max mode for prisa
    prisa_max_years: list[int] = Field(
        default_factory=list,
        description="Years where max mode (25% cap) applies instead of manual income",
    )


class AcquisitionPart(BaseModel):
    """A single acquisition event (property may have multiple)."""

    acquisition_date: date
    acquisition_type: AcquisitionType = AcquisitionType.PURCHASE
    amount: float = Field(gt=0)
    currency: Currency = Currency.ILS
    share_percent: float = Field(ge=0, le=100, description="Share acquired in this event")
    # For inheritance
    deceased_eligible_for_exemption: bool = False


class Deduction(BaseModel):
    """An allowed deduction (nikui)."""

    description: str
    amount: float = Field(ge=0)
    currency: Currency = Currency.ILS
    deduction_date: date


class RentalPeriod(BaseModel):
    """A period during which the property was rented out."""

    start_date: date
    end_date: date
    tax_track: RentalTaxTrack = RentalTaxTrack.FLAT_10
    depreciation_rate: DepreciationRate = DepreciationRate.RATE_2_FULL


class DepreciationInput(BaseModel):
    """Depreciation configuration."""

    mode: str = Field(default="manual", description="'manual' or 'auto'")
    manual_amount: float = 0.0
    rental_periods: list[RentalPeriod] = Field(default_factory=list)
    land_ratio: float = Field(default=1 / 3, ge=0, le=1, description="Land portion (default 1/3)")


class ExemptionCheck(BaseModel):
    """Exemption eligibility data."""

    is_single_apartment: bool = False
    ownership_months: int = 0
    is_inheritance: bool = False
    has_building_rights: bool = False
    building_rights_value: float = 0.0
    apartment_value_without_rights: float = 0.0


class TransactionInput(BaseModel):
    """Complete transaction input for calculation."""

    # Sale details
    sale_date: date
    sale_amount: float = Field(gt=0)
    sale_currency: Currency = Currency.ILS

    # Sellers
    sellers: list[Seller]

    # Acquisition history
    acquisitions: list[AcquisitionPart]

    # Deductions
    deductions: list[Deduction] = Field(default_factory=list)

    # Depreciation
    depreciation: DepreciationInput = Field(default_factory=DepreciationInput)

    # Exemption
    exemption: ExemptionCheck = Field(default_factory=ExemptionCheck)

    # Prisa preference
    prisa_years: int = Field(default=0, ge=0, le=4, description="0 = no prisa, 1-4 = years")

    # Property type qualification
    is_residential: bool = Field(
        default=True, description="Is this a qualifying residential property (for linear mutav)"
    )

    # Betterment levy
    betterment_levy: float = Field(default=0.0, ge=0, description="Hetel hashbacha paid (ILS)")


class TaxPeriodBreakdown(BaseModel):
    """Tax breakdown by period for linear calculation."""

    days_total: int
    days_before_2001_11_07: int
    days_2001_to_2012: int
    days_after_2012: int
    days_to_2014_01_01: int
    days_after_2014: int


class PrisaYearResult(BaseModel):
    """Result for a single prisa year."""

    year: int
    spread_amount: float
    other_income: float
    total_taxable: float
    tax_calculated: float
    is_max_mode: bool = False


class PrisaResult(BaseModel):
    """Complete prisa calculation result."""

    years: int
    year_results: list[PrisaYearResult]
    total_tax: float
    tax_without_prisa: float
    savings: float


class SellerResult(BaseModel):
    """Calculation result for a single seller."""

    seller_name: str
    share_percent: float

    # Core values
    sale_amount_ils: float
    acquisition_amount_ils_indexed: float
    deductions_total_indexed: float
    total_cost_indexed: float

    # Shevach
    shevach_mekarkein: float
    inflationary_amount: float
    real_shevach: float

    # Linear split
    period_breakdown: TaxPeriodBreakdown
    shevach_to_2014: float
    shevach_after_2014: float

    # Tax
    tax_linear: float
    tax_regular: float
    tax_with_prisa: Optional[float] = None
    tax_inflationary: float = 0.0  # 10% on pre-1994 inflationary amount
    mas_yesaf: float
    total_tax: float
    recommended_route: str

    # Prisa details
    prisa_result: Optional[PrisaResult] = None

    # Depreciation
    depreciation_amount: float

    # Exemption
    partial_exemption_amount: float = 0.0

    # CPI data
    cpi_acquisition: float
    cpi_sale: float
    indexation_ratio: float


class ComparisonRoute(BaseModel):
    """A tax route option for comparison."""

    route_name: str
    tax_amount: float
    effective_rate: float
    savings_vs_regular: float


class CalculationResult(BaseModel):
    """Complete calculation result."""

    # Per-seller results
    seller_results: list[SellerResult]

    # Full transaction values (for JSON export)
    full_shevach_mekarkein: float
    full_inflationary: float
    full_real_shevach: float
    full_tax: float

    # Route comparison
    route_comparison: list[ComparisonRoute]

    # Prisa comparison (1-4 years)
    prisa_comparison: list[PrisaResult] = Field(default_factory=list)
