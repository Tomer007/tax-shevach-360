"""Tests for algorithm improvements.

Covers:
1. Per-deduction indexation
2. Per-acquisition indexation
3. Currency conversion
4. Depreciation not re-indexed
5. Linear qualification check
6. Mas Yesaf with other income stacking
7. Inflationary tax (Section 48a(d))
8. Partial exemption
9. Non-resident tax
10. Betterment levy deduction
"""

from datetime import date

import pytest

from app.calculator import (
    _convert_to_ils_static,
    _index_acquisition,
    _index_deduction,
    calculate_non_resident_tax,
    calculate_transaction,
)
from app.cpi_data import get_indexation_ratio
from app.models import (
    AcquisitionPart,
    AcquisitionType,
    Currency,
    Deduction,
    DepreciationInput,
    ExemptionCheck,
    Seller,
    TransactionInput,
)
from app.tax_rates import (
    calculate_inflationary_tax,
    calculate_mas_yesaf,
    calculate_partial_exemption,
)


def _make_seller(
    name: str = "Test",
    birth_date: date = date(1970, 1, 1),
    share: float = 100,
    is_resident: bool = True,
    annual_incomes: dict[int, float] | None = None,
) -> Seller:
    return Seller(
        name=name,
        id_number="123456789",
        birth_date=birth_date,
        share_percent=share,
        is_israeli_resident=is_resident,
        annual_incomes=annual_incomes or {},
        prisa_max_years=[],
    )


def _make_txn(
    sale_date: date = date(2025, 6, 1),
    sale_amount: float = 3_000_000,
    sellers: list[Seller] | None = None,
    acquisitions: list[AcquisitionPart] | None = None,
    deductions: list[Deduction] | None = None,
    is_residential: bool = True,
    betterment_levy: float = 0,
    exemption: ExemptionCheck | None = None,
) -> TransactionInput:
    if sellers is None:
        sellers = [_make_seller()]
    if acquisitions is None:
        acquisitions = [
            AcquisitionPart(
                acquisition_date=date(2005, 1, 1),
                amount=1_000_000,
                currency=Currency.ILS,
                share_percent=100,
            )
        ]
    return TransactionInput(
        sale_date=sale_date,
        sale_amount=sale_amount,
        sale_currency=Currency.ILS,
        sellers=sellers,
        acquisitions=acquisitions,
        deductions=deductions or [],
        depreciation=DepreciationInput(),
        exemption=exemption or ExemptionCheck(),
        prisa_years=0,
        is_residential=is_residential,
        betterment_levy=betterment_levy,
    )


# --- Test #1: Per-deduction indexation ---

class TestPerDeductionIndexation:
    def test_deduction_indexed_from_own_date(self):
        """A 2018 deduction should have different indexation than a 2005 acquisition."""
        ded = Deduction(
            description="renovation",
            amount=100_000,
            currency=Currency.ILS,
            deduction_date=date(2018, 6, 1),
        )
        indexed = _index_deduction(ded, 2025)
        ratio_2018_to_2025 = get_indexation_ratio(2018, 2025)
        assert abs(indexed - 100_000 * ratio_2018_to_2025) < 0.01

    def test_deduction_vs_acquisition_different_ratios(self):
        """Deductions from different years get different indexation."""
        ded_2005 = Deduction(
            description="legal fees", amount=50_000, currency=Currency.ILS, deduction_date=date(2005, 1, 1)
        )
        ded_2020 = Deduction(
            description="renovation", amount=50_000, currency=Currency.ILS, deduction_date=date(2020, 1, 1)
        )
        idx_2005 = _index_deduction(ded_2005, 2025)
        idx_2020 = _index_deduction(ded_2020, 2025)
        # 2005 deduction should be indexed more
        assert idx_2005 > idx_2020

    def test_transaction_uses_per_deduction_indexation(self):
        """Full transaction indexes each deduction independently."""
        txn = _make_txn(
            deductions=[
                Deduction(description="early", amount=50_000, currency=Currency.ILS, deduction_date=date(2006, 1, 1)),
                Deduction(description="late", amount=50_000, currency=Currency.ILS, deduction_date=date(2023, 1, 1)),
            ]
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        # Deductions indexed total should NOT equal 100_000 * single ratio
        single_ratio = get_indexation_ratio(2005, 2025)
        assert abs(seller.deductions_total_indexed - 100_000 * single_ratio) > 1.0


# --- Test #2: Per-acquisition indexation ---

class TestPerAcquisitionIndexation:
    def test_multi_acquisition_different_dates(self):
        """Two acquisitions at different dates get different indexation."""
        txn = _make_txn(
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(2000, 1, 1), amount=500_000, currency=Currency.ILS, share_percent=50
                ),
                AcquisitionPart(
                    acquisition_date=date(2015, 1, 1), amount=500_000, currency=Currency.ILS, share_percent=50
                ),
            ]
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]

        # Indexed total should be sum of individually indexed parts
        ratio_2000 = get_indexation_ratio(2000, 2025)
        ratio_2015 = get_indexation_ratio(2015, 2025)
        expected = 500_000 * ratio_2000 + 500_000 * ratio_2015
        assert abs(seller.acquisition_amount_ils_indexed - expected) < 0.01

    def test_single_acquisition_unchanged(self):
        """Single acquisition still works correctly."""
        txn = _make_txn()
        result = calculate_transaction(txn)
        ratio = get_indexation_ratio(2005, 2025)
        expected = 1_000_000 * ratio
        assert abs(result.seller_results[0].acquisition_amount_ils_indexed - expected) < 0.01


