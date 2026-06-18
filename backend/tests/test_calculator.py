"""Tests for the core calculator module."""

from datetime import date

import pytest

from app.calculator import (
    calculate_days_breakdown,
    calculate_linear_tax,
    calculate_prisa,
    calculate_regular_tax,
    calculate_transaction,
    check_49z_building_rights,
)
from app.models import (
    AcquisitionPart,
    AcquisitionType,
    Deduction,
    DepreciationInput,
    ExemptionCheck,
    Seller,
    TaxPeriodBreakdown,
    TransactionInput,
)
from app.tax_rates import BUILDING_RIGHTS_49Z_CEILING, BUILDING_RIGHTS_NEGLIGIBLE


class TestCalculateDaysBreakdown:
    """Tests for calculate_days_breakdown function."""

    def test_all_before_2001(self):
        """Acquisition and sale both before 7.11.2001."""
        breakdown = calculate_days_breakdown(date(1990, 1, 1), date(2000, 1, 1))
        assert breakdown.days_total == (date(2000, 1, 1) - date(1990, 1, 1)).days
        assert breakdown.days_before_2001_11_07 == breakdown.days_total
        assert breakdown.days_2001_to_2012 == 0
        assert breakdown.days_after_2012 == 0

    def test_all_after_2014(self):
        """Both dates after 1.1.2014."""
        breakdown = calculate_days_breakdown(date(2015, 1, 1), date(2024, 1, 1))
        assert breakdown.days_before_2001_11_07 == 0
        assert breakdown.days_to_2014_01_01 == 0
        assert breakdown.days_after_2014 == breakdown.days_total

    def test_spanning_all_periods(self):
        """Transaction spanning all periods."""
        breakdown = calculate_days_breakdown(date(1995, 1, 1), date(2024, 1, 1))
        assert breakdown.days_before_2001_11_07 > 0
        assert breakdown.days_2001_to_2012 > 0
        assert breakdown.days_after_2012 > 0
        assert breakdown.days_to_2014_01_01 > 0
        assert breakdown.days_after_2014 > 0
        # Sum of pre/post 2014 should equal total
        assert breakdown.days_to_2014_01_01 + breakdown.days_after_2014 == breakdown.days_total

    def test_same_day(self):
        """Same acquisition and sale date = 0 days."""
        breakdown = calculate_days_breakdown(date(2020, 1, 1), date(2020, 1, 1))
        assert breakdown.days_total == 0

    def test_sale_before_acquisition(self):
        """Invalid: sale before acquisition = 0 days."""
        breakdown = calculate_days_breakdown(date(2024, 1, 1), date(2020, 1, 1))
        assert breakdown.days_total == 0

    def test_mordehai_case(self):
        """Real case: Mordehai transaction dates."""
        # Acquisition: 2008-10-27, Sale: 2024-02-15
        breakdown = calculate_days_breakdown(date(2008, 10, 27), date(2024, 2, 15))
        assert breakdown.days_total == 5589
        assert breakdown.days_to_2014_01_01 > 0
        assert breakdown.days_after_2014 > 0

    def test_amir_rozen_case(self):
        """Real case: Amir Rozen transaction."""
        breakdown = calculate_days_breakdown(date(2010, 10, 5), date(2025, 12, 31))
        assert breakdown.days_total > 0
        # Acquired after 2001, so no pre-2001 days
        assert breakdown.days_before_2001_11_07 == 0


