# SIH 2026 - Problem Statement 107: BIS Compliance AI Assistant Backend

An AI-powered intelligent compliance assistant and management system for Indian Standards (IS) and Bureau of Indian Standards (BIS) services, built with **FastAPI**, **Inngest**, **Qdrant Vector Database**, and **MySQL**.

---

## 🏛 Architecture Overview

```
Frontend (Next.js @ port 3000)
       │ HTTP / JSON
       ▼
Backend (FastAPI @ port 8000)
 ├── Inngest Event Workflow Orchestration (/api/inngest)
 ├── Qdrant Vector Store (Local on-disk / Cloud cluster RAG)
 └── Relational Database Manager
      ├── Live MySQL Server (bis_compliance database, 12 tables)
      └── Automatic Fallback SQLite (bis_compliance_fallback.db)
```

---

## 📂 Backend Project Structure

```
Backend/
├── main.py                 # FastAPI application, Inngest functions, CORS & all endpoints
├── database.py             # Database manager with all 15 parameterized queries & dual-mode driver
├── vector_db.py            # Qdrant client wrapper for indexing & cosine similarity semantic search
├── data_loader.py          # PDF document text chunking & OpenAI/deterministic vector embeddings
├── custom_types.py         # Pydantic data schemas & response contracts
├── requirements.txt        # Production dependencies
├── .env.example            # Template for environment variables
├── init_db.py              # Script to bootstrap MySQL database from bis_compliance.sql
├── seed_data.py            # Script to seed Qdrant with BIS standards corpus
├── bis_compliance.sql      # Official DDL and seed dataset (12 relational tables)
├── test_backend.py         # Comprehensive test suite verifying all 8 endpoints & 15 queries
└── README.md               # Backend technical documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- (Optional) MySQL 8.0+ running locally or in Docker
- (Optional) OpenAI API Key (for live AI embeddings and LLM answers)

### 2. Setup Virtual Environment
```bash
# In Backend/ directory
python -m venv venv

# Activate venv:
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your settings in `.env`:
```ini
OPENAI_API_KEY=your_openai_api_key_here
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=bis_compliance
FRONTEND_URL=http://localhost:3000
```
> **Note**: If MySQL server is unreachable, the system automatically initializes an SQLite fallback (`bis_compliance_fallback.db`) with identical schema and records, ensuring full endpoint availability.

### 4. Initialize Database & Seed Vectors
```bash
# Initialize MySQL database (if MySQL is running):
python init_db.py

# Seed Qdrant vector database with BIS standards documentation:
python seed_data.py
```

### 5. Run the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Inngest Dev Server: `http://localhost:8000/api/inngest`

---

## 📡 API Endpoints

### Health & Monitoring
- **`GET /api/health`**
  - Returns backend operational status, active database backend (`mysql` or `sqlite_fallback`), and vector DB connectivity.

### Products & Compliance
- **`GET /api/products`**
  - Lists all registered products, categories, manufacturers, and active certification counts.
  - Optional Query Param: `?category_code=ELEC`
- **`GET /api/products/{product_id}`**
  - Returns full product details, applicable Indian standards, requirements breakdown, and test metrics.
- **`GET /api/products/{product_id}/compliance`**
  - Returns comprehensive compliance passport: readiness score percentage, completed vs pending requirements, compliance gaps, and recommended corrective actions.

### Standards & Alerts
- **`GET /api/standards`**
  - Lists active Indian Standards (e.g., IS 13252, IS 616, IS 4250, IS 302-2-15).
  - Optional Query Param: `?status=ACTIVE`
- **`GET /api/alerts`**
  - Fetches compliance alerts across critical, warning, and informational severity levels.
  - Optional Query Param: `?product_id=1&severity=CRITICAL`

### Analytics & AI Assistant
- **`GET /api/dashboard/stats`**
  - Returns aggregated executive KPIs: total products, active standards, active certifications, and open critical alerts.
- **`POST /api/chat`**
  - AI Assistant supporting semantic RAG retrieval over BIS standards and contextual product compliance queries.
  - Request body: `{"message": "What are the fire safety requirements under IS 13252?", "product_id": 1}`

### Background Jobs (Inngest)
- **`rag/ingest_pdf`**: Background job to extract, chunk, embed, and index compliance documentation into Qdrant.
- **`rag/query_pdf_ai`**: Multi-step AI search workflow with rate limiting and throttling.

---

## 🧪 Testing

Run the automated endpoint test suite:
```bash
python test_backend.py
```
All tests validate real HTTP responses against the expected schemas and status codes.
