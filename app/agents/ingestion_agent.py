"""
Ingestion Agent — Reads CSV files and converts to standardized JSON format.

Responsibilities:
- Validate CSV file structure and content
- Map CSV columns to RawTransaction schema
- Handle encoding issues and malformed rows
- Return a list of RawTransaction objects
"""

import csv
import io
from typing import List, Tuple

import pandas as pd

from app.core.logging_config import get_logger
from app.schemas.transaction_schema import RawTransaction

logger = get_logger("ingestion_agent")

# Expected CSV column mappings (flexible matching)
COLUMN_MAPPINGS = {
    "date": ["date", "transaction_date", "txn_date", "trans_date", "Date"],
    "description": ["description", "details", "narration", "remarks", "particulars", "Description"],
    "amount": ["amount", "txn_amount", "transaction_amount", "debit", "Amount"],
    "mode": ["mode", "payment_mode", "type", "txn_type", "channel", "Mode"],
    "reference_id": ["reference_id", "ref_id", "txn_id", "transaction_id", "utr", "Reference"],
}


class IngestionAgent:
    """
    Agent responsible for ingesting raw CSV transaction data.

    Reads CSV files, validates structure, and converts rows
    to standardized RawTransaction objects.
    """

    def __init__(self) -> None:
        self.errors: List[str] = []
        logger.info("IngestionAgent initialized.")

    def _resolve_column(self, columns: List[str], field: str) -> str | None:
        """
        Find the matching CSV column for a given schema field.

        Args:
            columns: List of CSV column names.
            field: Schema field name to match.

        Returns:
            Matched column name, or None if no match found.
        """
        possible_names = COLUMN_MAPPINGS.get(field, [field])
        for col in columns:
            col_lower = col.strip().lower()
            for name in possible_names:
                if col_lower == name.lower():
                    return col
        return None

    def _validate_csv_structure(self, df: pd.DataFrame) -> bool:
        """
        Validate that the CSV has required columns.

        Args:
            df: Pandas DataFrame from CSV.

        Returns:
            True if valid, False otherwise.
        """
        required_fields = ["date", "description", "amount"]
        resolved = {}

        for field in required_fields:
            col = self._resolve_column(df.columns.tolist(), field)
            if col is None:
                self.errors.append(
                    f"Required column '{field}' not found. "
                    f"Available columns: {df.columns.tolist()}"
                )
                return False
            resolved[field] = col

        return True

    def ingest_csv(self, file_content: str) -> Tuple[List[RawTransaction], List[str]]:
        """
        Ingest CSV content and convert to RawTransaction list.

        Args:
            file_content: Raw CSV file content as string.

        Returns:
            Tuple of (list of RawTransaction, list of error messages).
        """
        self.errors = []
        transactions: List[RawTransaction] = []

        try:
            # Read CSV with pandas for robust parsing
            df = pd.read_csv(
                io.StringIO(file_content),
                encoding="utf-8",
                skipinitialspace=True,
                na_values=["", "NA", "N/A", "null", "None"],
            )

            if df.empty:
                self.errors.append("CSV file is empty.")
                return transactions, self.errors

            # Validate structure
            if not self._validate_csv_structure(df):
                return transactions, self.errors

            # Resolve column names
            col_map = {}
            for field in ["date", "description", "amount", "mode", "reference_id"]:
                col_map[field] = self._resolve_column(df.columns.tolist(), field)

            logger.info("CSV loaded with %d rows. Column mapping: %s", len(df), col_map)

            # Convert each row to RawTransaction
            for idx, row in df.iterrows():
                try:
                    raw_txn = RawTransaction(
                        date=str(row.get(col_map["date"], "")).strip(),
                        description=str(row.get(col_map["description"], "")).strip(),
                        amount=str(row.get(col_map["amount"], "0")).strip(),
                        mode=str(row.get(col_map["mode"], "")).strip() if col_map.get("mode") else None,
                        reference_id=(
                            str(row.get(col_map["reference_id"], "")).strip()
                            if col_map.get("reference_id") else None
                        ),
                    )
                    transactions.append(raw_txn)
                except Exception as e:
                    error_msg = f"Row {idx + 1}: Failed to parse — {str(e)}"
                    self.errors.append(error_msg)
                    logger.warning(error_msg)

            logger.info(
                "Ingestion complete: %d transactions parsed, %d errors.",
                len(transactions),
                len(self.errors),
            )

        except pd.errors.ParserError as e:
            self.errors.append(f"CSV parsing error: {str(e)}")
            logger.error("CSV parsing failed: %s", e)
        except Exception as e:
            self.errors.append(f"Unexpected error during ingestion: {str(e)}")
            logger.exception("Unexpected ingestion error")

        return transactions, self.errors
