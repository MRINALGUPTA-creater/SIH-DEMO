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
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardStatsResponse(BaseModel):
    total_products: int
    active_standards: int
    active_certifications: int
    critical_alerts: int
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
