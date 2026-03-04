"""
Alert Agent — Monitors spending and triggers alerts when thresholds are exceeded.

Responsibilities:
- Check daily spending against configurable thresholds
- Generate alert objects for high spending days
- Support multiple alert severity levels
- Log alerts for visibility
"""

from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.models import Transaction
from app.schemas.transaction_schema import AlertResponse

logger = get_logger("alert_agent")


class AlertAgent:
    """
    Agent responsible for monitoring spending and generating alerts.

    Checks daily spending totals against configurable thresholds
    and produces alert notifications when limits are exceeded.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize AlertAgent with database session.

        Args:
            db: SQLAlchemy session instance.
        """
        self.db = db
        self.settings = get_settings()
        self.threshold = self.settings.daily_spending_threshold
        logger.info(
            "AlertAgent initialized with daily threshold: ₹%.2f",
            self.threshold,
        )

    def _get_daily_spending(self, target_date: datetime) -> float:
        """
        Get total spending for a specific date.

        Args:
            target_date: Date to check spending for.

        Returns:
            Total amount spent on that date.
        """
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = (
            self.db.query(func.sum(Transaction.amount))
            .filter(Transaction.date >= start, Transaction.date < end)
            .scalar()
        )
        return float(result) if result else 0.0

    def _determine_severity(self, total: float) -> str:
        """
        Determine alert severity based on overspend ratio.

        Args:
            total: Total daily spending amount.

        Returns:
            Severity level string.
        """
        ratio = total / self.threshold
        if ratio >= 2.0:
            return "critical"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.0:
            return "warning"
        return "info"

    def check_alerts(self, days_back: int = 7) -> List[AlertResponse]:
        """
        Check spending alerts for recent days.

        Scans the last N days and generates alerts for any day
        where spending exceeded the configured threshold.

        Args:
            days_back: Number of days to check (default: 7).

        Returns:
            List of AlertResponse objects for threshold violations.
        """
        alerts: List[AlertResponse] = []
        today = datetime.utcnow()

        for i in range(days_back):
            check_date = today - timedelta(days=i)
            daily_total = self._get_daily_spending(check_date)

            if daily_total > self.threshold:
                severity = self._determine_severity(daily_total)
                date_str = check_date.strftime("%Y-%m-%d")

                alert = AlertResponse(
                    alert_type="daily_spending_exceeded",
                    message=(
                        f"⚠️ Daily spending on {date_str} was ₹{daily_total:,.2f}, "
                        f"exceeding threshold of ₹{self.threshold:,.2f} "
                        f"by ₹{daily_total - self.threshold:,.2f}"
                    ),
                    date=date_str,
                    total_spent=daily_total,
                    threshold=self.threshold,
                    severity=severity,
                )
                alerts.append(alert)

                # Log the alert
                logger.warning(
                    "🚨 SPENDING ALERT [%s]: ₹%.2f spent (threshold: ₹%.2f) — Severity: %s",
                    date_str,
                    daily_total,
                    self.threshold,
                    severity.upper(),
                )

        if not alerts:
            logger.info("No spending alerts for the last %d days.", days_back)

        return alerts

    def check_for_new_transactions(
        self, transactions_dates: List[datetime],
    ) -> List[AlertResponse]:
        """
        Check alerts specifically for dates present in newly uploaded transactions.

        This is called after processing a new CSV upload to provide
        immediate feedback on any high-spending days.

        Args:
            transactions_dates: List of dates from newly processed transactions.

        Returns:
            List of AlertResponse objects.
        """
        unique_dates = set(
            dt.replace(hour=0, minute=0, second=0, microsecond=0)
            for dt in transactions_dates
        )
        alerts: List[AlertResponse] = []

        for check_date in sorted(unique_dates):
            daily_total = self._get_daily_spending(check_date)

            if daily_total > self.threshold:
                severity = self._determine_severity(daily_total)
                date_str = check_date.strftime("%Y-%m-%d")

                alert = AlertResponse(
                    alert_type="daily_spending_exceeded",
                    message=(
                        f"⚠️ Daily spending on {date_str} was ₹{daily_total:,.2f}, "
                        f"exceeding threshold of ₹{self.threshold:,.2f}"
                    ),
                    date=date_str,
                    total_spent=daily_total,
                    threshold=self.threshold,
                    severity=severity,
                )
                alerts.append(alert)
                logger.warning(
                    "🚨 NEW UPLOAD ALERT [%s]: ₹%.2f spent", date_str, daily_total
                )

        return alerts