class TestCalculateLinearTax:
    """Tests for calculate_linear_tax function."""

    def test_all_after_2014(self):
        """If all days after 2014, full 25% on real shevach."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=0,
            days_2001_to_2012=0,
            days_after_2012=1000,
            days_to_2014_01_01=0,
            days_after_2014=1000,
        )
        tax = calculate_linear_tax(1_000_000, breakdown)
        assert tax == 250_000.0

    def test_half_before_2014(self):
        """Half before 2014 = half exempt, half at 25%."""
        breakdown = TaxPeriodBreakdown(
            days_total=2000,
            days_before_2001_11_07=500,
            days_2001_to_2012=500,
            days_after_2012=1000,
            days_to_2014_01_01=1000,
            days_after_2014=1000,
        )
        tax = calculate_linear_tax(1_000_000, breakdown)
        assert tax == 125_000.0  # 50% * 25% * 1M

    def test_all_before_2014(self):
        """All before 2014 = fully exempt."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=500,
            days_2001_to_2012=500,
            days_after_2012=0,
            days_to_2014_01_01=1000,
            days_after_2014=0,
        )
        tax = calculate_linear_tax(1_000_000, breakdown)
        assert tax == 0.0

    def test_zero_days(self):
        """Zero total days = zero tax."""
        breakdown = TaxPeriodBreakdown(
            days_total=0,
            days_before_2001_11_07=0,
            days_2001_to_2012=0,
            days_after_2012=0,
            days_to_2014_01_01=0,
            days_after_2014=0,
        )
        tax = calculate_linear_tax(1_000_000, breakdown)
        assert tax == 0.0


