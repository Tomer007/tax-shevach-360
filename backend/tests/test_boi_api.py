"""Tests for Bank of Israel API module."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.boi_api import (
    ILP_TO_ILS,
    ILR_TO_ILS,
    convert_to_ils,
    fetch_exchange_rate,
)
from app.models import Currency


class TestConvertToIls:
    """Tests for convert_to_ils function."""

    def test_ils_unchanged(self):
        """ILS returns unchanged."""
        assert convert_to_ils(1000, Currency.ILS, None) == 1000

    def test_ilp_conversion(self):
        """ILP uses fixed rate."""
        result = convert_to_ils(1_000_000, Currency.ILP, None)
        assert result == 1_000_000 * ILP_TO_ILS

    def test_ilr_conversion(self):
        """ILR uses fixed rate."""
        result = convert_to_ils(1_000, Currency.ILR, None)
        assert result == 1_000 * ILR_TO_ILS

    def test_usd_with_rate(self):
        """USD with given rate."""
        result = convert_to_ils(100, Currency.USD, 3.65)
        assert result == 365.0

    def test_eur_with_rate(self):
        """EUR with given rate."""
        result = convert_to_ils(100, Currency.EUR, 4.0)
        assert result == 400.0

    def test_none_rate_fallback(self):
        """None rate returns amount as-is (fallback)."""
        result = convert_to_ils(100, Currency.USD, None)
        assert result == 100

    def test_zero_amount(self):
        """Zero amount returns zero."""
        assert convert_to_ils(0, Currency.USD, 3.65) == 0.0

    def test_ilp_very_small(self):
        """ILP conversion produces very small ILS values."""
        # 1 Lira = 0.000001 NIS
        result = convert_to_ils(1, Currency.ILP, None)
        assert result == 0.000001


@pytest.mark.asyncio
class TestFetchExchangeRate:
    """Tests for fetch_exchange_rate function."""

    async def test_ils_returns_1(self):
        """ILS always returns 1.0."""
        rate = await fetch_exchange_rate(Currency.ILS, date(2024, 1, 1))
        assert rate == 1.0

    async def test_ilp_returns_fixed(self):
        """ILP returns fixed conversion rate."""
        rate = await fetch_exchange_rate(Currency.ILP, date(1975, 1, 1))
        assert rate == ILP_TO_ILS

    async def test_ilr_returns_fixed(self):
        """ILR returns fixed conversion rate."""
        rate = await fetch_exchange_rate(Currency.ILR, date(1983, 1, 1))
        assert rate == ILR_TO_ILS

    @patch("app.boi_api._fetch_rate_for_date")
    async def test_usd_calls_api(self, mock_fetch):
        """USD calls the BOI API."""
        mock_fetch.return_value = 3.65
        rate = await fetch_exchange_rate(Currency.USD, date(2024, 6, 1))
        assert rate == 3.65
        mock_fetch.assert_called()

    @patch("app.boi_api._fetch_rate_for_date")
    async def test_api_failure_returns_none(self, mock_fetch):
        """API failure returns None."""
        mock_fetch.return_value = None
        rate = await fetch_exchange_rate(Currency.USD, date(2024, 6, 1))
        assert rate is None

    @patch("app.boi_api._fetch_rate_for_date")
    async def test_retries_nearby_dates(self, mock_fetch):
        """Retries nearby dates when exact date fails."""
        # First call (exact date) fails, second succeeds
        mock_fetch.side_effect = [None, None, 3.65]
        rate = await fetch_exchange_rate(Currency.USD, date(2024, 6, 1))
        assert rate == 3.65
        assert mock_fetch.call_count >= 2
