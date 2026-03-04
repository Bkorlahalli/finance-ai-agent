"""
Parsing Agent — Cleans raw transaction fields and extracts structured data.

Responsibilities:
- Parse dates from multiple formats
- Clean and normalize amount strings
- Extract merchant names from transaction descriptions
- Detect payment mode from description patterns
- Convert RawTransaction → ParsedTransaction
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from app.core.logging_config import get_logger
from app.schemas.transaction_schema import (
    RawTransaction,
    ParsedTransaction,
    PaymentMode,
)

logger = get_logger("parsing_agent")

# Regex patterns for merchant extraction from UPI descriptions
UPI_PATTERNS = [
    # "UPI-GooglePay-swiggy@paytm-SBIN" → "Swiggy"
    re.compile(r"UPI[-/]?\w*[-/]?(\w+)@", re.IGNORECASE),
    # "UPI/DR/123456/swiggy/PayTM" → "Swiggy"
    re.compile(r"UPI/\w+/\d+/(\w+)", re.IGNORECASE),
]

# Known merchant keyword mappings
MERCHANT_KEYWORDS = {
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "uber": "Uber",
    "ola": "Ola",
    "paytm": "Paytm",
    "phonepe": "PhonePe",
    "gpay": "Google Pay",
    "googlepay": "Google Pay",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "airtel": "Airtel",
    "jio": "Jio",
    "vodafone": "Vodafone",
    "bigbasket": "BigBasket",
    "myntra": "Myntra",
    "rapido": "Rapido",
    "blinkit": "Blinkit",
    "zerodha": "Zerodha",
    "groww": "Groww",
    "cred": "CRED",
}

# Date format patterns to try
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


class ParsingAgent:
    """
    Agent responsible for cleaning and parsing raw transaction data.

    Extracts merchant names, normalizes amounts, parses dates,
    and detects payment modes from raw transaction descriptions.
    """

    def __init__(self) -> None:
        self.errors: List[str] = []
        logger.info("ParsingAgent initialized.")

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string trying multiple formats.

        Args:
            date_str: Raw date string from CSV.

        Returns:
            Parsed datetime or None if all formats fail.
        """
        date_str = date_str.strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse amount string to float, handling currency symbols and commas.

        Args:
            amount_str: Raw amount string (e.g., "₹1,450.00", "Rs. 500").

        Returns:
            Parsed float or None on failure.
        """
        try:
            # Remove currency symbols, commas, and whitespace
            cleaned = re.sub(r"[₹$€£Rs.\s,]", "", amount_str.strip())
            # Handle negative amounts (debits)
            cleaned = cleaned.replace("(", "-").replace(")", "")
            amount = float(cleaned)
            return abs(amount)  # Treat all as positive spend
        except (ValueError, TypeError):
            return None

    def _extract_merchant(self, description: str) -> str:
        """
        Extract merchant name from transaction description.

        Uses UPI patterns, keyword matching, and fallback heuristics.

        Args:
            description: Raw transaction description.

        Returns:
            Extracted merchant name.
        """
        desc_lower = description.lower()

        # Try known merchant keywords first
        for keyword, merchant_name in MERCHANT_KEYWORDS.items():
            if keyword in desc_lower:
                return merchant_name

        # Try UPI regex patterns
        for pattern in UPI_PATTERNS:
            match = pattern.search(description)
            if match:
                return match.group(1).strip().title()

        # Fallback: clean up the description itself
        # Remove common prefixes
        cleaned = re.sub(
            r"^(UPI[-/]|NEFT[-/]|IMPS[-/]|POS[-/]|ATM[-/]|DR[-/]|CR[-/])",
            "",
            description,
            flags=re.IGNORECASE,
        )
        # Take first meaningful segment
        parts = re.split(r"[-/|@]", cleaned)
        for part in parts:
            part = part.strip()
            if len(part) > 2 and not part.isdigit():
                return part.title()[:50]

        return description[:50].title()

    def _detect_payment_mode(self, description: str, raw_mode: Optional[str]) -> PaymentMode:
        """
        Detect payment mode from description or explicit mode field.

        Args:
            description: Transaction description text.
            raw_mode: Optional explicit mode value from CSV.

        Returns:
            Detected PaymentMode enum value.
        """
        # Check explicit mode first
        if raw_mode:
            mode_lower = raw_mode.strip().lower()
            mode_map = {
                "upi": PaymentMode.UPI,
                "card": PaymentMode.CARD,
                "debit card": PaymentMode.CARD,
                "credit card": PaymentMode.CARD,
                "net banking": PaymentMode.NET_BANKING,
                "netbanking": PaymentMode.NET_BANKING,
                "neft": PaymentMode.NET_BANKING,
                "imps": PaymentMode.NET_BANKING,
                "cash": PaymentMode.CASH,
                "wallet": PaymentMode.WALLET,
            }
            if mode_lower in mode_map:
                return mode_map[mode_lower]

        # Infer from description
        desc_lower = description.lower()
        if "upi" in desc_lower:
            return PaymentMode.UPI
        elif any(kw in desc_lower for kw in ["pos", "card", "visa", "mastercard", "rupay"]):
            return PaymentMode.CARD
        elif any(kw in desc_lower for kw in ["neft", "imps", "rtgs"]):
            return PaymentMode.NET_BANKING
        elif any(kw in desc_lower for kw in ["wallet", "paytm wallet"]):
            return PaymentMode.WALLET

        return PaymentMode.UNKNOWN

    def parse_transactions(
        self, raw_transactions: List[RawTransaction]
    ) -> Tuple[List[ParsedTransaction], List[str]]:
        """
        Parse a list of raw transactions into structured format.

        Args:
            raw_transactions: List of RawTransaction from ingestion.

        Returns:
            Tuple of (parsed transactions, error messages).
        """
        self.errors = []
        parsed: List[ParsedTransaction] = []

        for idx, raw in enumerate(raw_transactions):
            try:
                # Parse date
                date = self._parse_date(raw.date)
                if date is None:
                    self.errors.append(f"Row {idx + 1}: Invalid date format '{raw.date}'")
                    continue

                # Parse amount
                amount = self._parse_amount(raw.amount)
                if amount is None or amount <= 0:
                    self.errors.append(f"Row {idx + 1}: Invalid amount '{raw.amount}'")
                    continue

                # Extract merchant
                merchant = self._extract_merchant(raw.description)

                # Detect payment mode
                mode = self._detect_payment_mode(raw.description, raw.mode)

                parsed_txn = ParsedTransaction(
                    date=date,
                    amount=amount,
                    merchant=merchant,
                    description=raw.description,
                    mode=mode,
                    reference_id=raw.reference_id,
                )
                parsed.append(parsed_txn)

            except Exception as e:
                error_msg = f"Row {idx + 1}: Parsing error — {str(e)}"
                self.errors.append(error_msg)
                logger.warning(error_msg)

        logger.info(
            "Parsing complete: %d/%d transactions parsed successfully.",
            len(parsed),
            len(raw_transactions),
        )
        return parsed, self.errors
