# 🏦 Personal Finance Multi-Agent Expense Tracker

A production-ready multi-agent AI system that automatically ingests, parses, categorizes, and analyzes your personal expense transactions using a pipeline of specialized agents powered by **LangChain** and **OpenAI**.

---

## ✨ Features

- **📥 CSV Ingestion** — Upload bank/UPI transaction CSVs with flexible column mapping
- **🧹 Smart Parsing** — Extracts merchant names from UPI descriptions, handles multiple date formats
- **🏷️ AI Categorization** — LLM-powered expense categorization (Food, Travel, Rent, Shopping, etc.)
- **💾 SQLite Storage** — Persistent storage with duplicate detection
- **📊 Financial Insights** — Category breakdowns, top merchants, weekly spending trends
- **🚨 Spending Alerts** — Configurable daily spending threshold alerts with severity levels
- **🌐 REST API** — FastAPI endpoints with auto-generated Swagger documentation
- **🔄 Fallback Mode** — Rule-based categorization when OpenAI API is unavailable

---

## 🏗️ Architecture

```
CSV Upload → Ingestion Agent → Parsing Agent → Categorization Agent (LLM)
                                                        ↓
              Alert Agent ← Storage Agent (SQLite) ← Categorized Data
                                    ↓
                           Analysis Agent → API Response
```

### Agent Pipeline

| Agent | Description |
|-------|-------------|
| **Ingestion Agent** | Reads CSV, validates schema, converts to standardized JSON |
| **Parsing Agent** | Cleans fields, extracts amount/merchant/date/mode from UPI descriptions |
| **Categorization Agent** | Uses OpenAI GPT to classify transactions into 7 categories |
| **Storage Agent** | Persists to SQLite with duplicate detection via reference IDs |
| **Analysis Agent** | Generates weekly summaries, category distributions, top merchants |
| **Alert Agent** | Triggers alerts when daily spending exceeds configurable threshold |

### Why LangChain over CrewAI?

- **Granular Control** — Each agent is individually configured with custom prompts and chains
- **Deterministic Pipeline** — Sequential execution with clear data contracts (Pydantic schemas)
- **Production Stability** — Mature ecosystem with superior error handling and retry logic
- **Structured Output** — Seamless integration with Pydantic for type-safe LLM responses

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (optional — falls back to rule-based categorization)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/finance-ai-agent.git
cd finance-ai-agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

> **Note:** The system works without an OpenAI API key! It will use rule-based categorization as a fallback.

### 5. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Base**: http://localhost:8000

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with system status |
| `POST` | `/upload` | Upload CSV transaction file |
| `GET` | `/transactions` | List transactions (with pagination & filtering) |
| `GET` | `/summary` | Get financial insights and analytics |
| `GET` | `/alerts` | Check spending alerts |

---

## 🧪 Example API Usage

### Upload Transactions

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@data/sample_transactions.csv"
```

### Get Transactions

```bash
# All transactions
curl "http://localhost:8000/transactions"

# With pagination
curl "http://localhost:8000/transactions?limit=10&offset=0"

# Filter by category
curl "http://localhost:8000/transactions?category=Food"
```

### Get Financial Summary

```bash
curl "http://localhost:8000/summary"
```

**Example Response:**
```json
{
  "total_spending": 96726.0,
  "total_transactions": 25,
  "average_transaction": 3869.04,
  "category_breakdown": [
    {"category": "Rent", "total_amount": 25000.0, "transaction_count": 1, "percentage": 25.8},
    {"category": "Investment", "total_amount": 30000.0, "transaction_count": 3, "percentage": 31.0},
    {"category": "Food", "total_amount": 3700.0, "transaction_count": 7, "percentage": 3.8}
  ],
  "top_merchants": [
    {"merchant": "Groww", "total_amount": 15000.0, "transaction_count": 2},
    {"merchant": "Zerodha", "total_amount": 15000.0, "transaction_count": 1}
  ],
  "weekly_trends": [
    {"week": "2025-W02", "total_amount": 45000.0, "transaction_count": 8}
  ]
}
```

### Check Alerts

```bash
# Last 7 days
curl "http://localhost:8000/alerts"

# Last 30 days
curl "http://localhost:8000/alerts?days=30"
```

### Health Check

```bash
curl "http://localhost:8000/health"
```

---

## 📁 Project Structure

```
finance-ai-agent/
│
├── app/
│   ├── agents/
│   │   ├── ingestion_agent.py      # CSV reader & validator
│   │   ├── parsing_agent.py        # Data cleaner & merchant extractor
│   │   ├── categorization_agent.py # LLM categorizer with fallback rules
│   │   ├── storage_agent.py        # SQLite persistence layer
│   │   ├── analysis_agent.py       # Financial insights generator
│   │   └── alert_agent.py          # Spending threshold monitor
│   │
│   ├── core/
│   │   ├── config.py               # Settings management (pydantic-settings)
│   │   └── logging_config.py       # Structured logging setup
│   │
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   └── database.py             # Engine, session factory, migrations
│   │
│   ├── schemas/
│   │   └── transaction_schema.py   # Pydantic data contracts
│   │
│   ├── services/
│   │   └── agent_orchestrator.py   # Pipeline coordinator
│   │
│   ├── api/
│   │   └── routes.py               # FastAPI route definitions
│   │
│   └── main.py                     # Application entry point
│
├── data/
│   └── sample_transactions.csv     # 25 sample UPI/Card transactions
│
├── tests/
│   ├── test_parsing_agent.py       # Parsing agent unit tests
│   ├── test_ingestion_agent.py     # Ingestion agent unit tests
│   └── test_api.py                 # API integration tests
│
├── .env.example                    # Environment variable template
├── requirements.txt                # Pinned Python dependencies
├── Dockerfile                      # Production Docker image
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parsing_agent.py -v

# Run with coverage
pytest tests/ -v --tb=short
```

---

## 🐳 Docker

### Build and Run

```bash
# Build the image
docker build -t finance-ai-agent .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  --name finance-agent \
  finance-ai-agent
```

---

## ⚙️ Configuration

All settings are loaded from environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key for LLM categorization |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model to use |
| `DATABASE_URL` | `sqlite:///./data/finance.db` | Database connection string |
| `DAILY_SPENDING_THRESHOLD` | `5000.0` | Daily spending alert threshold (₹) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `false` | Debug mode |

---

## 📊 Supported CSV Format

Your CSV should have at minimum these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `date` | ✅ | Transaction date (multiple formats supported) |
| `description` | ✅ | Transaction narration/details |
| `amount` | ✅ | Transaction amount |
| `mode` | ❌ | Payment mode (UPI, Card, NetBanking) |
| `reference_id` | ❌ | Unique transaction reference |

> Column names are **flexible** — the system auto-maps common variations like `txn_date`, `narration`, `txn_amount`, etc.

---

## 🔐 Security

- ✅ API keys loaded from environment variables (never hardcoded)
- ✅ CSV input validated for structure, size (max 10MB), and encoding
- ✅ SQL injection prevented via SQLAlchemy ORM
- ✅ Input sanitization on all API endpoints
- ✅ `.env` excluded from version control via `.gitignore`

---

## 📝 License

MIT License

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
