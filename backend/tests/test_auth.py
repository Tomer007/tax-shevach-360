"""Tests for authentication and contract upload."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth import (
    authenticate_user,
    create_access_token,
    verify_code_name,
    verify_password,
    VALID_USERS,
)
from app.contract_parser import ParsedContract, parse_contract_text
from app.main import app

client = TestClient(app)


class TestCodeName:
    """Test code name verification (POKER)."""

    def test_valid_code_name(self):
        assert verify_code_name("POKER") is True

    def test_valid_code_name_lowercase(self):
        assert verify_code_name("poker") is True

    def test_valid_code_name_mixed_case(self):
        assert verify_code_name("Poker") is True

    def test_valid_code_name_with_spaces(self):
        assert verify_code_name("  POKER  ") is True

    def test_invalid_code_name(self):
        assert verify_code_name("WRONG") is False

    def test_empty_code_name(self):
        assert verify_code_name("") is False

    def test_verify_code_endpoint_valid(self):
        response = client.post("/api/auth/verify-code", json={"code_name": "POKER"})
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_verify_code_endpoint_invalid(self):
        response = client.post("/api/auth/verify-code", json={"code_name": "WRONG"})
        assert response.status_code == 403


class TestAuthentication:
    """Test user authentication (tomer/gur)."""

    def test_valid_login(self):
        user = authenticate_user("tomer", "gur")
        assert user is not None
        assert user["username"] == "tomer"

    def test_invalid_username(self):
        user = authenticate_user("nonexistent", "gur")
        assert user is None

    def test_invalid_password(self):
        user = authenticate_user("tomer", "wrong")
        assert user is None

    def test_login_endpoint_success(self):
        response = client.post("/api/auth/login", json={"username": "tomer", "password": "gur"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_endpoint_wrong_password(self):
        response = client.post("/api/auth/login", json={"username": "tomer", "password": "bad"})
        assert response.status_code == 401

    def test_login_endpoint_wrong_username(self):
        response = client.post("/api/auth/login", json={"username": "admin", "password": "gur"})
        assert response.status_code == 401


class TestJWT:
    """Test JWT token generation and validation."""

    def test_create_token(self):
        token = create_access_token(data={"sub": "tomer"})
        assert isinstance(token, str)
        assert len(token) > 50

    def test_me_endpoint_with_valid_token(self):
        # Login first
        login_resp = client.post("/api/auth/login", json={"username": "tomer", "password": "gur"})
        token = login_resp.json()["access_token"]

        # Use token
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["username"] == "tomer"
        assert response.json()["full_name"] == "Tomer Gur"

    def test_me_endpoint_without_token(self):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_endpoint_with_invalid_token(self):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401


class TestContractUpload:
    """Test contract upload and parsing."""

    def test_upload_requires_auth(self):
        """Upload endpoint requires authentication."""
        response = client.post("/api/upload-contract", files={"file": ("test.txt", b"content")})
        assert response.status_code == 401

    def test_upload_empty_file(self):
        """Empty file is rejected."""
        token = self._get_token()
        response = client.post(
            "/api/upload-contract",
            files={"file": ("test.txt", b"")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    def test_upload_too_large(self):
        """Files over 2MB are rejected."""
        token = self._get_token()
        large_content = b"x" * 2_100_000
        response = client.post(
            "/api/upload-contract",
            files={"file": ("test.txt", large_content)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    @patch("app.auth_routes.parse_contract_text")
    def test_upload_success(self, mock_parse):
        """Successful upload returns parsed contract."""
        mock_parse.return_value = ParsedContract(
            sale_date="2025-01-01",
            sale_amount=3_000_000,
            sale_currency="ILS",
            sellers=[{"name": "ישראל ישראלי", "share_percent": 100}],
            confidence="high",
        )
        token = self._get_token()
        response = client.post(
            "/api/upload-contract",
            files={"file": ("contract.txt", "חוזה מכר דירה".encode("utf-8"))},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sale_amount"] == 3_000_000
        assert data["confidence"] == "high"

    @patch("app.auth_routes.parse_contract_text")
    def test_upload_no_openai_key(self, mock_parse):
        """Missing OpenAI key returns 503."""
        mock_parse.side_effect = ValueError("OPENAI_API_KEY environment variable not set")
        token = self._get_token()
        response = client.post(
            "/api/upload-contract",
            files={"file": ("contract.txt", b"some contract text")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503

    def _get_token(self) -> str:
        resp = client.post("/api/auth/login", json={"username": "tomer", "password": "gur"})
        return resp.json()["access_token"]


class TestContractParser:
    """Test the contract parser logic."""

    @patch("app.contract_parser.OPENAI_API_KEY", "")
    def test_no_api_key_raises(self):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            parse_contract_text("some text")

    @patch("app.contract_parser.OPENAI_API_KEY", "fake-key")
    @patch("app.contract_parser.OpenAI")
    def test_parse_returns_parsed_contract(self, mock_openai_cls):
        """Successful parse returns structured data."""
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {
                "message": type("Message", (), {
                    "content": '{"sale_date": "2025-06-01", "sale_amount": 2500000, "sellers": [{"name": "Test"}]}'
                })()
            })()
        ]

        result = parse_contract_text("חוזה מכר")
        assert result.sale_date == "2025-06-01"
        assert result.sale_amount == 2_500_000
        assert result.confidence == "high"

    @patch("app.contract_parser.OPENAI_API_KEY", "fake-key")
    @patch("app.contract_parser.OpenAI")
    def test_parse_invalid_json(self, mock_openai_cls):
        """Invalid JSON from OpenAI returns low confidence."""
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {
                "message": type("Message", (), {"content": "not json at all"})()
            })()
        ]

        result = parse_contract_text("some text")
        assert result.confidence == "failed"
