"""
Pydantic schemas for transaction data validation.

Defines the data contracts between agents at each pipeline stage:
RawTransaction → ParsedTransaction → CategorizedTransaction → Response models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


class TransactionCategory(str, Enum):
    """Supported expense categories for classification."""
    FOOD = "Food"
    TRAVEL = "Travel"
    RENT = "Rent"
    SHOPPING = "Shopping"
    RECHARGE = "Recharge"
    INVESTMENT = "Investment"
    MISC = "Misc"


class PaymentMode(str, Enum):
    """Supported payment modes."""
    UPI = "UPI"
    CARD = "Card"
    NET_BANKING = "NetBanking"
    CASH = "Cash"
    WALLET = "Wallet"
    UNKNOWN = "Unknown"


# ─── Agent Pipeline Schemas ─────────────────────────────────────────

class RawTransaction(BaseModel):
    """Schema for raw transaction data from CSV ingestion."""
    date: str
    description: str
    amount: str
    mode: Optional[str] = None
    reference_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-01-15",
                "description": "UPI-GooglePay-swiggy@paytm-SBIN",
                "amount": "450.00",
                "mode": "UPI",
                "reference_id": "TXN123456789",
            }
        }


class ParsedTransaction(BaseModel):
    """Schema for cleaned and parsed transaction data."""
    date: datetime
    amount: float = Field(gt=0, description="Transaction amount must be positive")
    merchant: str = Field(min_length=1, max_length=255)
    description: str
    mode: PaymentMode = PaymentMode.UNKNOWN
    reference_id: Optional[str] = None

    @field_validator("merchant")
    @classmethod
    def clean_merchant(cls, v: str) -> str:
        """Strip and titlecase merchant name."""
        return v.strip().title()


class CategorizedTransaction(BaseModel):
    """Schema for transaction after LLM categorization."""
    date: datetime
    amount: float
    merchant: str
    description: str
    mode: PaymentMode
    reference_id: Optional[str] = None
    category: TransactionCategory = TransactionCategory.MISC
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="LLM confidence in categorization (0-1)"
    )


# ─── API Response Schemas ────────────────────────────────────────────

class TransactionResponse(BaseModel):
    """API response for a single transaction."""
    id: int
    date: datetime
    amount: float
    merchant: str
    description: Optional[str] = None
    mode: Optional[str] = None
    category: str
    confidence_score: Optional[float] = None
    reference_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryBreakdown(BaseModel):
    """Spending breakdown by category."""
    category: str
    total_amount: float
    transaction_count: int
    percentage: float


class MerchantSummary(BaseModel):
    """Top merchant spending summary."""
    merchant: str
    total_amount: float
    transaction_count: int


class SpendingTrend(BaseModel):
    """Weekly spending trend data point."""
    week: str
    total_amount: float
    transaction_count: int


class FinancialInsights(BaseModel):
    """Complete financial insights response."""
    total_spending: float
    total_transactions: int
    average_transaction: float
    category_breakdown: List[CategoryBreakdown]
    top_merchants: List[MerchantSummary]
    weekly_trends: List[SpendingTrend]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class AlertResponse(BaseModel):
    """Spending alert notification."""
    alert_type: str
    message: str
    date: str
    total_spent: float
    threshold: float
    severity: str = "warning"


class UploadResponse(BaseModel):
    """Response after CSV upload and processing."""
    status: str
    total_processed: int
    total_categorized: int
    total_stored: int
    alerts: List[AlertResponse] = []
    errors: List[str] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    openai_configured: bool
