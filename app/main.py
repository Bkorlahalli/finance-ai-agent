"""
Personal Finance Multi-Agent Expense Tracker — Main Application Entry Point.

Initializes FastAPI application, configures middleware, registers routes,
and sets up database on startup.

Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.db.database import init_db
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs database initialization on startup.
    """
    # Startup
    logger = setup_logging()
    logger.info("🚀 Starting %s v%s", settings.app_name, settings.app_version)

    # Initialize database tables
    init_db()
    logger.info("✅ Application started successfully.")

    yield

    # Shutdown
    logger.info("👋 Shutting down application.")


# Load settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A production-ready multi-agent AI system for personal finance tracking. "
        "Automatically ingests, parses, categorizes, and analyzes expense transactions "
        "using a pipeline of specialized agents powered by LangChain and OpenAI."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router, prefix="", tags=["Finance Agent API"])
