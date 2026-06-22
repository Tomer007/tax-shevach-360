"""Tests for email sending and main.py coverage."""

from unittest.mock import patch, MagicMock

from app.auth import _login_attempts
from app.auth_routes import _send_calculation_email
from app.main import app

from fastapi.testclient import TestClient

client = TestClient(app)


class TestSendCalculationEmail:
    """Test the _send_calculation_email helper."""

    @patch.dict("os.environ", {"SMTP_USERNAME": "", "SMTP_PASSWORD": ""})
    def test_no_smtp_credentials_returns_early(self):
        """If no SMTP credentials, function returns without error."""
        # Should not raise
        _send_calculation_email(
            result_data={"seller_results": [], "full_tax": 0, "full_real_shevach": 0, "route_comparison": []},
            user={"username": "test", "full_name": "Test"},
            user_email=None,
        )

    @patch("smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "pass",
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "NOTIFY_EMAIL": "admin@test.com",
    })
    def test_email_sent_with_results(self, mock_smtp_cls):
        """Email is sent with formatted results."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result_data = {
            "seller_results": [
                {"seller_name": "Test", "share_percent": 100, "total_tax": 50000, "recommended_route": "linear_mutav"}
            ],
            "full_tax": 50000,
            "full_real_shevach": 200000,
            "route_comparison": [
                {"route_name": "linear_mutav", "tax_amount": 50000, "effective_rate": 10.5},
                {"route_name": "regular", "tax_amount": 75000, "effective_rate": 15.0},
            ],
        }
        _send_calculation_email(result_data, {"username": "tomer", "full_name": "Tomer Gur"}, "user@test.com")
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "pass",
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
    })
    def test_email_failure_is_silent(self, mock_smtp_cls):
        """SMTP failure doesn't raise."""
        mock_smtp_cls.return_value.__enter__ = MagicMock(side_effect=Exception("SMTP down"))
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        _send_calculation_email(
            {"seller_results": [], "full_tax": 0, "full_real_shevach": 0, "route_comparison": []},
            {"username": "x", "full_name": "X"},
            None,
        )

    @patch("smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "pass",
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
    })
    def test_email_with_empty_routes(self, mock_smtp_cls):
        """Email handles empty route comparison gracefully."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        _send_calculation_email(
            {"seller_results": [], "full_tax": 0, "full_real_shevach": 0, "route_comparison": []},
            {"username": "x", "full_name": "X Y"},
            "user@email.com",
        )


class TestMainApp:
    """Test main app endpoints."""

    def test_health_check(self):
        """Health endpoint returns ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_unknown_api_route(self):
        """Unknown API routes are handled by the app."""
        resp = client.get("/api/nonexistent")
        # The SPA catch-all may serve 200, or API routes return 404/405
        assert resp.status_code in (200, 404, 405)


class TestAuthEdgeCases:
    """Test auth edge cases for coverage."""

    def setup_method(self):
        _login_attempts.clear()

    def test_expired_token(self):
        """Expired/invalid token returns 401."""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer expired.token.here"})
        assert resp.status_code == 401

    def test_malformed_bearer(self):
        """Malformed bearer header."""
        resp = client.get("/api/auth/me", headers={"Authorization": "NotBearer token"})
        assert resp.status_code == 401
