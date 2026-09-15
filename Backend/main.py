import os
import sys
import uuid
import logging
import datetime
from typing import Any, Dict, List, Optional

# Ensure Backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

import inngest
import inngest.fast_api
from inngest.experimental import ai

from database import DatabaseManager
from vector_db import QdrantStorage
from data_loader import load_and_chunk_pdf, embed_texts
from custom_types import (
    RAGSearchResult,
    RAGUpsertResult,
    RAGChunkAndSrc,
    ChatRequest,
    ChatResponse,
    ComplianceStatusResponse,
    ProductDetailResponse,
    DashboardStatsResponse,
)

load_dotenv()

logger = logging.getLogger("uvicorn")

app = FastAPI(
    title="SIH 2026 PS 107 - BIS Compliance AI Assistant",
    description="AI-powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers.",
    version="1.0.0",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_env = os.getenv("FRONTEND_URL")
if frontend_env and frontend_env not in origins:
    origins.append(frontend_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for seamless local dev / network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize resources
db = DatabaseManager()
qdrant = QdrantStorage()

# --- Inngest Workflow Integration ---

inngest_client = inngest.Inngest(
    app_id="bis_compliance_app",
    logger=logger,
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(limit=2, period=datetime.timedelta(minutes=1)),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.source_id",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context) -> dict:
    pdf_path = ctx.event.data["pdf_path"]
    source_id = ctx.event.data.get("source_id", pdf_path)

    def _load() -> RAGChunkAndSrc:
        chunks = load_and_chunk_pdf(pdf_path)
        if not chunks:
            raise ValueError(f"No chunks extracted from PDF: {pdf_path}")
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        src = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{src}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": src, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run("load-and-chunk", _load, output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run(
        "embed-and-upsert",
        _upsert,
        chunks_and_src,
        output_type=RAGUpsertResult,
    )
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"),
)
async def rag_query_pdf_ai(ctx: inngest.Context) -> dict:
    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    def _search(q: str, k: int) -> RAGSearchResult:
        query_vec = embed_texts([q])[0]
        found = QdrantStorage().search(query_vec, k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    found = await ctx.step.run(
        "embed-and-search",
        _search,
        question,
        top_k,
        output_type=RAGSearchResult,
    )

    if not found.contexts:
        return {
            "answer": "I couldn't find anything relevant in the ingested documents to answer that.",
            "sources": [],
            "num_contexts": 0,
        }

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("sk-mock") and len(openai_key) > 20:
        adapter = ai.openai.Adapter(
            auth_key=openai_key,
            model="gpt-4o-mini",
        )
        res = await ctx.step.ai.infer(
            "llm-answer",
            adapter=adapter,
            body={
                "max_tokens": 1024,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "You answer questions using only the provided context."},
                    {"role": "user", "content": user_content},
                ],
            },
        )
        answer = res["choices"][0]["message"]["content"].strip()
    else:
        answer = f"Based on BIS documentation: {found.contexts[0]}"

    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])


# --- API Endpoints ---

@app.get("/api/health")
def get_health():
    """Health check for system services."""
    return {
        "status": "healthy",
        "database": "MySQL (live)" if db.use_mysql else "SQLite (embedded schema compliant)",
        "vector_storage": "Qdrant (ready)",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY") and len(os.getenv("OPENAI_API_KEY")) > 20),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/products")
def list_products():
    """Return all products with category and manufacturer information."""
    try:
        products = db.get_all_products()
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@app.get("/api/products/{product_id}", response_model=ProductDetailResponse)
def get_product_details(product_id: int):
    """Return complete product details, category, standards, requirements, status, and alerts."""
    passport = db.get_product_passport(product_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    standards = db.get_product_standards(product_id)
    requirements = db.get_all_requirements_for_product(product_id)
    alerts = db.get_alerts(product_id=product_id)

    status_counts = {"COMPLETED": 0, "IN_PROGRESS": 0, "NOT_STARTED": 0, "FAILED": 0}
    for req in requirements:
        st = req.get("status", "NOT_STARTED")
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "product": passport,
        "category": passport.get("category_name"),
        "standards": standards,
        "requirements": requirements,
        "current_requirement_status": status_counts,
        "alerts": alerts,
    }


