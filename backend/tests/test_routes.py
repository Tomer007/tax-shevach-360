"""Tests for API routes."""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self):
        """Health check returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "mas-shevach-360"


class TestCpiEndpoint:
    """Tests for CPI endpoint."""

    def test_valid_year(self):
        """Returns CPI for valid year."""
        response = client.get("/api/cpi/2020")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2020
        assert data["cpi"] > 0

    def test_invalid_year_too_low(self):
        """Returns 400 for year below range."""
        response = client.get("/api/cpi/1900")
        assert response.status_code == 400

    def test_invalid_year_too_high(self):
        """Returns 400 for year above range."""
        response = client.get("/api/cpi/2050")
        assert response.status_code == 400


class TestIndexationEndpoint:
    """Tests for indexation endpoint."""

    def test_valid_range(self):
        """Returns indexation for valid range."""
        response = client.get("/api/indexation?acquisition_year=2000&sale_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["ratio"] > 1.0
        assert data["cpi_acquisition"] > 0
        assert data["cpi_sale"] > 0

    def test_invalid_range(self):
        """Returns 400 for invalid range."""
        response = client.get("/api/indexation?acquisition_year=1900&sale_year=2024")
        assert response.status_code == 400


class TestCalculateEndpoint:
    """Tests for calculate endpoint."""

    def _make_payload(self, **overrides):
        """Create a valid calculate payload."""
        payload = {
            "sale_date": "2024-06-01",
            "sale_amount": 2000000,
            "sale_currency": "ILS",
            "sellers": [
                {
                    "name": "Test Seller",
                    "id_number": "123456789",
                    "birth_date": "1970-01-01",
                    "share_percent": 100.0,
                }
            ],
            "acquisitions": [
                {
                    "acquisition_date": "2010-01-01",
                    "acquisition_type": "purchase",
                    "amount": 1000000,
                    "share_percent": 100.0,
                }
            ],
            "deductions": [],
            "depreciation": {"mode": "manual", "manual_amount": 0},
            "exemption": {},
            "prisa_years": 0,
        }
        payload.update(overrides)
        return payload

    def test_basic_calculation(self):
        """Basic calculation returns valid result."""
        response = client.post("/api/calculate", json=self._make_payload())
        assert response.status_code == 200
        data = response.json()
        assert data["full_shevach_mekarkein"] > 0
        assert len(data["seller_results"]) == 1
        assert len(data["route_comparison"]) >= 2
        # Linear tax should be positive
        assert data["seller_results"][0]["tax_linear"] > 0

    def test_with_deductions(self):
        """Calculation with deductions."""
        payload = self._make_payload(
            deductions=[
                {
                    "description": "Lawyer",
                    "amount": 30000,
                    "currency": "ILS",
                    "deduction_date": "2024-01-01",
                }
            ]
        )
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200

    def test_with_two_sellers(self):
        """Calculation with two sellers."""
        payload = self._make_payload(
            sellers=[
                {
                    "name": "Seller A",
                    "id_number": "111111111",
                    "birth_date": "1970-01-01",
                    "share_percent": 50.0,
                },
                {
                    "name": "Seller B",
                    "id_number": "222222222",
                    "birth_date": "1965-01-01",
                    "share_percent": 50.0,
                },
            ]
        )
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["seller_results"]) == 2

    def test_with_exemption(self):
        """Calculation with exemption."""
        payload = self._make_payload(
            exemption={
                "is_single_apartment": True,
                "ownership_months": 24,
            }
        )
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["seller_results"][0]["recommended_route"] == "exempt_49b2"

    def test_with_prisa(self):
        """Calculation with prisa."""
        payload = self._make_payload(
            prisa_years=3,
            sellers=[
                {
                    "name": "Test",
                    "id_number": "123456789",
                    "birth_date": "1960-01-01",
                    "share_percent": 100.0,
                    "annual_incomes": {"2024": 0, "2023": 0, "2022": 0},
                }
            ],
        )
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200

    def test_invalid_payload(self):
        """Invalid payload returns 422."""
        response = client.post("/api/calculate", json={"invalid": True})
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Missing required fields returns 422."""
        response = client.post("/api/calculate", json={})
        assert response.status_code == 422


class TestCheck49zEndpoint:
    """Tests for building rights endpoint."""

    def test_no_rights(self):
        """No building rights."""
        response = client.post(
            "/api/check-49z",
            json={"has_building_rights": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["applicable"] is False

    def test_negligible_rights(self):
        """Negligible rights."""
        response = client.post(
            "/api/check-49z",
            json={
                "has_building_rights": True,
                "building_rights_value": 50000,
                "apartment_value_without_rights": 2000000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reason"] == "negligible_rights"


class TestExchangeRateEndpoint:
    """Tests for exchange rate endpoint."""

    def test_ils_rate(self):
        """ILS always returns 1.0."""
        response = client.get("/api/exchange-rate?currency=ILS&target_date=2024-01-01")
        assert response.status_code == 200
        data = response.json()
        assert data["rate"] == 1.0

    def test_ilp_rate(self):
        """ILP returns fixed rate."""
        response = client.get("/api/exchange-rate?currency=ILP&target_date=1975-01-01")
        assert response.status_code == 200
        data = response.json()
        assert data["rate"] == 0.000001


class TestConvertCurrencyEndpoint:
    """Tests for currency conversion endpoint."""

    def test_ils_conversion(self):
        """ILS conversion returns same amount."""
        response = client.post(
            "/api/convert-currency?amount=1000&currency=ILS&target_date=2024-01-01"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ils_amount"] == 1000