class TestCalculateRegularTax:
    """Tests for calculate_regular_tax function."""

    def test_all_before_2001(self):
        """All before 2001: 47%."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=1000,
            days_2001_to_2012=0,
            days_after_2012=0,
            days_to_2014_01_01=1000,
            days_after_2014=0,
        )
        tax = calculate_regular_tax(1_000_000, breakdown)
        assert abs(tax - 470_000) < 1.0

    def test_all_2001_to_2012(self):
        """All in 2001-2012: 20%."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=0,
            days_2001_to_2012=1000,
            days_after_2012=0,
            days_to_2014_01_01=1000,
            days_after_2014=0,
        )
        tax = calculate_regular_tax(1_000_000, breakdown)
        assert abs(tax - 200_000) < 1.0

    def test_all_after_2012(self):
        """All after 2012: 25%."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=0,
            days_2001_to_2012=0,
            days_after_2012=1000,
            days_to_2014_01_01=0,
            days_after_2014=1000,
        )
        tax = calculate_regular_tax(1_000_000, breakdown)
        assert abs(tax - 250_000) < 1.0

    def test_zero_shevach(self):
        """Zero shevach = zero tax."""
        breakdown = TaxPeriodBreakdown(
            days_total=1000,
            days_before_2001_11_07=500,
            days_2001_to_2012=500,
            days_after_2012=0,
            days_to_2014_01_01=1000,
            days_after_2014=0,
        )
        tax = calculate_regular_tax(0, breakdown)
        assert tax == 0.0


class TestCalculatePrisa:
    """Tests for calculate_prisa function."""

    def test_zero_years(self):
        """Zero years = no prisa, just 25% flat."""
        result = calculate_prisa(
            taxable_shevach=100_000,
            sale_year=2024,
            seller_birth_year=1970,
            annual_incomes={},
            max_years=[],
            num_years=0,
        )
        assert result.years == 0
        assert result.total_tax == 25_000.0
        assert result.savings == 0.0

    def test_prisa_reduces_tax(self):
        """Prisa should reduce tax for over-60 with low income."""
        # Over 60, low income = benefit from lower brackets
        result = calculate_prisa(
            taxable_shevach=200_000,
            sale_year=2024,
            seller_birth_year=1960,
            annual_incomes={2024: 0, 2023: 0, 2022: 0},
            max_years=[],
            num_years=3,
        )
        assert result.total_tax < result.tax_without_prisa
        assert result.savings > 0

    def test_max_mode_caps_at_25(self):
        """Max mode year caps tax at 25%."""
        result = calculate_prisa(
            taxable_shevach=400_000,
            sale_year=2024,
            seller_birth_year=1960,
            annual_incomes={2023: 0, 2022: 0},
            max_years=[2024],  # Sale year in max mode
            num_years=3,
        )
        # Year 2024 (max mode) should pay exactly 25% of its share
        sale_year_result = next(yr for yr in result.year_results if yr.year == 2024)
        expected_max = (400_000 / 3) * 0.25
        assert abs(sale_year_result.tax_calculated - expected_max) < 0.01
        assert sale_year_result.is_max_mode is True

    def test_prisa_never_exceeds_no_prisa(self):
        """Prisa tax should never exceed 25% (cap)."""
        result = calculate_prisa(
            taxable_shevach=1_000_000,
            sale_year=2024,
            seller_birth_year=1960,
            annual_incomes={2024: 500_000, 2023: 500_000, 2022: 500_000, 2021: 500_000},
            max_years=[],
            num_years=4,
        )
        # Even with high income, cap at 25%
        assert result.total_tax <= result.tax_without_prisa + 1.0

    def test_more_years_generally_better(self):
        """More prisa years generally means lower tax (for low income)."""
        results = []
        for years in range(1, 5):
            r = calculate_prisa(
                taxable_shevach=400_000,
                sale_year=2024,
                seller_birth_year=1960,
                annual_incomes={2024: 0, 2023: 0, 2022: 0, 2021: 0},
                max_years=[],
                num_years=years,
            )
            results.append(r.total_tax)
        # Should be non-increasing (or at least not significantly increasing)
        # Note: may plateau when all brackets utilized
        assert results[-1] <= results[0] + 1.0


class TestCheck49zBuildingRights:
    """Tests for check_49z_building_rights function."""

    def test_no_building_rights(self):
        """No building rights = not applicable."""
        exemption = ExemptionCheck(has_building_rights=False)
        result = check_49z_building_rights(exemption)
        assert result["applicable"] is False
        assert result["exempt_amount"] == 0.0

    def test_negligible_rights(self):
        """Rights under 100K = fully exempt."""
        exemption = ExemptionCheck(
            has_building_rights=True,
            building_rights_value=80_000,
            apartment_value_without_rights=2_000_000,
        )
        result = check_49z_building_rights(exemption)
        assert result["applicable"] is True
        assert result["exempt_amount"] == 80_000
        assert result["taxable_amount"] == 0.0
        assert result["reason"] == "negligible_rights"

    def test_exactly_negligible_threshold(self):
        """Exactly at 100K threshold = still negligible."""
        exemption = ExemptionCheck(
            has_building_rights=True,
            building_rights_value=BUILDING_RIGHTS_NEGLIGIBLE,
            apartment_value_without_rights=2_000_000,
        )
        result = check_49z_building_rights(exemption)
        assert result["reason"] == "negligible_rights"

    def test_double_exemption(self):
        """Apartment under ceiling: double exemption."""
        exemption = ExemptionCheck(
            has_building_rights=True,
            building_rights_value=500_000,
            apartment_value_without_rights=1_500_000,
        )
        result = check_49z_building_rights(exemption)
        assert result["applicable"] is True
        assert result["reason"] == "double_exemption"
        # Exempt up to ceiling - apartment value
        expected_exempt = min(500_000, BUILDING_RIGHTS_49Z_CEILING - 1_500_000)
        assert result["exempt_amount"] == expected_exempt

    def test_above_ceiling(self):
        """Apartment above ceiling: no exemption on rights."""
        exemption = ExemptionCheck(
            has_building_rights=True,
            building_rights_value=500_000,
            apartment_value_without_rights=3_000_000,
        )
        result = check_49z_building_rights(exemption)
        assert result["applicable"] is True
        assert result["reason"] == "above_ceiling"
        assert result["exempt_amount"] == 0.0
        assert result["taxable_amount"] == 500_000


class TestCalculateTransaction:
    """Integration tests for calculate_transaction."""

    def _make_simple_transaction(self, **kwargs) -> TransactionInput:
        """Create a simple test transaction."""
        defaults = {
            "sale_date": date(2024, 6, 1),
            "sale_amount": 2_000_000,
            "sale_currency": "ILS",
            "sellers": [
                Seller(
                    name="Test Seller",
                    id_number="123456789",
                    birth_date=date(1970, 1, 1),
                    share_percent=100.0,
                )
            ],
            "acquisitions": [
                AcquisitionPart(
                    acquisition_date=date(2010, 1, 1),
                    acquisition_type=AcquisitionType.PURCHASE,
                    amount=1_000_000,
                    share_percent=100.0,
                )
            ],
            "deductions": [],
            "depreciation": DepreciationInput(mode="manual", manual_amount=0),
            "exemption": ExemptionCheck(),
            "prisa_years": 0,
        }
        defaults.update(kwargs)
        return TransactionInput(**defaults)

    def test_basic_transaction(self):
        """Basic transaction produces valid result."""
        txn = self._make_simple_transaction()
        result = calculate_transaction(txn)
        assert result.full_shevach_mekarkein > 0
        assert result.full_tax >= 0
        assert len(result.seller_results) == 1
        assert len(result.route_comparison) >= 2
        # Linear tax should be > 0
        assert result.seller_results[0].tax_linear > 0

    def test_two_sellers(self):
        """Two sellers split correctly."""
        txn = self._make_simple_transaction(
            sellers=[
                Seller(
                    name="Seller A",
                    id_number="111111111",
                    birth_date=date(1970, 1, 1),
                    share_percent=50.0,
                ),
                Seller(
                    name="Seller B",
                    id_number="222222222",
                    birth_date=date(1965, 1, 1),
                    share_percent=50.0,
                ),
            ]
        )
        result = calculate_transaction(txn)
        assert len(result.seller_results) == 2
        # Each seller has linear tax > 0
        assert result.seller_results[0].tax_linear > 0
        assert result.seller_results[1].tax_linear > 0
        # Both should have 50% share
        assert result.seller_results[0].share_percent == 50.0
        assert result.seller_results[1].share_percent == 50.0

    def test_exemption_single_apartment(self):
        """Single apartment exemption zeroes tax (minus yesaf)."""
        txn = self._make_simple_transaction(
            sale_amount=3_000_000,
            exemption=ExemptionCheck(
                is_single_apartment=True,
                ownership_months=24,
            ),
        )
        result = calculate_transaction(txn)
        # Should be exempt
        assert result.seller_results[0].recommended_route == "exempt_49b2"

    def test_with_deductions(self):
        """Deductions reduce shevach."""
        txn_no_ded = self._make_simple_transaction()
        txn_with_ded = self._make_simple_transaction(
            deductions=[
                Deduction(
                    description="Lawyer fees",
                    amount=50_000,
                    deduction_date=date(2024, 1, 1),
                ),
                Deduction(
                    description="Broker",
                    amount=40_000,
                    deduction_date=date(2024, 1, 1),
                ),
            ]
        )
        result_no = calculate_transaction(txn_no_ded)
        result_with = calculate_transaction(txn_with_ded)
        assert result_with.full_shevach_mekarkein < result_no.full_shevach_mekarkein

    def test_with_depreciation(self):
        """Depreciation increases shevach (reduces cost basis)."""
        txn_no_dep = self._make_simple_transaction()
        txn_with_dep = self._make_simple_transaction(
            depreciation=DepreciationInput(mode="manual", manual_amount=100_000),
        )
        result_no = calculate_transaction(txn_no_dep)
        result_with = calculate_transaction(txn_with_dep)
        assert result_with.full_shevach_mekarkein > result_no.full_shevach_mekarkein

    def test_old_acquisition(self):
        """Very old acquisition has high indexation."""
        txn = self._make_simple_transaction(
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(1980, 1, 1),
                    acquisition_type=AcquisitionType.PURCHASE,
                    amount=10_000,
                    share_percent=100.0,
                )
            ]
        )
        result = calculate_transaction(txn)
        # Indexation should be massive
        assert result.seller_results[0].indexation_ratio > 1000

    def test_prisa_requested(self):
        """Requested prisa years applied."""
        txn = self._make_simple_transaction(
            prisa_years=3,
            sellers=[
                Seller(
                    name="Test",
                    id_number="123456789",
                    birth_date=date(1960, 1, 1),
                    share_percent=100.0,
                    annual_incomes={2024: 0, 2023: 0, 2022: 0},
                )
            ],
        )
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        assert seller.prisa_result is not None

    def test_route_comparison_populated(self):
        """Route comparison has at least 2 routes."""
        txn = self._make_simple_transaction()
        result = calculate_transaction(txn)
        assert len(result.route_comparison) >= 2
        route_names = [r.route_name for r in result.route_comparison]
        assert "linear_mutav" in route_names
        assert "regular" in route_names

    def test_cpi_data_populated(self):
        """CPI fields are populated."""
        txn = self._make_simple_transaction()
        result = calculate_transaction(txn)
        seller = result.seller_results[0]
        assert seller.cpi_acquisition > 0
        assert seller.cpi_sale > 0
        assert seller.indexation_ratio > 0
