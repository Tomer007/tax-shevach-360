"""Tests for tax rates module."""

import pytest

from app.tax_rates import (
    BASE_CREDIT_POINTS,
    BUILDING_RIGHTS_49Z_CEILING,
    CREDIT_POINT_VALUES,
    EXEMPTION_49B2_CEILING,
    MAS_YESAF_RATE_ADDITIONAL_2025,
    MAS_YESAF_RATE_BASE,
    MAS_YESAF_THRESHOLD_2025,
    RATE_LINEAR_POST_2014,
    _calc_brackets,
    calculate_mas_yesaf,
    calculate_tax_on_income,
    get_marginal_tax_brackets,
    get_tax_brackets,
)


class TestGetTaxBrackets:
    """Tests for get_tax_brackets function."""

    def test_under_60_starts_at_31(self):
        """Under 60: passive income starts at 31%."""
        brackets = get_tax_brackets(2024, is_over_60=False)
        assert brackets[0][2] == 0.31

    def test_over_60_starts_at_10(self):
        """Over 60: first bracket is 10%."""
        brackets = get_tax_brackets(2024, is_over_60=True)
        assert brackets[0][2] == 0.10

    def test_top_bracket_is_50(self):
        """Top bracket is 50%."""
        brackets = get_tax_brackets(2024, is_over_60=False)
        assert brackets[-1][2] == 0.50

    def test_brackets_are_continuous(self):
        """Brackets should be continuous (no gaps)."""
        brackets = get_tax_brackets(2024)
        for i in range(1, len(brackets)):
            assert brackets[i][0] == brackets[i - 1][1]


class TestGetMarginalTaxBrackets:
    """Tests for get_marginal_tax_brackets function."""

    def test_starts_at_10(self):
        """Marginal brackets start at 10%."""
        brackets = get_marginal_tax_brackets(2024)
        assert brackets[0][2] == 0.10

    def test_has_all_brackets(self):
        """Should have 7 brackets."""
        brackets = get_marginal_tax_brackets(2024)
        assert len(brackets) == 7


class TestCalcBrackets:
    """Tests for _calc_brackets helper."""

    def test_zero_income(self):
        """Zero income = zero tax."""
        brackets = [(0, 100000, 0.10), (100000, float("inf"), 0.20)]
        assert _calc_brackets(0, brackets) == 0.0

    def test_negative_income(self):
        """Negative income = zero tax."""
        brackets = [(0, 100000, 0.10)]
        assert _calc_brackets(-5000, brackets) == 0.0

    def test_single_bracket(self):
        """Income in single bracket."""
        brackets = [(0, 100000, 0.10), (100000, float("inf"), 0.20)]
        assert _calc_brackets(50000, brackets) == 5000.0

    def test_two_brackets(self):
        """Income spanning two brackets."""
        brackets = [(0, 100000, 0.10), (100000, float("inf"), 0.20)]
        tax = _calc_brackets(150000, brackets)
        expected = 100000 * 0.10 + 50000 * 0.20
        assert abs(tax - expected) < 0.01

    def test_exact_bracket_boundary(self):
        """Income exactly at bracket boundary."""
        brackets = [(0, 100000, 0.10), (100000, 200000, 0.20)]
        tax = _calc_brackets(100000, brackets)
        assert tax == 10000.0


class TestCalculateTaxOnIncome:
    """Tests for calculate_tax_on_income function."""

    def test_zero_taxable(self):
        """Zero taxable income = zero tax."""
        assert calculate_tax_on_income(0, 0) == 0.0

    def test_negative_taxable(self):
        """Negative taxable income = zero tax."""
        assert calculate_tax_on_income(-10000, 0) == 0.0

    def test_basic_calculation(self):
        """Basic tax calculation without other income."""
        tax = calculate_tax_on_income(100000, other_income=0, year=2024)
        assert tax >= 0

    def test_stacking_on_other_income(self):
        """Tax increases when stacked on other income."""
        tax_alone = calculate_tax_on_income(100000, other_income=0, year=2024)
        tax_stacked = calculate_tax_on_income(100000, other_income=300000, year=2024)
        assert tax_stacked >= tax_alone

    def test_over_60_pays_less(self):
        """Over 60 pays less due to lower starting bracket."""
        # Use higher amount where credit points don't zero it all out
        tax_young = calculate_tax_on_income(500000, year=2024, is_over_60=False)
        tax_old = calculate_tax_on_income(500000, year=2024, is_over_60=True)
        assert tax_old < tax_young

    def test_credit_points_reduce_tax(self):
        """Credit points reduce tax when no other income."""
        tax_no_credit = calculate_tax_on_income(
            100000, year=2024, credit_points=0, is_over_60=True
        )
        tax_with_credit = calculate_tax_on_income(
            100000, year=2024, credit_points=BASE_CREDIT_POINTS, is_over_60=True
        )
        assert tax_with_credit < tax_no_credit

    def test_credit_points_not_below_zero(self):
        """Tax cannot go below zero even with many credits."""
        tax = calculate_tax_on_income(1000, year=2024, credit_points=10, is_over_60=True)
        assert tax == 0.0


class TestCalculateMasYesaf:
    """Tests for calculate_mas_yesaf function."""

    def test_below_threshold(self):
        """No surtax below threshold."""
        yesaf = calculate_mas_yesaf(500000, sale_year=2024)
        assert yesaf == 0.0

    def test_above_threshold_2024(self):
        """3% surtax on amount above threshold in 2024."""
        shevach = 1_000_000
        yesaf = calculate_mas_yesaf(shevach, sale_year=2024)
        expected = (shevach - MAS_YESAF_THRESHOLD_2025) * MAS_YESAF_RATE_BASE
        assert abs(yesaf - expected) < 0.01

    def test_additional_2_percent_from_2025(self):
        """Additional 2% from 2025."""
        shevach = 1_000_000
        yesaf_2024 = calculate_mas_yesaf(shevach, sale_year=2024)
        yesaf_2025 = calculate_mas_yesaf(shevach, sale_year=2025)
        # 2025 should be higher by the additional 2%
        additional = (shevach - MAS_YESAF_THRESHOLD_2025) * MAS_YESAF_RATE_ADDITIONAL_2025
        assert abs(yesaf_2025 - yesaf_2024 - additional) < 0.01

    def test_exempt_under_5m(self):
        """No surtax on exempt sale under 5M."""
        yesaf = calculate_mas_yesaf(
            real_shevach=1_000_000,
            sale_year=2024,
            is_exempt=True,
            sale_amount=4_000_000,
        )
        assert yesaf == 0.0

    def test_exempt_over_5m(self):
        """Surtax applies on exempt sale over 5M."""
        yesaf = calculate_mas_yesaf(
            real_shevach=1_000_000,
            sale_year=2024,
            is_exempt=True,
            sale_amount=6_000_000,
        )
        assert yesaf > 0.0

    def test_exactly_at_threshold(self):
        """Exactly at threshold = zero surtax."""
        yesaf = calculate_mas_yesaf(MAS_YESAF_THRESHOLD_2025, sale_year=2024)
        assert yesaf == 0.0
