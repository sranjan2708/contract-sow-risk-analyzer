"""
FROZEN DATA CONTRACTS — shared by every module.
Change ONLY through the contract-change process in AGENTS.md section 7.
Contract 1: ParsedDocument   doc_engine   -> backend / ai_engine
Contract 2: ClauseGraph      graph_engine -> backend / ai_engine
Contract 3: API responses    backend      -> frontend (see docs/api_contracts.md)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"


class DocumentType(str, Enum):
    MSA = "MSA"
    SOW = "SOW"
    OTHER = "OTHER"


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class RelationType(str, Enum):
    REFERENCES = "REFERENCES"
    OVERRIDES = "OVERRIDES"
    DEPENDS_ON = "DEPENDS_ON"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    PAYMENT = "PAYMENT"
    LIABILITY = "LIABILITY"
    INDEMNITY = "INDEMNITY"
    TERMINATION = "TERMINATION"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"
    WARRANTY = "WARRANTY"
    DATA_PROTECTION = "DATA_PROTECTION"
    SCOPE = "SCOPE"
    DELIVERY = "DELIVERY"
    GOVERNING_LAW = "GOVERNING_LAW"
    OTHER = "OTHER"


class EvidenceSource(str, Enum):
    CLAUSE = "CLAUSE"
    PLAYBOOK = "PLAYBOOK"
    GRAPH = "GRAPH"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False, protected_namespaces=())


# ---- Contract 1: clauses
class Clause(_Strict):
    clause_id: str
    title: Optional[str] = None
    text: str = Field(..., min_length=1)
    page_number: int = Field(..., ge=1)
    section: Optional[str] = None
    parent_clause_id: Optional[str] = None
    references: list[str] = Field(default_factory=list)


class ParsedDocument(_Strict):
    document_id: Optional[int] = None
    document_type: DocumentType
    file_name: str
    page_count: int = Field(..., ge=1)
    clauses: list[Clause]
    parser_version: str = "0.1.0"


# ---- Contract 2: graph
class GraphNode(_Strict):
    clause_id: str
    title: Optional[str] = None


class GraphEdge(_Strict):
    source: str
    target: str
    relation: RelationType


class InvalidReference(_Strict):
    clause_id: str
    missing_target: str


class ClauseGraph(_Strict):
    document_id: Optional[int] = None
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)
    has_cycle: bool = False
    cycles: list[list[str]] = Field(default_factory=list)
    invalid_references: list[InvalidReference] = Field(default_factory=list)


# ---- AI outputs
class Evidence(_Strict):
    source: EvidenceSource
    reference: str
    quote: Optional[str] = None
    page_number: Optional[int] = Field(None, ge=1)


class RiskFinding(_Strict):
    finding_id: Optional[int] = None
    clause_id: str
    risk_level: RiskLevel
    risk_category: RiskCategory
    explanation: str
    evidence: list[Evidence] = Field(default_factory=list)
    suggested_redline: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING


class AnalysisResult(_Strict):
    document_id: Optional[int] = None
    overall_risk_score: float = Field(..., ge=0, le=100)
    summary: str
    findings: list[RiskFinding]
    model_used: str


class Contradiction(_Strict):
    contradiction_id: Optional[int] = None
    msa_clause_id: str
    sow_clause_id: str
    risk_category: RiskCategory
    risk_level: RiskLevel
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    suggested_redline: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING


class ComparisonResult(_Strict):
    msa_document_id: Optional[int] = None
    sow_document_id: Optional[int] = None
    contradictions: list[Contradiction]
    model_used: str


# ---- Contract 3: API-only models
class UserRegister(_Strict):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str


class UserLogin(_Strict):
    email: str
    password: str


class TokenResponse(_Strict):
    access_token: str
    token_type: str = "bearer"


class UserOut(_Strict):
    user_id: int
    email: str
    full_name: str


class DocumentOut(_Strict):
    document_id: int
    file_name: str
    document_type: DocumentType
    status: DocumentStatus
    page_count: Optional[int] = None
    uploaded_at: datetime


class CompareRequest(_Strict):
    msa_document_id: int
    sow_document_id: int


class ReviewUpdate(_Strict):
    review_status: ReviewStatus
    comment: Optional[str] = None
    modified_redline: Optional[str] = None


class AuditEvent(_Strict):
    event_id: int
    document_id: int
    user_id: Optional[int] = None
    action: str
    details: Optional[str] = None
    created_at: datetime


class ErrorResponse(_Strict):
    detail: str
