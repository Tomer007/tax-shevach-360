"""Tests for depreciation module."""

from datetime import date

import pytest

from app.depreciation import (
    EXEMPT_DEPRECIATION_START,
    RATE_VALUES,
    calculate_depreciation,
    _calculate_period_depreciation,
)
from app.models import (
    DepreciationInput,
    DepreciationRate,
    RentalPeriod,
    RentalTaxTrack,
)


class TestCalculateDepreciation:
    """Tests for calculate_depreciation function."""

    def test_manual_mode(self):
        """Manual mode returns manual_amount directly."""
        dep = DepreciationInput(mode="manual", manual_amount=50000.0)
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        assert result == 50000.0

    def test_manual_mode_zero(self):
        """Manual mode with zero amount."""
        dep = DepreciationInput(mode="manual", manual_amount=0.0)
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        assert result == 0.0

    def test_auto_mode_no_periods(self):
        """Auto mode with no rental periods = zero depreciation."""
        dep = DepreciationInput(mode="auto", rental_periods=[])
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        assert result == 0.0

    def test_auto_mode_single_period(self):
        """Auto mode with one rental period."""
        period = RentalPeriod(
            start_date=date(2015, 1, 1),
            end_date=date(2020, 1, 1),
            tax_track=RentalTaxTrack.FLAT_10,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        dep = DepreciationInput(mode="auto", rental_periods=[period])
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        # 5 years * 2% * 1,000,000 = 100,000
        expected = 1_000_000 * 0.02 * (5 * 365 / 365.25)
        assert abs(result - expected) < 100  # Approximate due to day counting

    def test_auto_mode_multiple_periods(self):
        """Auto mode sums multiple periods."""
        periods = [
            RentalPeriod(
                start_date=date(2015, 1, 1),
                end_date=date(2017, 1, 1),
                tax_track=RentalTaxTrack.MARGINAL,
                depreciation_rate=DepreciationRate.RATE_2_FULL,
            ),
            RentalPeriod(
                start_date=date(2018, 1, 1),
                end_date=date(2020, 1, 1),
                tax_track=RentalTaxTrack.FLAT_10,
                depreciation_rate=DepreciationRate.RATE_4_BUILDING,
            ),
        ]
        dep = DepreciationInput(mode="auto", rental_periods=periods)
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        assert result > 0

    def test_building_only_rate(self):
        """Building-only rates use 2/3 of value."""
        period = RentalPeriod(
            start_date=date(2015, 1, 1),
            end_date=date(2016, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_4_BUILDING,
        )
        dep = DepreciationInput(mode="auto", rental_periods=[period], land_ratio=1 / 3)
        result = calculate_depreciation(dep, acquisition_amount=1_000_000)
        # 1 year * 4% * (2/3 * 1,000,000) = 26,667
        building_value = 1_000_000 * (2 / 3)
        expected = building_value * 0.04 * (365 / 365.25)
        assert abs(result - expected) < 100


class TestCalculatePeriodDepreciation:
    """Tests for _calculate_period_depreciation function."""

    def test_exempt_chen_zero(self):
        """Chen ruling (2024): zero depreciation."""
        period = RentalPeriod(
            start_date=date(2010, 1, 1),
            end_date=date(2020, 1, 1),
            tax_track=RentalTaxTrack.EXEMPT_CHEN,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        assert result == 0.0

    def test_exempt_before_2007(self):
        """Exempt track before 2007: no depreciation."""
        period = RentalPeriod(
            start_date=date(2000, 1, 1),
            end_date=date(2005, 1, 1),
            tax_track=RentalTaxTrack.EXEMPT,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        assert result == 0.0

    def test_exempt_spanning_2007(self):
        """Exempt track spanning 2007: only counts from Feb 2007."""
        period = RentalPeriod(
            start_date=date(2005, 1, 1),
            end_date=date(2010, 1, 1),
            tax_track=RentalTaxTrack.EXEMPT,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        # Should only count from Feb 2007 to Jan 2010 (~3 years)
        days = (date(2010, 1, 1) - EXEMPT_DEPRECIATION_START).days
        expected = 1_000_000 * 0.02 * (days / 365.25)
        assert abs(result - expected) < 100

    def test_exempt_after_2007(self):
        """Exempt track after 2007: full depreciation."""
        period = RentalPeriod(
            start_date=date(2010, 1, 1),
            end_date=date(2015, 1, 1),
            tax_track=RentalTaxTrack.EXEMPT,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        expected = 1_000_000 * 0.02 * (5 * 365 / 365.25)
        assert abs(result - expected) < 200

    def test_zero_days(self):
        """Zero-length period = zero depreciation."""
        period = RentalPeriod(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        assert result == 0.0

    def test_negative_days(self):
        """End before start = zero depreciation."""
        period = RentalPeriod(
            start_date=date(2020, 6, 1),
            end_date=date(2020, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        assert result == 0.0

    def test_cap_at_base_value(self):
        """Depreciation cannot exceed base value."""
        # 100 years at 6.5% = 650% > 100%, should cap
        period = RentalPeriod(
            start_date=date(1920, 1, 1),
            end_date=date(2020, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_6_5_BUILDING,
        )
        result = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        max_base = 1_000_000 * (2 / 3)  # Building portion
        assert result <= max_base + 0.01  # Float tolerance

    def test_custom_land_ratio(self):
        """Custom land ratio changes building portion."""
        period = RentalPeriod(
            start_date=date(2015, 1, 1),
            end_date=date(2016, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_4_BUILDING,
        )
        # 50% land = 50% building
        result = _calculate_period_depreciation(period, 1_000_000, 0.5)
        building = 1_000_000 * 0.5
        expected = building * 0.04 * (365 / 365.25)
        assert abs(result - expected) < 100

    def test_full_rate_ignores_land_ratio(self):
        """2% full rate applies to entire value regardless of land ratio."""
        period = RentalPeriod(
            start_date=date(2015, 1, 1),
            end_date=date(2016, 1, 1),
            tax_track=RentalTaxTrack.MARGINAL,
            depreciation_rate=DepreciationRate.RATE_2_FULL,
        )
        result_third = _calculate_period_depreciation(period, 1_000_000, 1 / 3)
        result_half = _calculate_period_depreciation(period, 1_000_000, 0.5)
        # Both should be the same since RATE_2_FULL applies to full value
        assert abs(result_third - result_half) < 0.01
