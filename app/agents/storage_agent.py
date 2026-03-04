"""
Storage Agent — Persists categorized transactions to SQLite via SQLAlchemy.

Responsibilities:
- Store CategorizedTransaction objects as database records
- Handle duplicate detection via reference_id
- Provide query methods for analysis and alerting
- Support bulk insert operations
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.logging_config import get_logger
from app.db.models import Transaction
from app.schemas.transaction_schema import CategorizedTransaction, TransactionResponse

logger = get_logger("storage_agent")


class StorageAgent:
    """
    Agent responsible for persisting transactions to the database.

    Handles CRUD operations, duplicate detection, and provides
    query interfaces for the Analysis and Alert agents.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize StorageAgent with a database session.

        Args:
            db: SQLAlchemy session instance.
        """
        self.db = db
        logger.info("StorageAgent initialized.")

    def store_transactions(
        self, transactions: List[CategorizedTransaction]
    ) -> Tuple[int, List[str]]:
        """
        Store a batch of categorized transactions.

        Skips duplicates based on reference_id if present.

        Args:
            transactions: List of categorized transactions to store.

        Returns:
            Tuple of (number stored, list of error/skip messages).
        """
        stored_count = 0
        messages: List[str] = []

        for txn in transactions:
            try:
                # Check for duplicates by reference_id
                if txn.reference_id:
                    existing = (
                        self.db.query(Transaction)
                        .filter(Transaction.reference_id == txn.reference_id)
                        .first()
                    )
                    if existing:
                        messages.append(
                            f"Skipped duplicate: ref_id={txn.reference_id}"
                        )
                        logger.debug("Skipped duplicate transaction: %s", txn.reference_id)
                        continue

                db_record = Transaction(
                    date=txn.date,
                    amount=txn.amount,
                    merchant=txn.merchant,
                    description=txn.description,
                    mode=txn.mode.value,
                    reference_id=txn.reference_id,
                    category=txn.category.value,
                    confidence_score=txn.confidence_score,
                )
                self.db.add(db_record)
                stored_count += 1

            except Exception as e:
                error_msg = f"Failed to store transaction ({txn.merchant}): {e}"
                messages.append(error_msg)
                logger.warning(error_msg)

        try:
            self.db.commit()
            logger.info("Stored %d transactions successfully.", stored_count)
        except Exception as e:
            self.db.rollback()
            error_msg = f"Database commit failed: {e}"
            messages.append(error_msg)
            logger.error(error_msg)
            stored_count = 0

        return stored_count, messages

    def get_all_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Transaction]:
        """
        Query transactions with optional filters.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.
            category: Filter by category name.
            start_date: Filter transactions on or after this date.
            end_date: Filter transactions on or before this date.

        Returns:
            List of Transaction ORM objects.
        """
        query = self.db.query(Transaction)

        if category:
            query = query.filter(Transaction.category == category)
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        return (
            query.order_by(Transaction.date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_transactions_by_date(self, target_date: datetime) -> List[Transaction]:
        """
        Get all transactions for a specific date.

        Args:
            target_date: Date to query.

        Returns:
            List of Transaction objects for that date.
        """
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return (
            self.db.query(Transaction)
            .filter(Transaction.date >= start, Transaction.date < end)
            .all()
        )

    def get_daily_totals(self, days: int = 30) -> List[Tuple[str, float, int]]:
        """
        Get daily spending totals for the last N days.

        Args:
            days: Number of days to look back.

        Returns:
            List of (date_string, total_amount, transaction_count) tuples.
        """
        since = datetime.utcnow() - timedelta(days=days)
        results = (
            self.db.query(
                func.date(Transaction.date).label("day"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.date >= since)
            .group_by(func.date(Transaction.date))
            .order_by(func.date(Transaction.date).desc())
            .all()
        )
        return [(str(r.day), float(r.total), int(r.count)) for r in results]

    def get_category_totals(self) -> List[Tuple[str, float, int]]:
        """
        Get spending totals grouped by category.

        Returns:
            List of (category, total_amount, transaction_count) tuples.
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
        return [(r.category, float(r.total), int(r.count)) for r in results]

    def get_top_merchants(self, limit: int = 10) -> List[Tuple[str, float, int]]:
        """
        Get top merchants by total spending.

        Args:
            limit: Number of top merchants to return.

        Returns:
            List of (merchant, total_amount, transaction_count) tuples.
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
        return [(r.merchant, float(r.total), int(r.count)) for r in results]

    def get_total_spending(self) -> float:
        """Get total spending across all transactions."""
        result = self.db.query(func.sum(Transaction.amount)).scalar()
        return float(result) if result else 0.0

    def get_transaction_count(self) -> int:
        """Get total number of transactions."""
        return self.db.query(func.count(Transaction.id)).scalar() or 0