# --- Test #3: Currency conversion ---

class TestCurrencyConversion:
    def test_ils_unchanged(self):
        assert _convert_to_ils_static(100_000, Currency.ILS) == 100_000

    def test_ilp_conversion(self):
        # 1 ILP = 0.000001 ILS
        assert _convert_to_ils_static(1_000_000, Currency.ILP) == 1.0

    def test_ilr_conversion(self):
        # 1 ILR = 0.001 ILS
        assert _convert_to_ils_static(1_000, Currency.ILR) == 1.0

    def test_usd_fallback_to_same_amount(self):
        """USD without live rate falls back to amount as-is."""
        result = _convert_to_ils_static(100_000, Currency.USD)
        assert result == 100_000

    def test_acquisition_in_ilp(self):
        """ILP acquisition is converted before indexation."""
        acq = AcquisitionPart(
            acquisition_date=date(1975, 1, 1),
            amount=500_000_000,  # 500M ILP
            currency=Currency.ILP,
            share_percent=100,
        )
        indexed = _index_acquisition(acq, 2025)
        ils_amount = 500_000_000 * 0.000001  # = 500 ILS
        ratio = get_indexation_ratio(1975, 2025)
        expected = ils_amount * ratio
        assert abs(indexed - expected) < 0.01


# --- Test #4: Depreciation not re-indexed ---

class TestDepreciationNotReindexed:
    def test_depreciation_reduces_cost_directly(self):
        """Depreciation reduces indexed cost basis without being re-indexed."""
        txn = _make_txn(
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(2005, 1, 1), amount=1_000_000, currency=Currency.ILS, share_percent=100
                )
            ],
        )
        txn.depreciation = DepreciationInput(mode="manual", manual_amount=50_000, rental_periods=[], land_ratio=1 / 3)
        result = calculate_transaction(txn)
        seller = result.seller_results[0]

        # Total cost indexed should be acquisition_indexed - depreciation (not * ratio)
        ratio = get_indexation_ratio(2005, 2025)
        expected_cost = 1_000_000 * ratio - 50_000
        assert abs(seller.total_cost_indexed - expected_cost) < 0.01


# --- Test #5: Linear qualification check ---

class TestLinearQualification:
    def test_non_residential_no_linear(self):
        """Non-residential property should not get linear mutav."""
        txn = _make_txn(is_residential=False)
        result = calculate_transaction(txn)
        # Route comparison should NOT include linear_mutav
        route_names = [r.route_name for r in result.route_comparison]
        assert "linear_mutav" not in route_names

    def test_residential_gets_linear(self):
        """Residential property gets linear mutav option."""
        txn = _make_txn(is_residential=True)
        result = calculate_transaction(txn)
        route_names = [r.route_name for r in result.route_comparison]
        assert "linear_mutav" in route_names


# --- Test #6: Mas Yesaf with other income ---

