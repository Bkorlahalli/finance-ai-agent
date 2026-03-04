"""
Agent Orchestrator — Coordinates the multi-agent pipeline.

Manages the sequential execution of all agents:
Ingestion → Parsing → Categorization → Storage → Analysis → Alerting

This is the central entry point for processing transaction data
through the entire agent pipeline.
"""

from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.agents.ingestion_agent import IngestionAgent
from app.agents.parsing_agent import ParsingAgent
from app.agents.categorization_agent import CategorizationAgent
from app.agents.storage_agent import StorageAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.alert_agent import AlertAgent
from app.schemas.transaction_schema import (
    UploadResponse,
    FinancialInsights,
    AlertResponse,
    TransactionResponse,
)

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """
    Orchestrates the multi-agent transaction processing pipeline.

    Coordinates data flow between all agents in the correct order,
    aggregating results and errors from each stage.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize orchestrator with database session and all agents.

        Args:
            db: SQLAlchemy session for storage, analysis, and alert agents.
        """
        self.db = db

        # Initialize pipeline agents
        self.ingestion_agent = IngestionAgent()
        self.parsing_agent = ParsingAgent()
        self.categorization_agent = CategorizationAgent()
        self.storage_agent = StorageAgent(db)
        self.analysis_agent = AnalysisAgent(db)
        self.alert_agent = AlertAgent(db)

        logger.info("AgentOrchestrator initialized with all 6 agents.")

    def process_csv(self, csv_content: str) -> UploadResponse:
        """
        Execute the full agent pipeline on CSV content.

        Pipeline: Ingest → Parse → Categorize → Store → Alert

        Args:
            csv_content: Raw CSV file content as string.

        Returns:
            UploadResponse with processing results and any alerts.
        """
        all_errors: List[str] = []
        logger.info("=" * 60)
        logger.info("🚀 Starting agent pipeline execution")
        logger.info("=" * 60)

        # ─── Stage 1: Ingestion ──────────────────────────────────
        logger.info("📥 Stage 1: Ingestion Agent")
        raw_transactions, ingest_errors = self.ingestion_agent.ingest_csv(csv_content)
        all_errors.extend(ingest_errors)

        if not raw_transactions:
            logger.error("Ingestion produced no transactions. Aborting pipeline.")
            return UploadResponse(
                status="error",
                total_processed=0,
                total_categorized=0,
                total_stored=0,
                errors=all_errors or ["No transactions could be ingested from the CSV."],
            )

        logger.info("  → Ingested %d raw transactions", len(raw_transactions))

        # ─── Stage 2: Parsing ────────────────────────────────────
        logger.info("🧹 Stage 2: Parsing Agent")
        parsed_transactions, parse_errors = self.parsing_agent.parse_transactions(
            raw_transactions
        )
        all_errors.extend(parse_errors)

        if not parsed_transactions:
            logger.error("Parsing produced no transactions. Aborting pipeline.")
            return UploadResponse(
                status="error",
                total_processed=len(raw_transactions),
                total_categorized=0,
                total_stored=0,
                errors=all_errors,
            )

        logger.info("  → Parsed %d transactions", len(parsed_transactions))

        # ─── Stage 3: Categorization ────────────────────────────
        logger.info("🏷️  Stage 3: Categorization Agent")
        categorized_transactions, cat_errors = (
            self.categorization_agent.categorize_transactions(parsed_transactions)
        )
        all_errors.extend(cat_errors)

        if not categorized_transactions:
            logger.error("Categorization produced no transactions. Aborting pipeline.")
            return UploadResponse(
                status="error",
                total_processed=len(raw_transactions),
                total_categorized=0,
                total_stored=0,
                errors=all_errors,
            )

        logger.info("  → Categorized %d transactions", len(categorized_transactions))

        # ─── Stage 4: Storage ────────────────────────────────────
        logger.info("💾 Stage 4: Storage Agent")
        stored_count, storage_messages = self.storage_agent.store_transactions(
            categorized_transactions
        )
        all_errors.extend(
            [msg for msg in storage_messages if "error" in msg.lower() or "failed" in msg.lower()]
        )

        logger.info("  → Stored %d transactions", stored_count)

        # ─── Stage 5: Alert Check ────────────────────────────────
        logger.info("🚨 Stage 5: Alert Agent")
        transaction_dates = [t.date for t in categorized_transactions]
        alerts = self.alert_agent.check_for_new_transactions(transaction_dates)

        logger.info("  → Generated %d alerts", len(alerts))

        # ─── Pipeline Complete ───────────────────────────────────
        status = "success" if stored_count > 0 else "partial"
        logger.info("=" * 60)
        logger.info(
            "✅ Pipeline complete: %d ingested → %d parsed → %d categorized → %d stored",
            len(raw_transactions),
            len(parsed_transactions),
            len(categorized_transactions),
            stored_count,
        )
        logger.info("=" * 60)

        return UploadResponse(
            status=status,
            total_processed=len(raw_transactions),
            total_categorized=len(categorized_transactions),
            total_stored=stored_count,
            alerts=alerts,
            errors=all_errors,
        )

    def get_insights(self) -> FinancialInsights:
        """
        Generate financial insights using the Analysis Agent.

        Returns:
            FinancialInsights with all analytics data.
        """
        logger.info("📊 Generating financial insights...")
        return self.analysis_agent.generate_insights()

    def get_alerts(self, days_back: int = 7) -> List[AlertResponse]:
        """
        Check spending alerts using the Alert Agent.

        Args:
            days_back: Number of days to check for alerts.

        Returns:
            List of AlertResponse objects.
        """
        logger.info("🚨 Checking spending alerts (last %d days)...", days_back)
        return self.alert_agent.check_alerts(days_back=days_back)

    def get_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        category: str | None = None,
    ) -> List[TransactionResponse]:
        """
        Retrieve stored transactions with optional filtering.

        Args:
            limit: Maximum results to return.
            offset: Results to skip for pagination.
            category: Optional category filter.

        Returns:
            List of TransactionResponse objects.
        """
        transactions = self.storage_agent.get_all_transactions(
            limit=limit, offset=offset, category=category
        )
        return [
            TransactionResponse(
                id=t.id,
                date=t.date,
                amount=t.amount,
                merchant=t.merchant,
                description=t.description,
                mode=t.mode,
                category=t.category,
                confidence_score=t.confidence_score,
                reference_id=t.reference_id,
                created_at=t.created_at,
            )
            for t in transactions
        ]
