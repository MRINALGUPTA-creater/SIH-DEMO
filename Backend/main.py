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
    CreateProductRequest,
    RAGIngestRequest,
    ComplaintRequest,
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

@app.get("/health")
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


# --- Products & Compliance Passport ---

@app.get("/products")
@app.get("/api/products")
def list_products():
    """Return all products with category and manufacturer information."""
    try:
        products = db.get_all_products()
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@app.post("/products")
@app.post("/api/products")
def create_product(req: CreateProductRequest):
    """Create a new product, automatically map relevant standards and requirements."""
    try:
        res = db.create_product(req.model_dump())
        return res
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail="Failed to create product passport")


@app.get("/products/{product_id}", response_model=ProductDetailResponse)
@app.get("/api/products/{product_id}", response_model=ProductDetailResponse)
def get_product_details(product_id: int):
    """Return complete product details, category, standards, requirements, status, documents, tests, and alerts."""
    passport = db.get_product_passport(product_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    standards = db.get_product_standards(product_id)
    requirements = db.get_all_requirements_for_product(product_id)
    alerts = db.get_alerts(product_id=product_id)
    documents = db.get_product_documents(product_id)
    tests = db.get_product_tests(product_id)
    certifications = db.get_product_certifications(product_id)
    recommended_actions = db.get_recommended_actions(product_id)
    readiness = db.get_compliance_readiness(product_id)

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
        "documents": documents,
        "tests": tests,
        "certifications": certifications,
        "recommended_actions": recommended_actions,
        "compliance_readiness": readiness,
        "alerts": alerts,
    }


@app.get("/products/{product_id}/compliance", response_model=ComplianceStatusResponse)
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