@app.get("/api/products/{product_id}/compliance", response_model=ComplianceStatusResponse)
def get_compliance_status(product_id: int):
    """Return compliance metrics, readiness percentage, applicable standards, gaps, and actions."""
    passport = db.get_product_passport(product_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    readiness = db.get_compliance_readiness(product_id)
    standards = db.get_product_standards(product_id)
    gaps = db.get_compliance_gaps(product_id)
    actions = db.get_recommended_actions(product_id)

    return {
        "product_id": product_id,
        "product_name": passport.get("product_name", "Unknown Product"),
        "total_requirements": readiness.get("total_requirements", 0),
        "completed": readiness.get("completed_requirements", 0),
        "pending": readiness.get("pending_requirements", 0),
        "failed": readiness.get("failed_requirements", 0),
        "readiness_percentage": readiness.get("readiness_percentage", 0.0),
        "applicable_standards": standards,
        "compliance_gaps": gaps,
        "recommended_actions": actions,
    }


@app.get("/api/alerts")
def get_alerts(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    status: Optional[str] = Query("OPEN", description="Filter by status (OPEN, RESOLVED, All)"),
):
    """Return compliance alerts from MySQL."""
    try:
        return db.get_alerts(product_id=product_id, severity=severity, status=status)
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch compliance alerts")


@app.get("/api/standards")
def get_standards(
    q: Optional[str] = Query("", description="Search term for standard number or title"),
    category: Optional[str] = Query(None, description="Category code filter"),
    scheme: Optional[str] = Query(None, description="Scheme filter"),
    status: Optional[str] = Query(None, description="Status filter"),
):
    """Search and filter standards using Queries 9, 10, 11."""
    try:
        return db.search_standards(query=q or "", category_code=category, scheme=scheme, status=status)
    except Exception as e:
        logger.error(f"Error searching standards: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch standards")


@app.get("/api/standards/{standard_id}")
def get_standard_detail(standard_id: int):
    """Get single standard details (Query 12)."""
    std = db.get_standard_details(standard_id)
    if not std:
        raise HTTPException(status_code=404, detail="Standard not found")
    return std


@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats():
    """Return dashboard statistics (Query 15) and recent compliance activity."""
    try:
        return db.get_dashboard_statistics()
    except Exception as e:
        logger.error(f"Error fetching dashboard statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(req: ChatRequest):
    """
    AI Assistant Endpoint:
    Combines:
    1. Structured MySQL data for the product (or detected product).
    2. Unstructured RAG context from Qdrant vector database.
    3. Natural language response generated by OpenAI (gpt-4o-mini).
    """
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    product_id = req.product_id

    # Auto-detect product_id from query text if not explicitly provided
    if not product_id:
        q_lower = question.lower()
        if "tv" in q_lower or "television" in q_lower or "display" in q_lower:
            product_id = 1
        elif "kettle" in q_lower or "appliance" in q_lower or "mixer" in q_lower:
            product_id = 2

    # 1. Fetch structured MySQL context
    product_passport = None
    applicable_standards = []
    requirements = []
    alerts = []

    if product_id:
        product_passport = db.get_product_passport(product_id)
        applicable_standards = db.get_product_standards(product_id)
        requirements = db.get_all_requirements_for_product(product_id)
        alerts = db.get_alerts(product_id=product_id)

    # 2. Fetch Qdrant RAG vector context
    query_vec = embed_texts([question])[0]
    search_res = qdrant.search(query_vec, k=4)
    rag_contexts = search_res.get("contexts", [])
    sources = search_res.get("sources", [])

    # Include structured standards as sources if present
    for s in applicable_standards:
        s_num = s.get("standard_number")
        if s_num and s_num not in sources:
            sources.append(s_num)

    # 3. Formulate grounded prompt for OpenAI
    structured_block = ""
    if product_passport:
        std_str = ", ".join([f"{s.get('standard_number')} ({s.get('standard_title')})" for s in applicable_standards])
        req_str = "\n".join([f"- {r.get('requirement_code')}: {r.get('requirement_title')} [Status: {r.get('status')}]" for r in requirements])
        alert_str = "\n".join([f"- [{a.get('severity')}] {a.get('title')}: {a.get('message')}" for a in alerts])

        structured_block = (
            f"\n--- PRODUCT CONTEXT (FROM BIS DATABASE) ---\n"
            f"Product: {product_passport.get('product_name')} (Model: {product_passport.get('model_number')})\n"
            f"Category: {product_passport.get('category_name')}\n"
            f"Manufacturer: {product_passport.get('manufacturer_name')}\n"
            f"Applicable Standards: {std_str}\n"
            f"Compliance Requirements:\n{req_str}\n"
            f"Open Alerts:\n{alert_str if alert_str else 'None'}\n"
        )

    rag_block = "\n".join([f"- {c}" for c in rag_contexts])

    system_prompt = (
        "You are the official Bureau of Indian Standards (BIS) AI Compliance Assistant. "
        "Your role is to guide manufacturers, consumers, and compliance officers regarding Indian Standards, "
        "certification schemes (ISI Mark Scheme I, CRS, Hallmarking), laboratory testing, and documentation requirements. "
        "\nIMPORTANT SAFETY RULES:\n"
        "1. Answer strictly based on the provided BIS database context and standard documents.\n"
        "2. Do NOT hallucinate standard numbers or regulatory requirements not present in the reference data.\n"
        "3. Always format your answer clearly with applicable standard codes, certification route, key requirements, and next action items."
    )

    user_prompt = (
        f"User Question: {question}\n\n"
        f"{structured_block}\n"
        f"--- OFFICIAL BIS REFERENCE KNOWLEDGE ---\n"
        f"{rag_block}\n\n"
        "Provide a concise, professional, source-grounded response."
    )

    # 4. Generate answer using OpenAI or Grounded Deterministic Fallback
    openai_key = os.getenv("OPENAI_API_KEY")
    answer = None

    if openai_key and not openai_key.startswith("sk-mock") and len(openai_key) > 20:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            answer = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI completion error ({e}). Using grounded rule-based generator.")

    if not answer:
        # Grounded rule-based response using exact database & RAG data
        if product_passport and applicable_standards:
            p_name = product_passport.get("product_name")
            std_codes = " and ".join([s.get("standard_number") for s in applicable_standards])
            req_bullets = "\n".join([f"• {r.get('requirement_title')} ({r.get('status')})" for r in requirements[:3]])
            answer = (
                f"For your **{p_name}**, the applicable Indian Standards are **{std_codes}**.\n\n"
                f"**Applicable Scheme:** {'Compulsory Registration Scheme (CRS)' if 'TV' in p_name else 'ISI Marking Scheme (Scheme I)'}\n\n"
                f"**Key Requirements:**\n{req_bullets}\n\n"
                f"**Recommended Next Steps:**\n"
                f"1. Verify laboratory test reports against {applicable_standards[0].get('standard_number')}.\n"
                f"2. Ensure complete rating and standard mark artwork is prepared.\n"
                f"3. Submit application dossier on the BIS portal."
            )
        elif rag_contexts:
            answer = (
                f"Based on official BIS documentation:\n\n{rag_contexts[0]}\n\n"
                f"Refer to {sources[0] if sources else 'BIS Portal'} for detailed submission procedures."
            )
        else:
            answer = (
                "Please specify your product or query (such as Smart TV, Electric Kettle, or IS standard code) "
                "so I can provide the applicable BIS standards, testing requirements, and certification steps."
            )

    return {
        "answer": answer,
        "sources": sources,
        "product": product_passport,
        "requirements": requirements,
        "alerts": alerts,
    }
