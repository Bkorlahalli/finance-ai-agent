"""
FastAPI route definitions for the Finance AI Agent API.

Exposes endpoints for:
- CSV file upload and processing
- Transaction listing with filters
- Financial insights and summaries
- Spending alerts
- Health check
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.services.agent_orchestrator import AgentOrchestrator
from app.schemas.transaction_schema import (
    TransactionResponse,
    FinancialInsights,
    AlertResponse,
    UploadResponse,
    HealthResponse,
)
from app.core.config import get_settings

logger = get_logger("api.routes")

router = APIRouter()


def get_orchestrator(db: Session = Depends(get_db)) -> AgentOrchestrator:
    """Dependency injection for AgentOrchestrator."""
    return AgentOrchestrator(db)


# ─── Health Check ────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.

    Returns application status, version, and configuration state.
    """
    settings = get_settings()

    # Quick DB check
    db_status = "connected"
    try:
        from app.db.database import SessionLocal
        db = SessionLocal()
        db.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )
        db.close()
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
        openai_configured=settings.is_openai_configured,
    )


# ─── Upload CSV ──────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, tags=["Transactions"])
async def upload_transactions(
    file: UploadFile = File(...),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Upload a CSV file of transactions for processing.

    The file goes through the full agent pipeline:
    Ingestion → Parsing → Categorization → Storage → Alerting

    **Accepted CSV columns:**
    - `date` (required) — Transaction date
    - `description` (required) — Transaction description/narration
    - `amount` (required) — Transaction amount
    - `mode` (optional) — Payment mode (UPI, Card, etc.)
    - `reference_id` (optional) — Unique transaction reference
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted. Please upload a .csv file.",
        )

    # Read file content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            csv_content = content.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file. Please ensure it is UTF-8 encoded.",
            )

    # Validate file is not empty
    if not csv_content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate file size (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB.",
        )

    logger.info("Processing uploaded file: %s (%d bytes)", file.filename, len(content))

    # Run the agent pipeline
    result = orchestrator.process_csv(csv_content)

    return result


# ─── Get Transactions ────────────────────────────────────────────────

@router.get("/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
async def list_transactions(
    limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Skip N results"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    List stored transactions with optional filtering.

    Supports pagination via `limit` and `offset` parameters.
    Filter by category using the `category` query parameter.

    **Available categories:** Food, Travel, Rent, Shopping, Recharge, Investment, Misc
    """
    transactions = orchestrator.get_transactions(
        limit=limit, offset=offset, category=category
    )

    if not transactions:
        logger.info("No transactions found matching the query.")

    return transactions


# ─── Financial Summary ───────────────────────────────────────────────

@router.get("/summary", response_model=FinancialInsights, tags=["Analytics"])
async def get_summary(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Get comprehensive financial insights and spending summary.

    Returns:
    - **Total spending** and transaction count
    - **Category breakdown** with percentages
    - **Top merchants** by spending
    - **Weekly spending trends**
    """
    insights = orchestrator.get_insights()

    if insights.total_transactions == 0:
        logger.info("No transactions available for summary.")

    return insights


# ─── Spending Alerts ─────────────────────────────────────────────────

@router.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(
    days: int = Query(default=7, ge=1, le=90, description="Days to check"),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Check for spending alerts in the recent period.

    Returns alerts for days where spending exceeded the configured
    daily threshold (default: ₹5,000).

    **Alert severity levels:**
    - `warning` — 1x-1.5x threshold
    - `high` — 1.5x-2x threshold
    - `critical` — 2x+ threshold
    """
    alerts = orchestrator.get_alerts(days_back=days)
    return alerts
