"""Tests for Pydantic models."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import (
    AcquisitionPart,
    AcquisitionType,
    Currency,
    Deduction,
    DepreciationInput,
    DepreciationRate,
    ExemptionCheck,
    RentalPeriod,
    RentalTaxTrack,
    Seller,
    TransactionInput,
)


class TestCurrencyEnum:
    """Tests for Currency enum."""

    def test_all_values(self):
        """All expected currencies exist."""
        assert Currency.ILS == "ILS"
        assert Currency.USD == "USD"
        assert Currency.EUR == "EUR"
        assert Currency.GBP == "GBP"
        assert Currency.ILP == "ILP"
        assert Currency.ILR == "ILR"


class TestAcquisitionTypeEnum:
    """Tests for AcquisitionType enum."""

    def test_all_values(self):
        """All acquisition types exist."""
        assert AcquisitionType.PURCHASE == "purchase"
        assert AcquisitionType.INHERITANCE == "inheritance"
        assert AcquisitionType.GIFT == "gift"
        assert AcquisitionType.DIVORCE == "divorce"


class TestRentalTaxTrackEnum:
    """Tests for RentalTaxTrack enum."""

    def test_all_tracks(self):
        """All tax tracks exist."""
        assert RentalTaxTrack.MARGINAL == "marginal"
        assert RentalTaxTrack.FLAT_10 == "flat_10"
        assert RentalTaxTrack.EXEMPT == "exempt"
        assert RentalTaxTrack.EXEMPT_CHEN == "exempt_chen"


class TestDepreciationRateEnum:
    """Tests for DepreciationRate enum."""

    def test_all_rates(self):
        """All depreciation rates exist."""
        assert len(DepreciationRate) == 6


class TestSeller:
    """Tests for Seller model."""

    def test_valid_seller(self):
        """Creates valid seller."""
        seller = Seller(
            name="Test",
            id_number="123456789",
            birth_date=date(1970, 1, 1),
            share_percent=50.0,
        )
        assert seller.name == "Test"
        assert seller.share_percent == 50.0
        assert seller.is_israeli_resident is True

    def test_share_percent_validation(self):
        """Share percent must be 0-100."""
        with pytest.raises(ValidationError):
            Seller(
                name="Test",
                id_number="123",
                birth_date=date(1970, 1, 1),
                share_percent=150.0,
            )

    def test_negative_share(self):
        """Negative share is invalid."""
        with pytest.raises(ValidationError):
            Seller(
                name="Test",
                id_number="123",
                birth_date=date(1970, 1, 1),
                share_percent=-10.0,
            )

    def test_default_values(self):
        """Default values are applied."""
        seller = Seller(
            name="Test",
            id_number="123",
            birth_date=date(1970, 1, 1),
            share_percent=100.0,
        )
        assert seller.annual_incomes == {}
        assert seller.prisa_max_years == []
        assert seller.marital_status == "single"


class TestAcquisitionPart:
    """Tests for AcquisitionPart model."""

    def test_valid_acquisition(self):
        """Creates valid acquisition part."""
        part = AcquisitionPart(
            acquisition_date=date(2010, 1, 1),
            amount=1_000_000,
            share_percent=100.0,
        )
        assert part.acquisition_type == AcquisitionType.PURCHASE
        assert part.currency == Currency.ILS

    def test_zero_amount_invalid(self):
        """Zero amount is invalid (must be > 0)."""
        with pytest.raises(ValidationError):
            AcquisitionPart(
                acquisition_date=date(2010, 1, 1),
                amount=0,
                share_percent=100.0,
            )

    def test_negative_amount_invalid(self):
        """Negative amount is invalid."""
        with pytest.raises(ValidationError):
            AcquisitionPart(
                acquisition_date=date(2010, 1, 1),
                amount=-100,
                share_percent=100.0,
            )


class TestDeduction:
    """Tests for Deduction model."""

    def test_valid_deduction(self):
        """Creates valid deduction."""
        ded = Deduction(
            description="Lawyer fees",
            amount=30000,
            deduction_date=date(2024, 1, 1),
        )
        assert ded.currency == Currency.ILS

    def test_negative_amount_invalid(self):
        """Negative amount is invalid."""
        with pytest.raises(ValidationError):
            Deduction(
                description="Test",
                amount=-1000,
                deduction_date=date(2024, 1, 1),
            )


class TestDepreciationInput:
    """Tests for DepreciationInput model."""

    def test_defaults(self):
        """Default values."""
        dep = DepreciationInput()
        assert dep.mode == "manual"
        assert dep.manual_amount == 0.0
        assert dep.rental_periods == []
        assert abs(dep.land_ratio - 1 / 3) < 0.001

    def test_land_ratio_validation(self):
        """Land ratio must be 0-1."""
        with pytest.raises(ValidationError):
            DepreciationInput(land_ratio=1.5)


class TestExemptionCheck:
    """Tests for ExemptionCheck model."""

    def test_defaults(self):
        """All defaults are False/0."""
        ex = ExemptionCheck()
        assert ex.is_single_apartment is False
        assert ex.ownership_months == 0
        assert ex.has_building_rights is False


class TestTransactionInput:
    """Tests for TransactionInput model."""

    def test_valid_transaction(self):
        """Creates valid transaction."""
        txn = TransactionInput(
            sale_date=date(2024, 6, 1),
            sale_amount=2_000_000,
            sellers=[
                Seller(
                    name="Test",
                    id_number="123",
                    birth_date=date(1970, 1, 1),
                    share_percent=100.0,
                )
            ],
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(2010, 1, 1),
                    amount=1_000_000,
                    share_percent=100.0,
                )
            ],
        )
        assert txn.prisa_years == 0
        assert txn.sale_currency == Currency.ILS

    def test_prisa_years_validation(self):
        """Prisa years must be 0-4."""
        with pytest.raises(ValidationError):
            TransactionInput(
                sale_date=date(2024, 6, 1),
                sale_amount=2_000_000,
                sellers=[
                    Seller(
                        name="Test",
                        id_number="123",
                        birth_date=date(1970, 1, 1),
                        share_percent=100.0,
                    )
                ],
                acquisitions=[
                    AcquisitionPart(
                        acquisition_date=date(2010, 1, 1),
                        amount=1_000_000,
                        share_percent=100.0,
                    )
                ],
                prisa_years=5,
            )