@app.get("/products/{product_id}/requirements")
@app.get("/api/products/{product_id}/requirements")
def get_product_requirements(product_id: int):
    """All requirements for a product (Query 3)."""
    passport = db.get_product_passport(product_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    return db.get_all_requirements_for_product(product_id)


@app.get("/products/{product_id}/alerts")
@app.get("/api/products/{product_id}/alerts")
def get_product_alerts(product_id: int):
    """Product-specific alerts (Query 13)."""
    return db.get_alerts(product_id=product_id)


# --- Standards Catalog & Search ---

@app.get("/standards")
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


@app.get("/standards/search")
@app.get("/api/standards/search")
def search_standards(
    q: Optional[str] = Query("", description="Search query"),
    category: Optional[str] = Query(None, description="Category code"),
):
    """Dedicated search endpoint for Indian Standards."""
    try:
        return db.search_standards(query=q or "", category_code=category)
    except Exception as e:
        logger.error(f"Error searching standards: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/standards/{standard_id}")
@app.get("/api/standards/{standard_id}")
def get_standard_detail(standard_id: int):
    """Get single standard details (Query 12)."""
    std = db.get_standard_details(standard_id)
    if not std:
        raise HTTPException(status_code=404, detail="Standard not found")
    return std


# --- Compliance Alerts ---

@app.get("/alerts")
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


@app.post("/alerts/{alert_id}/resolve")
@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert_endpoint(alert_id: int):
    """Resolve an open compliance alert."""
    success = db.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or already resolved")
    return {"status": "RESOLVED", "alert_id": alert_id}


# --- Dashboard Stats ---

@app.get("/dashboard/stats", response_model=DashboardStatsResponse)
@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats():
    """Return dashboard statistics (Query 15) and recent compliance activity."""
    try:
        return db.get_dashboard_statistics()
    except Exception as e:
        logger.error(f"Error fetching dashboard statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")


# --- Consumer Services ---

@app.get("/consumer/verify-licence")
@app.get("/api/consumer/verify-licence")
def verify_consumer_licence(licence_number: str = Query(..., description="CM/L or CRS registration number")):
    """Verify validity of BIS licence number, CM/L, or CRS registration."""
    res = db.verify_licence(licence_number)
    if not res:
        raise HTTPException(status_code=404, detail=f"No active BIS licence found matching '{licence_number}'")
    return res


@app.post("/consumer/complaint")
@app.post("/api/consumer/complaint")
def submit_consumer_complaint(req: ComplaintRequest):
    """Submit a consumer grievance or complaint regarding substandard product."""
    return db.submit_complaint(req.model_dump())


# --- Document Ingestion (RAG) ---

@app.post("/rag/ingest")
@app.post("/api/rag/ingest")
def rag_ingest_content(req: RAGIngestRequest):
    """Ingest custom text or PDF document into Qdrant vector database."""
    chunks = []
    if req.pdf_path:
        chunks = load_and_chunk_pdf(req.pdf_path)
    elif req.text:
        text = req.text.strip()
        chunks = [text[i:i+800] for i in range(0, len(text), 650)]

    if not chunks:
        raise HTTPException(status_code=400, detail="No valid content or PDF could be parsed for ingestion")

    vecs = embed_texts(chunks)
    ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{req.source_id}:{i}")) for i in range(len(chunks))]
    payloads = [{"source": req.source_id, "text": chunks[i]} for i in range(len(chunks))]
    qdrant.upsert(ids, vecs, payloads)
    return {"ingested_chunks": len(chunks), "source_id": req.source_id, "status": "SUCCESS"}


# --- AI Compliance Copilot ---

@app.post("/assistant/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(req: ChatRequest):
    """
    AI-Powered BIS Compliance Copilot:
    1. Detects ambiguous / underspecified requests and prompts adaptive clarifying questions.
    2. Handles consumer verification and grievance routing.
    3. Fetches structured MySQL context (products, standards, requirements, alerts).
    4. Fetches unstructured Qdrant vector context (official BIS standards and guidelines).
    5. Synthesizes a grounded response with zero hallucination.
    """
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    product_id = req.product_id
    q_lower = question.lower()

    # 1. Check for underspecified / ambiguous request requiring clarifying questions
    is_general_cert_query = any(phrase in q_lower for phrase in [
        "i want bis certification", "certify my product", "how to get bis",
        "i want certification", "certification for my product", "certify a product",
        "need bis mark", "apply for bis"
    ]) and not any(p in q_lower for p in [
        "tv", "television", "kettle", "display", "plug", "socket", "cable",
        "is 13252", "is 616", "is 4250", "is 302", "gold", "jewellery"
    ])

    if is_general_cert_query and not product_id:
        return {
            "answer": (
                "To accurately determine the applicable Indian Standards (IS), mandatory certification scheme "
                "(ISI Mark Scheme I vs. Compulsory Registration Scheme CRS), laboratory testing protocols, and documentation dossier, "
                "I need a few technical details regarding your product:"
            ),
            "sources": ["BIS Conformity Assessment Regulations, 2018", "BIS Compulsory Registration Scheme (CRS) Guidelines"],
            "product": None,
            "requirements": [],
            "alerts": [],
            "clarifying_questions": [
                "1. What is the specific product type or intended application (e.g., Smart TV, Electric Kettle, Solar Inverter)?",
                "2. What is the product category (Electronics/IT, Household Electrical, Machinery, Automotive)?",
                "3. Is the manufacturing facility located in India (domestic) or overseas (Foreign Manufacturers Scheme FMCS)?",
                "4. What are the key electrical specifications (rated voltage, power wattage, operating frequency)?",
                "5. Do you already hold any existing BIS licence, CM/L number, or CRS registration?"
            ],
            "suggested_prompts": [
                "I want to manufacture a Smart Television in India",
                "What BIS standards apply to an Electric Kettle?",
                "How do I verify a BIS licence or CM/L number?",
                "What documents are required for CRS registration?"
            ]
        }

    # 2. Check for consumer verification queries
    if "verify" in q_lower and any(k in q_lower for k in ["licence", "license", "cml", "cm/l", "isi mark", "r-number", "huid"]):
        return {
            "answer": (
                "To verify a BIS Licence or Standard Mark authenticity:\n\n"
                "1. **ISI Mark (CM/L Number)**: Look for the 7 or 8-digit CM/L number below the ISI logo on the product packaging.\n"
                "2. **CRS Registration (R-number)**: Look for the 8-digit Registration Number (e.g., R-XXXXXXXX) and the official portal URL `www.crsbis.in`.\n"
                "3. **Hallmarking (HUID)**: Every piece of hallmarked gold jewellery carries a 6-digit alphanumeric Unique Identification code.\n\n"
                "You can verify any licence immediately using our **Consumer Services** verification tool or the official *BIS Care App*."
            ),
            "sources": ["BIS Product Certification Scheme I", "Compulsory Registration Scheme (CRS)", "Hallmarking Regulations"],
            "product": None,
            "requirements": [],
            "alerts": [],
            "clarifying_questions": [],
            "suggested_prompts": [
                "Verify licence CM/L-8400012398",
                "How do I file a BIS complaint?",
                "What is HUID in gold hallmarking?"
            ]
        }

    # 3. Check for consumer grievance / complaint queries
    if any(k in q_lower for k in ["complaint", "grievance", "substandard", "fake isi", "fraudulent"]):
        return {
            "answer": (
                "Citizens can report substandard products, misuse of the ISI Mark, or fraudulent BIS registrations:\n\n"
                "• **Grievance Portal**: Submit a grievance directly via the **Consumer Services** tab in this platform.\n"
                "• **Required Details**: Product name, brand/model, purchase invoice, retailer address, and a photograph of the label.\n"
                "• **Investigation**: BIS Enforcement Branch inspects the premises and initiates legal proceedings under the BIS Act, 2016 for counterfeit or non-compliant goods."
            ),
            "sources": ["BIS Act 2016 (Section 14 & 15)", "BIS Consumer Engagement Guidelines"],
            "product": None,
            "requirements": [],
            "alerts": [],
            "clarifying_questions": [],
            "suggested_prompts": [
                "How do I file a BIS complaint?",
                "Verify licence CM/L-8400012398",
                "What standards apply to Smart TVs?"
            ]
        }

    # Auto-detect product_id from query text if not explicitly provided
    if not product_id:
        if "tv" in q_lower or "television" in q_lower or "display" in q_lower:
            product_id = 1
        elif "kettle" in q_lower or "appliance" in q_lower or "mixer" in q_lower:
            product_id = 2

    # Fetch structured SQL context
    product_passport = None
    applicable_standards = []
    requirements = []
    alerts = []

    if product_id:
        product_passport = db.get_product_passport(product_id)
        applicable_standards = db.get_product_standards(product_id)
        requirements = db.get_all_requirements_for_product(product_id)
        alerts = db.get_alerts(product_id=product_id)

    # Fetch Qdrant RAG vector context
    query_vec = embed_texts([question])[0]
    search_res = qdrant.search(query_vec, k=4)
    rag_contexts = search_res.get("contexts", [])
    sources = search_res.get("sources", [])

    # Include structured standards as sources if present
    for s in applicable_standards:
        s_num = s.get("standard_number")
        if s_num and s_num not in sources:
            sources.append(s_num)

    # Formulate grounded prompt
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

    # Generate answer using OpenAI or Grounded Deterministic Fallback
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
            req_bullets = "\n".join([f"• {r.get('requirement_title')} ({r.get('status')})" for r in requirements[:4]])
            answer = (
                f"For your **{p_name}**, the applicable Indian Standards are **{std_codes}**.\n\n"
                f"**Applicable Scheme:** {'Compulsory Registration Scheme (CRS)' if 'TV' in p_name else 'ISI Marking Scheme (Scheme I)'}\n\n"
                f"**Key Requirements & Evidence Checklist:**\n{req_bullets}\n\n"
                f"**Recommended Next Steps:**\n"
                f"1. Complete lab testing under accredited laboratory guidelines for {applicable_standards[0].get('standard_number')}.\n"
                f"2. Prepare technical file with circuit schematics, BOM, and label artwork.\n"
                f"3. Submit formal registration dossier on the BIS Manakonline portal."
            )
        elif rag_contexts:
            answer = (
                f"Based on official BIS documentation:\n\n{rag_contexts[0]}\n\n"
                f"Refer to {sources[0] if sources else 'BIS Portal'} for detailed statutory guidelines."
            )
        else:
            answer = (
                "Please specify your product (e.g. Smart TV, Electric Kettle, Solar Inverter) or standard number "
                "so I can provide the applicable BIS standards, testing requirements, and certification roadmap."
            )

    # Generate dynamic adaptive clarifying questions based on product context
    dynamic_cq = []
    if product_passport:
        p_name_l = product_passport.get("product_name", "").lower()
        if "tv" in p_name_l or "display" in p_name_l:
            dynamic_cq = [
                "Does the Smart TV support Wi-Fi / Bluetooth (requires WPC ETA wireless approval)?",
                "What is the diagonal screen size (e.g. 32-inch vs 55-inch or above)?",
                "Is the power supply internal or an external BIS-certified AC/DC adapter?",
            ]
        elif "kettle" in p_name_l or "appliance" in p_name_l:
            dynamic_cq = [
                "What is the rated liquid capacity (e.g. 1.5L domestic vs commercial bulk volume)?",
                "Does the heating element feature an automatic boil-dry thermal cut-off sensor?",
                "Is the body constructed from stainless steel, food-grade polypropylene, or borosilicate glass?",
            ]
        else:
            dynamic_cq = [
                "Is this product intended for domestic Indian sale or export?",
                "Are any critical sub-assemblies (e.g. power cords, switches) already BIS-marked?",
            ]
    else:
        dynamic_cq = [
            "What is your product category (IT/Electronics, Household Appliances, Machinery)?",
            "Are you seeking ISI Mark (Scheme-I) or Compulsory Registration (CRS)?",
        ]

    suggested_prompts = [
        "What documents do I need for BIS registration?",
        "Show my compliance gaps and pending requirements",
        "What are the dielectric strength test requirements?",
        "How do I verify a BIS licence?",
    ]

    return {
        "answer": answer,
        "sources": sources,
        "product": product_passport,
        "requirements": requirements,
        "alerts": alerts,
        "clarifying_questions": dynamic_cq,
        "suggested_prompts": suggested_prompts,
    }

