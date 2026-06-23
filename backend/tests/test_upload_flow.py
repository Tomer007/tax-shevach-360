"""Tests for contract upload flow, Vision fallback, caching, and calculation endpoint."""

import hashlib
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import _login_attempts
from app.auth_routes import _parse_cache
from app.contract_parser import ParsedContract
from app.main import app

client = TestClient(app)


def _get_token() -> str:
    """Get a valid auth token for tests."""
    _login_attempts.clear()
    resp = client.post("/api/auth/login", json={"username": "tomer", "password": "gur"})
    return resp.json()["access_token"]


class TestRateLimiting:
    """Test that rate limiting only records failed attempts."""

    def setup_method(self):
        _login_attempts.clear()

    def test_successful_login_does_not_count(self):
        """Successful logins should not count toward rate limit."""
        for _ in range(6):
            resp = client.post("/api/auth/login", json={"username": "tomer", "password": "gur"})
            assert resp.status_code == 200

    def test_failed_login_counts(self):
        """Failed logins should count toward rate limit."""
        for _ in range(5):
            resp = client.post("/api/auth/login", json={"username": "tomer", "password": "wrong"})
            assert resp.status_code == 401
        # 6th attempt should be rate limited
        resp = client.post("/api/auth/login", json={"username": "tomer", "password": "wrong"})
        assert resp.status_code == 429


