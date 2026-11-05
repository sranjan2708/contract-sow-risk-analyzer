"""
API test suite using FastAPI TestClient against mock endpoints.
"""
from __future__ import annotations

import io
from fastapi.testclient import TestClient

from backend.app.main import app
from shared.contracts import (
    AnalysisResult,
    ClauseGraph,
    ComparisonResult,
    DocumentOut,
    ParsedDocument,
    ReviewStatus,
    RiskFinding,
)

client = TestClient(app)


def test_health_ok():
    """GET /api/v1/health returns status 200 with status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mock_mode" in data
    assert "contract_version" in data


def test_upload_document_201():
    """POST /api/v1/documents returns 201 and validates against DocumentOut."""
    file_bytes = io.BytesIO(b"%PDF-1.4 dummy pdf contract content")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("master_agreement.pdf", file_bytes, "application/pdf")},
        data={"document_type": "MSA"},
    )
    assert response.status_code == 201
    doc_out = DocumentOut.model_validate(response.json())
    assert doc_out.document_id == 1
    assert doc_out.file_name == "master_agreement.pdf"


def test_clauses_graph_and_analyze_validate_against_models():
    """GET clauses, GET graph, and POST analyze endpoints validate against their contract models."""
    # Clauses
    response = client.get("/api/v1/documents/1/clauses")
    assert response.status_code == 200
    clauses_doc = ParsedDocument.model_validate(response.json())
    assert len(clauses_doc.clauses) > 0

    # Graph
    response = client.get("/api/v1/documents/1/graph")
    assert response.status_code == 200
    graph = ClauseGraph.model_validate(response.json())
    assert len(graph.nodes) > 0

    # Analyze
    response = client.post("/api/v1/documents/1/analyze")
    assert response.status_code == 200
    analysis = AnalysisResult.model_validate(response.json())
    assert analysis.overall_risk_score > 0
    assert len(analysis.findings) > 0


def test_compare_documents_validates_against_model():
    """POST /api/v1/compare returns 200 and validates against ComparisonResult."""
    response = client.post(
        "/api/v1/compare",
        json={"msa_document_id": 1, "sow_document_id": 2},
    )
    assert response.status_code == 200
    comparison = ComparisonResult.model_validate(response.json())
    assert len(comparison.contradictions) > 0


def test_review_finding_101_accepted():
    """PATCH /api/v1/findings/101/review updates finding review status to ACCEPTED."""
    response = client.patch(
        "/api/v1/findings/101/review",
        json={"review_status": "ACCEPTED", "comment": "Approved by senior legal counsel"},
    )
    assert response.status_code == 200
    reviewed_finding = RiskFinding.model_validate(response.json())
    assert reviewed_finding.finding_id == 101
    assert reviewed_finding.review_status == ReviewStatus.ACCEPTED


def test_get_unknown_document_404_with_detail():
    """GET /api/v1/documents/999 must return 404 with a detail property in response."""
    response = client.get("/api/v1/documents/999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
