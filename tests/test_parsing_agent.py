"""
Unit tests for the Parsing Agent.

Tests date parsing, amount cleaning, merchant extraction,
and payment mode detection.
"""

import pytest
from datetime import datetime

from app.agents.parsing_agent import ParsingAgent
from app.schemas.transaction_schema import RawTransaction, PaymentMode


@pytest.fixture
def parser():
    """Create a ParsingAgent instance."""
    return ParsingAgent()


class TestDateParsing:
    """Tests for date format parsing."""

    def test_iso_format(self, parser):
        date = parser._parse_date("2025-01-15")
        assert date == datetime(2025, 1, 15)

    def test_dd_mm_yyyy_dash(self, parser):
        date = parser._parse_date("15-01-2025")
        assert date == datetime(2025, 1, 15)

    def test_dd_mm_yyyy_slash(self, parser):
        date = parser._parse_date("15/01/2025")
        assert date == datetime(2025, 1, 15)

    def test_with_time(self, parser):
        date = parser._parse_date("2025-01-15 14:30:00")
        assert date == datetime(2025, 1, 15, 14, 30, 0)

    def test_invalid_date(self, parser):
        date = parser._parse_date("not-a-date")
        assert date is None

    def test_empty_string(self, parser):
        date = parser._parse_date("")
        assert date is None


class TestAmountParsing:
    """Tests for amount string cleaning."""

    def test_simple_amount(self, parser):
        assert parser._parse_amount("450.00") == 450.00

    def test_with_rupee_symbol(self, parser):
        assert parser._parse_amount("₹1,450.00") == 1450.00

    def test_with_rs_prefix(self, parser):
        assert parser._parse_amount("Rs. 500") == 500.00

    def test_with_commas(self, parser):
        assert parser._parse_amount("25,000.00") == 25000.00

    def test_negative_amount(self, parser):
        amount = parser._parse_amount("-450.00")
        assert amount == 450.00  # Should be absolute

    def test_invalid_amount(self, parser):
        assert parser._parse_amount("abc") is None


class TestMerchantExtraction:
    """Tests for merchant name extraction from descriptions."""

    def test_swiggy_upi(self, parser):
        merchant = parser._extract_merchant("UPI-GooglePay-swiggy@paytm-SBIN")
        assert merchant == "Swiggy"

    def test_zomato(self, parser):
        merchant = parser._extract_merchant("UPI-PhonePe-zomato@axisbank-Food")
        assert merchant == "Zomato"

    def test_uber(self, parser):
        merchant = parser._extract_merchant("UPI-GPay-uber@icici-Ride")
        assert merchant == "Uber"

    def test_amazon(self, parser):
        merchant = parser._extract_merchant("POS-Amazon Pay-Electronics")
        assert merchant == "Amazon"

    def test_unknown_merchant(self, parser):
        merchant = parser._extract_merchant("Some Random Store Payment")
        assert isinstance(merchant, str)
        assert len(merchant) > 0


class TestPaymentModeDetection:
    """Tests for payment mode detection."""

    def test_explicit_upi(self, parser):
        mode = parser._detect_payment_mode("some txn", "UPI")
        assert mode == PaymentMode.UPI

    def test_explicit_card(self, parser):
        mode = parser._detect_payment_mode("some txn", "Card")
        assert mode == PaymentMode.CARD

    def test_upi_in_description(self, parser):
        mode = parser._detect_payment_mode("UPI-GooglePay-merchant", None)
        assert mode == PaymentMode.UPI

    def test_pos_in_description(self, parser):
        mode = parser._detect_payment_mode("POS-Amazon-Electronics", None)
        assert mode == PaymentMode.CARD

    def test_neft_in_description(self, parser):
        mode = parser._detect_payment_mode("NEFT-Rent Transfer", None)
        assert mode == PaymentMode.NET_BANKING

    def test_unknown_mode(self, parser):
        mode = parser._detect_payment_mode("random payment", None)
        assert mode == PaymentMode.UNKNOWN


class TestFullParsing:
    """Tests for the complete parsing pipeline."""

    def test_parse_valid_transaction(self, parser):
        raw = RawTransaction(
            date="2025-01-15",
            description="UPI-GooglePay-swiggy@paytm-SBIN",
            amount="450.00",
            mode="UPI",
            reference_id="TXN123",
        )
        parsed, errors = parser.parse_transactions([raw])
        assert len(parsed) == 1
        assert len(errors) == 0
        assert parsed[0].merchant == "Swiggy"
        assert parsed[0].amount == 450.00
        assert parsed[0].mode == PaymentMode.UPI

    def test_parse_invalid_date_skips(self, parser):
        raw = RawTransaction(
            date="invalid-date",
            description="some transaction",
            amount="100.00",
        )
        parsed, errors = parser.parse_transactions([raw])
        assert len(parsed) == 0
        assert len(errors) == 1

    def test_parse_invalid_amount_skips(self, parser):
        raw = RawTransaction(
            date="2025-01-15",
            description="some transaction",
            amount="not-a-number",
        )
        parsed, errors = parser.parse_transactions([raw])
        assert len(parsed) == 0
        assert len(errors) == 1

    def test_parse_multiple_transactions(self, parser):
        raws = [
            RawTransaction(
                date="2025-01-15",
                description="UPI-swiggy@paytm",
                amount="450.00",
                mode="UPI",
            ),
            RawTransaction(
                date="2025-01-16",
                description="POS-Amazon-Electronics",
                amount="12500.00",
                mode="Card",
            ),
        ]
        parsed, errors = parser.parse_transactions(raws)
        assert len(parsed) == 2
        assert len(errors) == 0
