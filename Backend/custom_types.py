from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Inngest / RAG Types ---

class RAGChunkAndSrc(BaseModel):
    chunks: List[str]
    source_id: str


class RAGUpsertResult(BaseModel):
    ingested: int


class RAGSearchResult(BaseModel):
    contexts: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


# --- API Request / Response Types ---

class ChatRequest(BaseModel):
    message: str
    product_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    product: Optional[Dict[str, Any]] = None
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    suggested_prompts: List[str] = Field(default_factory=list)


class ComplianceStatusResponse(BaseModel):
    product_id: int
    product_name: str
    total_requirements: int
    completed: int
    pending: int
    failed: int
    readiness_percentage: float
    applicable_standards: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)


class ProductDetailResponse(BaseModel):
    product: Dict[str, Any]
    category: Optional[str] = None
    standards: List[Dict[str, Any]] = Field(default_factory=list)
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    current_requirement_status: Dict[str, int] = Field(default_factory=dict)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    tests: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_readiness: Optional[Dict[str, Any]] = None
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardStatsResponse(BaseModel):
    total_products: int
    active_standards: int
    active_certifications: int
    critical_alerts: int
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class CreateProductRequest(BaseModel):
    product_name: str
    model_number: str
    category_code: str = "ELEC"
    manufacturer_name: str = "Enterprise Manufacturer Pvt Ltd"
    country_of_origin: str = "India"
    description: Optional[str] = None


class RAGIngestRequest(BaseModel):
    text: Optional[str] = None
    content: Optional[str] = None
    source_id: Optional[str] = None
    document_id: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    pdf_path: Optional[str] = None


class ComplaintRequest(BaseModel):
    consumer_name: str
    consumer_email: str
    consumer_phone: Optional[str] = None
    product_name: str
    brand_or_model: Optional[str] = None
    licence_number: Optional[str] = None
    complaint_type: str = "SUBSTANDARD_PRODUCT"
    description: str

