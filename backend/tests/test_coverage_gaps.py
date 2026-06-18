"""Tests to fill coverage gaps."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.boi_api import _fetch_rate_for_date, fetch_exchange_rate
from app.calculator import calculate_prisa, calculate_transaction
from app.cpi_data import get_cpi_for_year, get_indexation_ratio
from app.main import app
from app.models import (
    AcquisitionPart,
    AcquisitionType,
    Currency,
    DepreciationInput,
    ExemptionCheck,
    Seller,
    TransactionInput,
)

client = TestClient(app)


class TestCpiInterpolation:
    """Tests for CPI interpolation between known years."""

    def test_interpolation_between_years(self):
        """Test interpolation when year is not in CPI_ANNUAL."""
        from unittest.mock import patch

        from app.cpi_data import CPI_ANNUAL

        # Create a modified dict missing a year to trigger interpolation
        modified_cpi = {k: v for k, v in CPI_ANNUAL.items() if k != 2005}
        with patch("app.cpi_data.CPI_ANNUAL", modified_cpi):
            val = get_cpi_for_year(2005)
            # Should interpolate between 2004 (88063) and 2006 (91244)
            expected = 88063 + (91244 - 88063) * 0.5
            assert abs(val - expected) < 1.0

    def test_cpi_before_first_year_boundary(self):
        """Years at or below FIRST_CPI_YEAR return FIRST_CPI_VALUE."""
        from app.cpi_data import FIRST_CPI_VALUE

        # 1952 is the first year, returns FIRST_CPI_VALUE
        val = get_cpi_for_year(1952)
        assert val == FIRST_CPI_VALUE
        # 1940 is before first year
        val2 = get_cpi_for_year(1940)
        assert val2 == FIRST_CPI_VALUE

    def test_indexation_same_year_is_1(self):
        """Indexation ratio for same year is 1.0."""
        ratio = get_indexation_ratio(2020, 2020)
        assert ratio == 1.0

    def test_indexation_zero_cpi_guard(self):
        """If acquisition CPI is somehow 0, returns 1.0."""
        from unittest.mock import patch

        with patch("app.cpi_data.get_cpi_for_year", side_effect=lambda y: 0 if y == 1950 else 100):
            ratio = get_indexation_ratio(1950, 2020)
            assert ratio == 1.0


class TestBoiApiFetchRateForDate:
    """Tests for _fetch_rate_for_date to cover network paths."""

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_successful_fetch(self, mock_client_cls):
        """Successful API response returns rate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "header\n2024-06-01,USD,ILS,3.65"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result == 3.65

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_timeout_returns_none(self, mock_client_cls):
        """Timeout returns None."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result is None

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_http_error_returns_none(self, mock_client_cls):
        """HTTP error returns None."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result is None

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_non_200_returns_none(self, mock_client_cls):
        """Non-200 status returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result is None

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_single_line_response_returns_none(self, mock_client_cls):
        """Response with only header (< 2 lines) returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "header_only"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result is None

    @pytest.mark.asyncio
    @patch("app.boi_api.httpx.AsyncClient")
    async def test_invalid_value_returns_none(self, mock_client_cls):
        """Invalid float value in response returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "header\n2024-06-01,USD,ILS,not_a_number"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_rate_for_date("EXR/RER_USD_ILS", date(2024, 6, 1))
        assert result is None


class TestFetchExchangeRateUnsupported:
    """Test unsupported currency in fetch_exchange_rate."""

    @pytest.mark.asyncio
    async def test_gbp_calls_api(self):
        """GBP uses API (not fixed rate)."""
        with patch("app.boi_api._fetch_rate_for_date", return_value=4.5):
            rate = await fetch_exchange_rate(Currency.GBP, date(2024, 1, 1))
            assert rate == 4.5

    @pytest.mark.asyncio
    async def test_unsupported_currency_returns_none(self):
        """Currency not in EXCHANGE_RATE_SERIES returns None."""
        # Patch EXCHANGE_RATE_SERIES to be empty to trigger the `if not series` branch
        with patch("app.boi_api.EXCHANGE_RATE_SERIES", {}):
            rate = await fetch_exchange_rate(Currency.USD, date(2024, 1, 1))
            assert rate is None


class TestCalculatorEdgeCases:
    """Test edge cases in calculator."""

    def test_prisa_negative_shevach(self):
        """Prisa with zero taxable shevach."""
        result = calculate_prisa(
            taxable_shevach=0,
            sale_year=2024,
            seller_birth_year=1970,
            annual_incomes={},
            max_years=[],
            num_years=3,
        )
        assert result.total_tax == 0.0

    def test_transaction_with_inheritance(self):
        """Transaction acquired via inheritance."""
        txn = TransactionInput(
            sale_date=date(2024, 6, 1),
            sale_amount=2_000_000,
            sellers=[
                Seller(
                    name="Heir",
                    id_number="123456789",
                    birth_date=date(1970, 1, 1),
                    share_percent=100.0,
                )
            ],
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(2000, 1, 1),
                    acquisition_type=AcquisitionType.INHERITANCE,
                    amount=500_000,
                    share_percent=100.0,
                    deceased_eligible_for_exemption=True,
                )
            ],
        )
        result = calculate_transaction(txn)
        assert result.full_shevach_mekarkein > 0

    def test_regular_route_chosen(self):
        """Force regular route to be chosen by patching linear to be higher."""
        from unittest.mock import patch

        txn = TransactionInput(
            sale_date=date(2024, 6, 1),
            sale_amount=2_000_000,
            sellers=[
                Seller(
                    name="Test",
                    id_number="123456789",
                    birth_date=date(1970, 1, 1),
                    share_percent=100.0,
                    annual_incomes={2024: 1_000_000, 2023: 1_000_000},
                )
            ],
            acquisitions=[
                AcquisitionPart(
                    acquisition_date=date(2010, 1, 1),
                    amount=1_000_000,
                    share_percent=100.0,
                )
            ],
            prisa_years=0,
        )

        # We need prisa to not be lower than linear, AND linear > regular
        # Patch both calculate_linear_tax and calculate_prisa
        def fake_prisa(*args, **kwargs):
            from app.models import PrisaResult
            return PrisaResult(years=1, year_results=[], total_tax=999_999, tax_without_prisa=999_999, savings=0)

        with patch("app.calculator.calculate_linear_tax", return_value=500_000):
            with patch("app.calculator.calculate_regular_tax", return_value=100_000):
                with patch("app.calculator.calculate_prisa", side_effect=fake_prisa):
                    result = calculate_transaction(txn)
                    assert result.seller_results[0].recommended_route == "regular"
                    assert result.seller_results[0].total_tax >= 100_000


class TestRoutesEdgeCases:
    """Test route edge cases for coverage."""

    def test_calculate_with_exception_handling(self):
        """Invalid data that passes validation but fails in logic."""
        # This tests the try/except in the calculate route
        payload = {
            "sale_date": "2024-06-01",
            "sale_amount": 1,
            "sale_currency": "ILS",
            "sellers": [
                {
                    "name": "Test",
                    "id_number": "123",
                    "birth_date": "1970-01-01",
                    "share_percent": 100.0,
                }
            ],
            "acquisitions": [
                {
                    "acquisition_date": "2024-06-01",
                    "acquisition_type": "purchase",
                    "amount": 1,
                    "share_percent": 100.0,
                }
            ],
        }
        response = client.post("/api/calculate", json=payload)
        # Should still succeed (edge case but valid)
        assert response.status_code == 200

    def test_calculate_route_exception(self):
        """Test the exception handler in calculate route."""
        with patch("app.routes.calculate_transaction", side_effect=ValueError("test error")):
            payload = {
                "sale_date": "2024-06-01",
                "sale_amount": 1000000,
                "sale_currency": "ILS",
                "sellers": [
                    {
                        "name": "Test",
                        "id_number": "123",
                        "birth_date": "1970-01-01",
                        "share_percent": 100.0,
                    }
                ],
                "acquisitions": [
                    {
                        "acquisition_date": "2010-01-01",
                        "acquisition_type": "purchase",
                        "amount": 500000,
                        "share_percent": 100.0,
                    }
                ],
            }
            response = client.post("/api/calculate", json=payload)
            assert response.status_code == 400
            assert "test error" in response.json()["detail"]

    def test_prisa_comparison_endpoint(self):
        """Test prisa comparison endpoint."""
        response = client.post(
            "/api/prisa-comparison?taxable_shevach=200000&sale_year=2024&birth_year=1960"
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 4

    @patch("app.routes.fetch_exchange_rate")
    def test_exchange_rate_not_found(self, mock_fetch):
        """Exchange rate not found returns 404."""
        mock_fetch.return_value = None
        response = client.get("/api/exchange-rate?currency=USD&target_date=2024-01-01")
        assert response.status_code == 404

    def test_convert_currency_ilp(self):
        """Convert ILP currency."""
        response = client.post(
            "/api/convert-currency?amount=1000000&currency=ILP&target_date=1975-01-01"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ils_amount"] == 1.0  # 1M * 0.000001
