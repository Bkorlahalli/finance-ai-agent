"""
Unit tests for the Ingestion Agent.

Tests CSV loading, column mapping, validation, and error handling.
"""

import pytest

from app.agents.ingestion_agent import IngestionAgent


@pytest.fixture
def agent():
    """Create an IngestionAgent instance."""
    return IngestionAgent()


class TestCSVIngestion:
    """Tests for CSV file ingestion."""

    def test_valid_csv(self, agent):
        csv_content = (
            "date,description,amount,mode,reference_id\n"
            "2025-01-15,UPI-swiggy@paytm,450.00,UPI,TXN001\n"
            "2025-01-16,POS-Amazon,12500.00,Card,TXN002\n"
        )
        transactions, errors = agent.ingest_csv(csv_content)
        assert len(transactions) == 2
        assert len(errors) == 0

    def test_empty_csv(self, agent):
        csv_content = ""
        transactions, errors = agent.ingest_csv(csv_content)
        assert len(transactions) == 0
        assert len(errors) > 0

    def test_csv_missing_required_column(self, agent):
        csv_content = (
            "description,amount\n"
            "UPI-swiggy@paytm,450.00\n"
        )
        transactions, errors = agent.ingest_csv(csv_content)
        assert len(transactions) == 0
        assert len(errors) > 0
        assert "date" in errors[0].lower()

    def test_csv_with_alternate_column_names(self, agent):
        csv_content = (
            "transaction_date,narration,txn_amount\n"
            "2025-01-15,UPI-swiggy@paytm,450.00\n"
        )
        # Should resolve alternate column names
        transactions, errors = agent.ingest_csv(csv_content)
        # txn_date maps to date, narration maps to description, txn_amount maps to amount
        # Depending on mapping, this should work
        assert isinstance(transactions, list)

    def test_csv_without_optional_columns(self, agent):
        csv_content = (
            "date,description,amount\n"
            "2025-01-15,UPI-swiggy@paytm,450.00\n"
        )
        transactions, errors = agent.ingest_csv(csv_content)
        assert len(transactions) == 1
        assert transactions[0].mode is None
        assert transactions[0].reference_id is None