class TestMasYesafStacking:
    def test_no_other_income_below_threshold(self):
        """Shevach below threshold = no surtax."""
        tax = calculate_mas_yesaf(500_000, 2025, other_annual_income=0)
        assert tax == 0.0

    def test_other_income_pushes_above_threshold(self):
        """Other income + shevach exceeds threshold = surtax."""
        # Threshold is 721,560. If other income = 600,000 and shevach = 200,000
        # Total = 800,000, exceeds by 78,440
        tax = calculate_mas_yesaf(200_000, 2025, other_annual_income=600_000)
        assert tax > 0

    def test_all_shevach_taxable_when_other_exceeds_threshold(self):
        """When other income alone exceeds threshold, all shevach is taxed."""
        tax = calculate_mas_yesaf(100_000, 2025, other_annual_income=800_000)
        # All 100K of shevach is above threshold
        expected = 100_000 * 0.03 + 100_000 * 0.02  # 3% + 2% for 2025
        assert abs(tax - expected) < 0.01

    def test_transaction_uses_seller_income(self):
        """Transaction uses seller's annual income for mas yesaf."""
        txn = _make_txn(
            sale_amount=3_000_000,
            sellers=[_make_seller(annual_incomes={2025: 600_000})],
        )
        result = calculate_transaction(txn)
        # Mas yesaf should be higher than without other income
        txn2 = _make_txn(
            sale_amount=3_000_000,
            sellers=[_make_seller(annual_incomes={})],
        )
        result2 = calculate_transaction(txn2)
        assert result.seller_results[0].mas_yesaf >= result2.seller_results[0].mas_yesaf


# --- Test #7: Inflationary tax (Section 48a(d)) ---

class TestInflationaryTax:
    def test_pre_1994_acquisition_pays_10(self):
        """Acquisition before 1994 pays 10% on inflationary amount."""
        tax = calculate_inflationary_tax(100_000, date(1990, 1, 1))
        assert tax == 10_000

    def test_post_1994_acquisition_exempt(self):
        """Acquisition after 1994 = inflationary amount is exempt."""
        tax = calculate_inflationary_tax(100_000, date(2005, 1, 1))
        assert tax == 0.0

    def test_zero_inflationary(self):
        tax = calculate_inflationary_tax(0, date(1980, 1, 1))
        assert tax == 0.0

    def test_transaction_includes_inflationary_tax(self):
        """Pre-1994 transaction includes inflationary tax in total."""
        txn = _make_txn(
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(1990, 1, 1), amount=100_000, currency=Currency.ILS, share_percent=100
                )
            ],
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        assert seller.tax_inflationary > 0


# --- Test #8: Partial exemption ---

class TestPartialExemption:
    def test_below_ceiling_full_exempt(self):
        exempt = calculate_partial_exemption(4_000_000, 5_008_000)
        assert exempt == 4_000_000

    def test_above_ceiling_partial(self):
        exempt = calculate_partial_exemption(6_000_000, 5_008_000)
        assert exempt == 5_008_000

    def test_transaction_partial_exemption(self):
        """Sale above ceiling with single apartment gets partial exemption."""
        txn = _make_txn(
            sale_amount=6_000_000,
            exemption=ExemptionCheck(is_single_apartment=True, ownership_months=24),
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        assert seller.partial_exemption_amount > 0


# --- Test #9: Non-resident tax ---

class TestNonResidentTax:
    def test_non_resident_flat_rate(self):
        """Non-resident pays 25% flat from day one."""
        tax = calculate_non_resident_tax(1_000_000)
        assert tax == 250_000

    def test_non_resident_no_linear_benefit(self):
        """Non-resident should not get linear mutav benefit."""
        txn = _make_txn(
            sellers=[_make_seller(is_resident=False)],
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        assert seller.recommended_route == "non_resident_flat"

    def test_resident_vs_non_resident_different_tax(self):
        """Resident pays less than non-resident for old property."""
        txn_resident = _make_txn(sellers=[_make_seller(is_resident=True)])
        txn_foreign = _make_txn(sellers=[_make_seller(is_resident=False)])
        res_resident = calculate_transaction(txn_resident)
        res_foreign = calculate_transaction(txn_foreign)
        # For a 2005 acquisition, resident with linear should pay less
        assert res_resident.seller_results[0].tax_linear < res_foreign.seller_results[0].tax_linear


# --- Test #10: Betterment levy ---

class TestBettermentLevy:
    def test_betterment_reduces_shevach(self):
        """Betterment levy paid reduces the taxable shevach."""
        txn_no_levy = _make_txn()
        txn_with_levy = _make_txn(betterment_levy=100_000)

        res_no = calculate_transaction(txn_no_levy)
        res_with = calculate_transaction(txn_with_levy)

        # Shevach with levy should be lower
        assert res_with.full_shevach_mekarkein < res_no.full_shevach_mekarkein
        # Difference should be exactly the levy amount
        diff = res_no.full_shevach_mekarkein - res_with.full_shevach_mekarkein
        assert abs(diff - 100_000) < 0.01
