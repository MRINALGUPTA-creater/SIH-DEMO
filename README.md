# SIH 2026 - Problem Statement 107
## AI-Powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers

This repository contains the backend implementation for SIH 2026 Problem Statement 107.

### 📁 Repository Structure

- [`Backend/`](./Backend): Complete FastAPI backend application, Qdrant Vector DB, Inngest workflows, and MySQL/SQLite database manager.
  - [`main.py`](./Backend/main.py): FastAPI API routes, Inngest functions, CORS configuration
  - [`database.py`](./Backend/database.py): Relational database manager (12 tables, 15 queries)
  - [`vector_db.py`](./Backend/vector_db.py): Qdrant vector database client
  - [`data_loader.py`](./Backend/data_loader.py): Document chunking & embeddings
  - [`custom_types.py`](./Backend/custom_types.py): Pydantic request & response schemas
  - [`requirements.txt`](./Backend/requirements.txt): Python dependencies
  - [`.env.example`](./Backend/.env.example): Environment variable template
  - [`init_db.py`](./Backend/init_db.py): MySQL database initialization script
  - [`seed_data.py`](./Backend/seed_data.py): Qdrant vector knowledge base seeder
  - [`test_backend.py`](./Backend/test_backend.py): Automated test suite for all endpoints
  - [`bis_compliance.sql`](./Backend/bis_compliance.sql): Complete SQL schema and seed data
  - [`README.md`](./Backend/README.md): Detailed backend documentation & instructions

### 🚀 Getting Started

To run the backend:

```bash
cd Backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Initialize database and seed vector store
python init_db.py
python seed_data.py

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

For full details, please refer to the [Backend Documentation](./Backend/README.md).