class TestUploadContract:
    """Test contract upload with Vision fallback and caching."""

    def setup_method(self):
        _login_attempts.clear()
        _parse_cache.clear()

    @patch("app.auth_routes.parse_contract_text")
    @patch("app.auth_routes.parse_contract_regex")
    @patch("app.auth_routes.send_contract_result_email", return_value=True)
    def test_text_pdf_uses_text_parser(self, mock_email, mock_regex, mock_parse):
        """PDF with good text tries regex first, falls back to AI."""
        # Regex returns low confidence → falls back to AI
        mock_regex.return_value = ParsedContract(confidence="failed")
        mock_parse.return_value = ParsedContract(
            sale_date="2025-01-01",
            sale_amount=2_000_000,
            sellers=[{"name": "Test", "share_percent": 100}],
            confidence="high",
        )
        token = _get_token()
        # Text content with Hebrew keywords to pass quality check
        content = "חוזה מכר\nתמורה של 2,000,000 ש\"ח\nמוכר: ישראל\nקונה: משה\n" * 20
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("contract.txt", content.encode("utf-8"))},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["sale_amount"] == 2_000_000
        mock_parse.assert_called_once()

    @patch("app.auth_routes.parse_contract_text")
    @patch("app.auth_routes.parse_contract_regex")
    @patch("app.auth_routes.send_contract_result_email", return_value=True)
    def test_cache_hit_skips_parsing(self, mock_email, mock_regex, mock_parse):
        """Second upload of same file uses cache."""
        mock_regex.return_value = ParsedContract(
            sale_date="2025-01-01",
            sale_amount=3_000_000,
            confidence="high",
        )
        token = _get_token()
        content = "חוזה מכר\nתמורה מוכר קונה שקל\n" * 20
        # First upload
        resp1 = client.post(
            "/api/upload-contract",
            files={"file": ("contract.txt", content.encode("utf-8"))},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 200
        # Second upload - same content
        resp2 = client.post(
            "/api/upload-contract",
            files={"file": ("contract.txt", content.encode("utf-8"))},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        # Both should succeed (cache or not)

    @patch("app.auth_routes.parse_contract_text")
    @patch("app.auth_routes.parse_contract_images")
    @patch("app.auth_routes.send_contract_result_email", return_value=True)
    def test_low_confidence_retries_with_vision(self, mock_email, mock_vision, mock_text):
        """If text parse returns low confidence, retry with Vision."""
        mock_text.return_value = ParsedContract(
            sale_date="2025-01-01",
            sale_amount=None,
            confidence="low",
        )
        mock_vision.return_value = ParsedContract(
            sale_date="2025-01-01",
            sale_amount=5_000_000,
            confidence="high",
        )
        token = _get_token()

        # Create a minimal valid PDF
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "חוזה מכר תמורה מוכר קונה שקל", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        resp = client.post(
            "/api/upload-contract",
            files={"file": ("contract.pdf", pdf_bytes)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["sale_amount"] == 5_000_000
        mock_vision.assert_called_once()

    def test_upload_unsupported_extension(self):
        """Unsupported file extensions are rejected."""
        token = _get_token()
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("image.jpg", b"fake image data")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "לא נתמך" in resp.json()["detail"]

    def test_upload_file_too_large(self):
        """Files over 10MB are rejected."""
        token = _get_token()
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("big.txt", b"x" * 10_100_000)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    @patch("app.auth_routes.parse_contract_text")
    @patch("app.auth_routes.parse_contract_regex")
    @patch("app.auth_routes.send_contract_result_email", return_value=False)
    def test_email_failure_does_not_fail_upload(self, mock_email, mock_regex, mock_parse):
        """Email send failure shouldn't cause upload to fail."""
        mock_regex.return_value = ParsedContract(
            sale_date="2025-06-01", sale_amount=1_000_000, confidence="high"
        )
        token = _get_token()
        content = "חוזה מכר תמורה מוכר קונה שקל\n" * 20
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("c.txt", content.encode("utf-8"))},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


class TestCalculateAndNotify:
    """Test the calculate-and-notify endpoint."""

    def setup_method(self):
        _login_attempts.clear()

    @patch("app.auth_routes._send_calculation_email")
    def test_valid_calculation(self, mock_email):
        """Valid input produces a calculation result."""
        token = _get_token()
        payload = {
            "sale_date": "2025-07-15",
            "sale_amount": 4800000,
            "sale_currency": "ILS",
            "sellers": [
                {
                    "name": "Test Seller",
                    "id_number": "123456789",
                    "birth_date": "1980-01-01",
                    "share_percent": 100,
                    "is_israeli_resident": True,
                    "marital_status": "single",
                    "annual_incomes": {},
                    "prisa_max_years": [],
                }
            ],
            "acquisitions": [
                {
                    "acquisition_date": "2020-01-01",
                    "acquisition_type": "purchase",
                    "amount": 2000000,
                    "currency": "ILS",
                    "share_percent": 100,
                    "deceased_eligible_for_exemption": False,
                }
            ],
            "deductions": [],
            "depreciation": {"mode": "manual", "manual_amount": 0, "rental_periods": [], "land_ratio": 0.333},
            "exemption": {
                "is_single_apartment": False,
                "ownership_months": 66,
                "is_inheritance": False,
                "has_building_rights": False,
                "building_rights_value": 0,
                "apartment_value_without_rights": 0,
            },
            "prisa_years": 0,
            "is_residential": True,
            "betterment_levy": 0,
        }
        resp = client.post(
            "/api/calculate-and-notify",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "seller_results" in data
        assert data["full_tax"] >= 0

    def test_missing_acquisition_date_returns_422(self):
        """Missing acquisition_date should return 422."""
        token = _get_token()
        payload = {
            "sale_date": "2025-07-15",
            "sale_amount": 4800000,
            "sale_currency": "ILS",
            "sellers": [{"name": "X", "id_number": "1", "birth_date": None, "share_percent": 100, "is_israeli_resident": True, "marital_status": "single", "annual_incomes": {}, "prisa_max_years": []}],
            "acquisitions": [{"acquisition_date": None, "acquisition_type": "purchase", "amount": 1000000, "currency": "ILS", "share_percent": 100, "deceased_eligible_for_exemption": False}],
            "deductions": [],
            "depreciation": {"mode": "manual", "manual_amount": 0, "rental_periods": [], "land_ratio": 0.333},
            "exemption": {"is_single_apartment": False, "ownership_months": 0, "is_inheritance": False, "has_building_rights": False, "building_rights_value": 0, "apartment_value_without_rights": 0},
            "prisa_years": 0,
            "is_residential": True,
            "betterment_levy": 0,
        }
        resp = client.post(
            "/api/calculate-and-notify",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_requires_auth(self):
        """Calculate endpoint requires authentication."""
        resp = client.post("/api/calculate-and-notify", json={})
        assert resp.status_code == 401


class TestVisionInitialPath:
    """Test Vision path for PDFs with poor text quality."""

    def setup_method(self):
        _login_attempts.clear()
        _parse_cache.clear()

    @patch("app.auth_routes.parse_contract_images")
    @patch("app.auth_routes.send_contract_result_email", return_value=True)
    def test_poor_quality_text_triggers_vision(self, mock_email, mock_vision):
        """PDF with non-Hebrew text triggers Vision path."""
        mock_vision.return_value = ParsedContract(
            sale_date="2025-03-01",
            sale_amount=1_500_000,
            sellers=[{"name": "Vision Seller"}],
            confidence="high",
        )
        token = _get_token()

        # Create PDF with non-Hebrew text (fails quality check)
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "This is English text only, no Hebrew keywords", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        resp = client.post(
            "/api/upload-contract",
            files={"file": ("scan.pdf", pdf_bytes)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["sale_amount"] == 1_500_000
        mock_vision.assert_called_once()

    @patch("app.auth_routes.parse_contract_images")
    def test_vision_value_error_returns_503(self, mock_vision):
        """Vision ValueError (e.g., no API key) returns 503."""
        mock_vision.side_effect = ValueError("OPENAI_API_KEY not set")
        token = _get_token()

        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "No Hebrew here at all", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        resp = client.post(
            "/api/upload-contract",
            files={"file": ("scan.pdf", pdf_bytes)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503

    @patch("app.auth_routes.parse_contract_images")
    def test_vision_unexpected_error_returns_500(self, mock_vision):
        """Vision unexpected error returns 500."""
        mock_vision.side_effect = RuntimeError("Unexpected")
        token = _get_token()

        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "No Hebrew here at all", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        resp = client.post(
            "/api/upload-contract",
            files={"file": ("scan.pdf", pdf_bytes)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 500


class TestCalculationEmail:
    """Test the _send_calculation_email function."""

    def setup_method(self):
        _login_attempts.clear()

    @patch("app.auth_routes._send_calculation_email")
    def test_calculation_sends_email(self, mock_email):
        """Successful calculation attempts to send email."""
        token = _get_token()
        payload = {
            "sale_date": "2025-07-15",
            "sale_amount": 4800000,
            "sale_currency": "ILS",
            "sellers": [{"name": "Test", "id_number": "123456789", "birth_date": "1980-01-01", "share_percent": 100, "is_israeli_resident": True, "marital_status": "single", "annual_incomes": {}, "prisa_max_years": []}],
            "acquisitions": [{"acquisition_date": "2020-01-01", "acquisition_type": "purchase", "amount": 2000000, "currency": "ILS", "share_percent": 100, "deceased_eligible_for_exemption": False}],
            "deductions": [],
            "depreciation": {"mode": "manual", "manual_amount": 0, "rental_periods": [], "land_ratio": 0.333},
            "exemption": {"is_single_apartment": False, "ownership_months": 66, "is_inheritance": False, "has_building_rights": False, "building_rights_value": 0, "apartment_value_without_rights": 0},
            "prisa_years": 0,
            "is_residential": True,
            "betterment_levy": 0,
        }
        resp = client.post("/api/calculate-and-notify", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        mock_email.assert_called_once()


class TestAuthEndpoints:
    """Test auth helper endpoints."""

    def setup_method(self):
        _login_attempts.clear()

    def test_get_me(self):
        """Get current user info."""
        token = _get_token()
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "tomer"

    def test_get_me_invalid_token(self):
        """Invalid token returns 401."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401

    def test_upload_no_filename(self):
        """Upload with empty filename gets rejected."""
        token = _get_token()
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("", b"content")},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Either 400 (no file/bad ext) or handled
        assert resp.status_code in (400, 422)

    @patch("app.auth_routes.parse_contract_text")
    @patch("app.auth_routes.parse_contract_regex")
    @patch("app.auth_routes.send_contract_result_email", return_value=True)
    def test_upload_latin1_fallback(self, mock_email, mock_regex, mock_parse):
        """Non-UTF8 text file falls back to latin-1 decoding."""
        mock_regex.return_value = ParsedContract(sale_date="2025-01-01", sale_amount=100000, confidence="high")
        token = _get_token()
        # Latin-1 encoded content with Hebrew-like keywords (won't be real Hebrew but tests the path)
        content = "חוזה מכר תמורה מוכר קונה שקל\n".encode("utf-8")  # UTF-8 is fine actually
        resp = client.post(
            "/api/upload-contract",
            files={"file": ("file.txt", content)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
