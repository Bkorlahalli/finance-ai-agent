"""
Analysis Agent — Generates financial insights from stored transactions.

Responsibilities:
- Calculate category-wise spending breakdown
- Identify top merchants by spending
- Generate weekly spending trends
- Compute summary statistics
"""

from datetime import datetime, timedelta
from typing import List

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.logging_config import get_logger
from app.db.models import Transaction
from app.schemas.transaction_schema import (
    FinancialInsights,
    CategoryBreakdown,
    MerchantSummary,
    SpendingTrend,
)

logger = get_logger("analysis_agent")


class AnalysisAgent:
    """
    Agent responsible for generating financial insights and analytics.

    Queries stored transactions and produces comprehensive spending
    summaries, trends, and category breakdowns.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize AnalysisAgent with database session.

        Args:
            db: SQLAlchemy session instance.
        """
        self.db = db
        logger.info("AnalysisAgent initialized.")

    def _get_category_breakdown(self) -> List[CategoryBreakdown]:
        """
        Calculate spending breakdown by category.

        Returns:
            List of CategoryBreakdown with amounts and percentages.
        """
        results = (
            self.db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        grand_total = sum(r.total for r in results) if results else 1.0

        return [
            CategoryBreakdown(
                category=r.category,
                total_amount=round(float(r.total), 2),
                transaction_count=int(r.count),
                percentage=round((float(r.total) / grand_total) * 100, 1),
            )
            for r in results
        ]

    def _get_top_merchants(self, limit: int = 10) -> List[MerchantSummary]:
        """
        Get top merchants ranked by total spending.

        Args:
            limit: Number of merchants to return.

        Returns:
            List of MerchantSummary objects.
        """
        results = (
            self.db.query(
                Transaction.merchant,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
            .all()
        )

        return [
            MerchantSummary(
                merchant=r.merchant,
                total_amount=round(float(r.total), 2),
                transaction_count=int(r.count),
            )
            for r in results
        ]

    def _get_weekly_trends(self, weeks: int = 8) -> List[SpendingTrend]:
        """
        Calculate weekly spending trends.

        Args:
            weeks: Number of weeks to analyze.

        Returns:
            List of SpendingTrend objects with weekly aggregates.
        """
        # Get all transactions within the period
        since = datetime.utcnow() - timedelta(weeks=weeks)
        transactions = (
            self.db.query(Transaction)
            .filter(Transaction.date >= since)
            .all()
        )

        if not transactions:
            return []

        # Use pandas for weekly aggregation
        data = [
            {"date": t.date, "amount": t.amount}
            for t in transactions
        ]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # Resample to weekly periods
        weekly = df.resample("W").agg(
            total_amount=("amount", "sum"),
            transaction_count=("amount", "count"),
        ).reset_index()

        return [
            SpendingTrend(
                week=row["date"].strftime("%Y-W%U"),
                total_amount=round(float(row["total_amount"]), 2),
                transaction_count=int(row["transaction_count"]),
            )
            for _, row in weekly.iterrows()
        ]

    def generate_insights(self) -> FinancialInsights:
        """
        Generate comprehensive financial insights.

        Returns:
            FinancialInsights object with all analytics data.
        """
        logger.info("Generating financial insights...")

        # Get summary statistics
        total_spending = self.db.query(func.sum(Transaction.amount)).scalar() or 0.0
        total_transactions = self.db.query(func.count(Transaction.id)).scalar() or 0

        # Get date range
        min_date = self.db.query(func.min(Transaction.date)).scalar()
        max_date = self.db.query(func.max(Transaction.date)).scalar()

        avg_transaction = (
            round(float(total_spending) / total_transactions, 2)
            if total_transactions > 0
            else 0.0
        )

        # Generate all breakdowns
        category_breakdown = self._get_category_breakdown()
        top_merchants = self._get_top_merchants()
        weekly_trends = self._get_weekly_trends()

        insights = FinancialInsights(
            total_spending=round(float(total_spending), 2),
            total_transactions=total_transactions,
            average_transaction=avg_transaction,
            category_breakdown=category_breakdown,
            top_merchants=top_merchants,
            weekly_trends=weekly_trends,
            period_start=min_date,
            period_end=max_date,
        )

        logger.info(
            "Insights generated: ₹%.2f total across %d transactions.",
            insights.total_spending,
            insights.total_transactions,
        )
        return insights
