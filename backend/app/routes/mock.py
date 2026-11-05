"""
Mock API routes implementing Contract 3 endpoints with sample data.
Activated when MOCK_MODE=True.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.app.config import get_settings
from shared.contracts import (
    CONTRACT_VERSION,
    AnalysisResult,
    AuditEvent,
    ClauseGraph,
    CompareRequest,
    ComparisonResult,
    Contradiction,
    DocumentOut,
    DocumentStatus,
    DocumentType,
    GraphNode,
    ParsedDocument,
    ReviewUpdate,
    RiskFinding,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from shared.samples import (
    sample_analysis,
    sample_comparison,
    sample_graph,
    sample_msa,
    sample_sow,
)

router = APIRouter(prefix="/api/v1", tags=["Mock"])

# Cached in-memory references for mock documents
_DOCS = {
    1: DocumentOut(
        document_id=1,
        file_name="sample_msa.pdf",
        document_type=DocumentType.MSA,
        status=DocumentStatus.ANALYZED,
        page_count=12,
        uploaded_at=datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc),
    ),
    2: DocumentOut(
        document_id=2,
        file_name="sample_sow.pdf",
        document_type=DocumentType.SOW,
        status=DocumentStatus.ANALYZED,
        page_count=5,
        uploaded_at=datetime(2026, 11, 1, 10, 5, 0, tzinfo=timezone.utc),
    ),
}


# 1. Health
@router.get("/health", tags=["Health"])
def health_endpoint() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_MODE,
        "contract_version": CONTRACT_VERSION,
    }


# 2. Register
@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister) -> UserOut:
    return UserOut(
        user_id=1,
        email=payload.email,
        full_name=payload.full_name,
    )


# 3. Login
@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin) -> TokenResponse:
    return TokenResponse(
        access_token="mock-access-token-12345",
        token_type="bearer",
    )


# 4. Current user
@router.get("/auth/me", response_model=UserOut)
def get_me() -> UserOut:
    return UserOut(
        user_id=1,
        email="analyst@example.com",
        full_name="Legal Analyst",
    )


# 5. Upload document
@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
) -> DocumentOut:
    doc_id = 1 if document_type == DocumentType.MSA else 2
    return DocumentOut(
        document_id=doc_id,
        file_name=file.filename or "uploaded_contract.pdf",
        document_type=document_type,
        status=DocumentStatus.PARSED,
        page_count=12 if document_type == DocumentType.MSA else 5,
        uploaded_at=datetime.now(timezone.utc),
    )


# 6. List documents
@router.get("/documents", response_model=list[DocumentOut])
def list_documents() -> list[DocumentOut]:
    return list(_DOCS.values())


# 7. Get document by ID
@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int) -> DocumentOut:
    if document_id not in _DOCS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return _DOCS[document_id]


# 8. Get document clauses
@router.get("/documents/{document_id}/clauses", response_model=ParsedDocument)
def get_document_clauses(document_id: int) -> ParsedDocument:
    if document_id == 1:
        return sample_msa()
    if document_id == 2:
        return sample_sow()
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {document_id} not found",
    )


# 9. Get clause graph
@router.get("/documents/{document_id}/graph", response_model=ClauseGraph)
def get_document_graph(document_id: int) -> ClauseGraph:
    if document_id == 1:
        return sample_graph()
    if document_id == 2:
        return ClauseGraph(
            document_id=2,
            nodes=[
                GraphNode(clause_id="2.1", title="Deliverables"),
                GraphNode(clause_id="4.1", title="Fees and Payment"),
            ],
            edges=[],
            has_cycle=False,
            cycles=[],
            invalid_references=[],
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {document_id} not found",
    )


# 10. Analyze document (trigger)
@router.post("/documents/{document_id}/analyze", response_model=AnalysisResult)
def trigger_analysis(document_id: int) -> AnalysisResult:
    if document_id == 1:
        return sample_analysis()
    if document_id == 2:
        return AnalysisResult(
            document_id=2,
            overall_risk_score=15.0,
            summary="SOW analyzed. Low risk detected.",
            findings=[],
            model_used="stub",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {document_id} not found",
    )


# 11. Get analysis result
@router.get("/documents/{document_id}/analysis", response_model=AnalysisResult)
def get_analysis(document_id: int) -> AnalysisResult:
    if document_id == 1:
        return sample_analysis()
    if document_id == 2:
        return AnalysisResult(
            document_id=2,
            overall_risk_score=15.0,
            summary="SOW analyzed. Low risk detected.",
            findings=[],
            model_used="stub",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {document_id} not found",
    )


# 12. Compare MSA vs SOW
@router.post("/compare", response_model=ComparisonResult)
def compare_documents(payload: CompareRequest) -> ComparisonResult:
    if payload.msa_document_id not in _DOCS or payload.sow_document_id not in _DOCS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more specified documents not found",
        )
    if payload.msa_document_id == 1 and payload.sow_document_id == 2:
        return sample_comparison()
    return ComparisonResult(
        msa_document_id=payload.msa_document_id,
        sow_document_id=payload.sow_document_id,
        contradictions=[],
        model_used="stub",
    )


# 13. Review finding
@router.patch("/findings/{finding_id}/review", response_model=RiskFinding)
def review_finding(finding_id: int, payload: ReviewUpdate) -> RiskFinding:
    analysis = sample_analysis()
    matching = [f for f in analysis.findings if f.finding_id == finding_id]
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk finding {finding_id} not found",
        )
    original = matching[0]
    redline = (
        payload.modified_redline
        if payload.modified_redline is not None
        else original.suggested_redline
    )
    return RiskFinding(
        finding_id=original.finding_id,
        clause_id=original.clause_id,
        risk_level=original.risk_level,
        risk_category=original.risk_category,
        explanation=original.explanation,
        evidence=original.evidence,
        suggested_redline=redline,
        review_status=payload.review_status,
    )


# 14. Review contradiction
@router.patch("/contradictions/{contradiction_id}/review", response_model=Contradiction)
def review_contradiction(
    contradiction_id: int,
    payload: ReviewUpdate,
) -> Contradiction:
    comparison = sample_comparison()
    matching = [
        c for c in comparison.contradictions if c.contradiction_id == contradiction_id
    ]
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contradiction {contradiction_id} not found",
        )
    original = matching[0]
    redline = (
        payload.modified_redline
        if payload.modified_redline is not None
        else original.suggested_redline
    )
    return Contradiction(
        contradiction_id=original.contradiction_id,
        msa_clause_id=original.msa_clause_id,
        sow_clause_id=original.sow_clause_id,
        risk_category=original.risk_category,
        risk_level=original.risk_level,
        description=original.description,
        evidence=original.evidence,
        suggested_redline=redline,
        review_status=payload.review_status,
    )


# 15. Audit trail
@router.get("/documents/{document_id}/audit", response_model=list[AuditEvent])
def get_document_audit(document_id: int) -> list[AuditEvent]:
    if document_id not in _DOCS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    return [
        AuditEvent(
            event_id=1,
            document_id=document_id,
            user_id=1,
            action="UPLOADED",
            details="Document uploaded successfully",
            created_at=base_time,
        ),
        AuditEvent(
            event_id=2,
            document_id=document_id,
            user_id=1,
            action="PARSED",
            details="Document parsed into clauses",
            created_at=base_time,
        ),
        AuditEvent(
            event_id=3,
            document_id=document_id,
            user_id=1,
            action="GRAPH_BUILT",
            details="Clause dependency graph constructed",
            created_at=base_time,
        ),
        AuditEvent(
            event_id=4,
            document_id=document_id,
            user_id=1,
            action="ANALYZED",
            details="AI playbook risk analysis complete",
            created_at=base_time,
        ),
    ]

