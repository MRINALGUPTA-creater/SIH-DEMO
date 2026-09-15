# SIH 2026 - Problem Statement 107: BIS Compliance AI Assistant Backend

**AI-powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers**

A production-ready AI backend built with **FastAPI**, **Inngest**, **Qdrant Vector Database**, and **MySQL (with automated embedded SQLite fallback)**.

---

## 🏛 Architecture Overview

`
                          ┌──────────────────────────┐
                          │   Next.js 16 Frontend    │
                          │   (Port 3000 / Turbopack)│
                          └─────────────┬────────────┘
                                        │ HTTP / JSON
                                        ▼
                          ┌──────────────────────────┐
                          │     FastAPI Backend      │
                          │   (Port 8000 / Uvicorn)  │
                          └───────┬───────┬──────┬───┘
                                  │       │      │
         ┌────────────────────────┘       │      └────────────────────────┐
         ▼                                ▼                               ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│ Relational DB    │            │ Qdrant Vector DB │            │ Inngest Event    │
│ (12+1 Tables)    │            │ (RAG Knowledge)  │            │ Orchestrator     │
│ • MySQL Server   │            │ • Persistent disk│            │ • Ingestion      │
│ • SQLite Fallback│            │ • Cosine search  │            │ • Background RAG │
└──────────────────┘            └──────────────────┘            └──────────────────┘
`

---

## 📂 Backend Project Structure

`
Backend/
├── main.py                 # FastAPI application, Inngest functions, CORS & dual routes
├── database.py             # Database manager: 12 tables, 15 queries, dual MySQL/SQLite driver
├── vector_db.py            # Qdrant client wrapper with concurrent process locking protection
├── data_loader.py          # PDF document text chunking & OpenAI/deterministic vector embeddings
├── custom_types.py         # Pydantic schemas (Product, Compliance, Complaints, Licences, Chat)
├── requirements.txt        # Production dependencies
├── .env.example            # Environment variables template
├── init_db.py              # Script to bootstrap MySQL database from bis_compliance.sql
├── seed_data.py            # Script to seed Qdrant with Indian Standards knowledge corpus
├── bis_compliance.sql      # Official DDL and seed dataset (12 relational tables)
├── test_backend.py         # Test suite verifying 17 endpoints & operations (All PASS)
└── README.md               # Complete documentation
`

---

## 🚀 Quick Start Guide

### 1. Setup Virtual Environment
`ash
cd Backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
`

### 2. Configure Environment Variables
Copy .env.example to .env:
`ash
cp .env.example .env
`

### 3. Initialize Database & Vector Store
`ash
python init_db.py
python seed_data.py
`

### 4. Run the FastAPI Server
`ash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
`
- Interactive Swagger UI: http://localhost:8000/docs
- ReDoc Documentation: http://localhost:8000/redoc

---

## 📡 Complete API Endpoints

### 🩺 Health & Diagnostic
- GET /api/health: Reports API operational status, active DB backend (MySQL or SQLite fallback), Qdrant status.

### 📦 Product Compliance Passport
- GET /api/products: List all registered products with metadata.
- POST /api/products: Dynamically register a new product profile.
- GET /api/products/{product_id}: Detailed product profile, standards, documents, lab tests, and certifications.
- GET /api/products/{product_id}/compliance: Live readiness score (%), completed vs pending requirements, compliance gaps, and recommended actions.
- GET /api/products/{product_id}/requirements: All requirements for a product.
- GET /api/products/{product_id}/alerts: Product-specific compliance alerts.

### 📜 Indian Standards & Discovery
- GET /api/standards: List and filter Indian Standards by category, scheme, or status.
- GET /api/standards/search: Keyword and category search for Indian Standards.
- GET /api/standards/{standard_id}: Comprehensive details for a specific Indian Standard.

### 🚨 Compliance Alerts Center
- GET /api/alerts: Retrieve active compliance alerts with severity and status filters.
- POST /api/alerts/{alert_id}/resolve: 1-Click resolution of compliance alerts with immediate database update.

### 🤖 AI Assistant & Semantic RAG
- POST /api/chat: Hybrid AI assistant combining structured database context + Qdrant semantic vector search + LLM generation. Supports **Adaptive Clarifying Questions** and **Suggested Prompts**.
- POST /rag/ingest: Ingest PDF or standard text documents into Qdrant for RAG.

### 👥 Consumer Services & Protection Hub
- GET /api/consumer/verify-licence?licence_number={number}: Instant validation of ISI Mark (CM/L-XXXXXXX) and CRS numbers.
- POST /api/consumer/complaint: Citizen grievance portal for reporting counterfeit ISI marks or substandard quality goods.

### 📊 Executive Analytics
- GET /api/dashboard/stats: High-level KPIs and live activity feed.

---

## 🧪 Automated Testing

Run the full automated test suite:
`ash
python test_backend.py
`
All 17 tests pass successfully with exit code 0.
