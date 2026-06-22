"""Tests for contract_parser module - both text and Vision paths."""

from unittest.mock import patch, MagicMock

import pytest
import openai

from app.contract_parser import (
    ParsedContract,
    parse_contract_text,
    parse_contract_images,
)


class TestParseContractText:
    """Tests for the text-based parser."""

    def test_missing_api_key(self):
        """Raises ValueError when API key is not set."""
        with patch("app.contract_parser.OPENAI_API_KEY", ""):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                parse_contract_text("some text")

    @patch("app.contract_parser.OpenAI")
    def test_successful_parse(self, mock_openai_cls):
        """Successful parse returns correct ParsedContract."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"sale_date": "2025-01-01", "sale_amount": 5000000, "sellers": [{"name": "Test"}], "property_type": "apartment"}'
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "test-key"):
            result = parse_contract_text("contract text")

        assert result.sale_date == "2025-01-01"
        assert result.sale_amount == 5_000_000
        assert result.confidence == "high"
        assert len(result.sellers) == 1

    @patch("app.contract_parser.OpenAI")
    def test_invalid_json_response(self, mock_openai_cls):
        """Invalid JSON from OpenAI returns failed confidence."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json {{"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "test-key"):
            result = parse_contract_text("text")

        assert result.confidence == "failed"

    @patch("app.contract_parser.OpenAI")
    def test_auth_error(self, mock_openai_cls):
        """AuthenticationError raises ValueError."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="Invalid", response=MagicMock(status_code=401), body=None
        )

        with patch("app.contract_parser.OPENAI_API_KEY", "bad-key"):
            with pytest.raises(ValueError, match="invalid API key"):
                parse_contract_text("text")

    @patch("app.contract_parser.OpenAI")
    def test_rate_limit_error(self, mock_openai_cls):
        """RateLimitError raises ValueError."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            message="Rate limited", response=MagicMock(status_code=429), body=None
        )

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            with pytest.raises(ValueError, match="rate limited"):
                parse_contract_text("text")

    @patch("app.contract_parser.OpenAI")
    def test_timeout_error(self, mock_openai_cls):
        """APITimeoutError raises ValueError."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            with pytest.raises(ValueError, match="timed out"):
                parse_contract_text("text")

    @patch("app.contract_parser.OpenAI")
    def test_sale_amount_string_with_commas(self, mock_openai_cls):
        """sale_amount as non-numeric string sets None."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"sale_date": "2025-01-01", "sale_amount": "not_a_number", "sellers": []}'
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            result = parse_contract_text("text")

        assert result.sale_amount is None
        assert result.confidence == "low"

    @patch("app.contract_parser.OpenAI")
    def test_medium_confidence(self, mock_openai_cls):
        """Date + amount but no sellers = medium confidence."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"sale_date": "2025-01-01", "sale_amount": 1000000, "sellers": []}'
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            result = parse_contract_text("text")

        assert result.confidence == "medium"


class TestParseContractImages:
    """Tests for the Vision-based parser."""

    def test_missing_api_key(self):
        """Raises ValueError when API key is not set."""
        with patch("app.contract_parser.OPENAI_API_KEY", ""):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                parse_contract_images(["base64data"])

    @patch("app.contract_parser.OpenAI")
    def test_successful_vision_parse(self, mock_openai_cls):
        """Successful Vision parse returns ParsedContract."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"sale_date": "2025-07-15", "sale_amount": 4800000, "sellers": [{"name": "Seller A"}], "property_type": "apartment"}'
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            result = parse_contract_images(["img1_b64", "img2_b64"])

        assert result.sale_amount == 4_800_000
        assert result.confidence == "high"

    @patch("app.contract_parser.OpenAI")
    def test_vision_invalid_json(self, mock_openai_cls):
        """Invalid JSON from Vision returns failed."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "garbage"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            result = parse_contract_images(["img"])

        assert result.confidence == "failed"

    @patch("app.contract_parser.OpenAI")
    def test_vision_auth_error(self, mock_openai_cls):
        """Vision AuthenticationError raises ValueError."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="Bad", response=MagicMock(status_code=401), body=None
        )

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            with pytest.raises(ValueError, match="invalid API key"):
                parse_contract_images(["img"])

    @patch("app.contract_parser.OpenAI")
    def test_vision_timeout(self, mock_openai_cls):
        """Vision timeout raises ValueError."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())

        with patch("app.contract_parser.OPENAI_API_KEY", "key"):
            with pytest.raises(ValueError, match="timed out"):
                parse_contract_images(["img"])


class TestParsedContractModel:
    """Test the ParsedContract model fields."""

    def test_default_values(self):
        """Default ParsedContract has expected defaults."""
        pc = ParsedContract()
        assert pc.confidence == "low"
        assert pc.sale_amount is None
        assert pc.sellers == []
        assert pc.is_single_apartment is None
        assert pc.is_inheritance is None

    def test_exemption_fields(self):
        """Exemption-related fields are properly set."""
        pc = ParsedContract(
            is_single_apartment=True,
            is_inheritance=False,
            has_building_rights=True,
            building_rights_value=500000,
            ownership_months=36,
        )
        assert pc.is_single_apartment is True
        assert pc.ownership_months == 36
        assert pc.building_rights_value == 500000
