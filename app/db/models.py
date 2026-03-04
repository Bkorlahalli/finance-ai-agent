"""
SQLAlchemy ORM models for the finance database.

Defines the Transaction table with all fields needed for
expense tracking, categorization, and analysis.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func

from app.db.database import Base


class Transaction(Base):
    """
    Represents a single financial transaction.

    Stores parsed, categorized transaction data with metadata
    for analysis and alerting.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Core transaction fields
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    merchant = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Transaction metadata
    mode = Column(String(50), nullable=True)  # UPI, Card, NetBanking, etc.
    reference_id = Column(String(100), nullable=True, unique=True)

    # Categorization
    category = Column(String(50), nullable=False, default="Misc", index=True)
    confidence_score = Column(Float, nullable=True)  # LLM confidence

    # Tracking
    is_alerted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, date={self.date}, "
            f"amount={self.amount}, merchant='{self.merchant}', "
            f"category='{self.category}')>"
        )
