"""
API test suite for real document upload and processing endpoints (Contract 3, Endpoints 5-9, 15).
Uses TestClient with create_app(mock_mode=False), in-memory monkeypatched repository,
real doc_engine and graph_engine runs on tests/fixtures/sample_msa.pdf, and temporary UPLOAD_DIR.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from backend.app import repository
from backend.app.config import get_settings
from backend.app.main import create_app
from backend.app.security import create_access_token
from shared.contracts import (
    AuditEvent,
    Clause,
    ClauseGraph,
    DocumentOut,
    DocumentStatus,
    DocumentType,
    ParsedDocument,
)

SAMPLE_MSA_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_msa.pdf"


@pytest.fixture
def doc_repo_store(monkeypatch):
    """
    In-memory storage for repository functions.
    Monkeypatches repository calls without requiring a running MySQL instance.
    """
    users_db: Dict[int, Dict[str, Any]] = {
        1: {"user_id": 1, "email": "alice@example.com", "full_name": "Alice Analyst"},
        2: {"user_id": 2, "email": "bob@example.com", "full_name": "Bob Reviewer"},
    }
    documents_db: Dict[int, Dict[str, Any]] = {}
    clauses_db: Dict[int, List[Dict[str, Any]]] = {}
    graphs_db: Dict[int, Dict[str, Any]] = {}
    audits_db: Dict[int, List[Dict[str, Any]]] = {}

    next_doc_id = [1]
    next_clause_id = [1]
    next_audit_id = [1]

    def fake_get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        user = users_db.get(user_id)
        return dict(user) if user else None

    def fake_create_document(
        file_name: str,
        document_type: str,
        stored_path: str,
        user_id: int,
    ) -> int:
        doc_id = next_doc_id[0]
        next_doc_id[0] += 1
        now = datetime.now(timezone.utc)
        record = {
            "document_id": doc_id,
            "file_name": file_name,
            "document_type": document_type,
            "status": "UPLOADED",
            "page_count": None,
            "stored_path": stored_path,
            "parser_version": "0.1.0",
            "uploaded_at": now,
            "created_by": user_id,
        }
        documents_db[doc_id] = record
        return doc_id

    def fake_update_document_status(
        document_id: int,
        status: str,
        page_count: Optional[int] = None,
        parser_version: Optional[str] = None,
    ) -> None:
        doc = documents_db.get(document_id)
        if doc:
            doc["status"] = status
            if page_count is not None:
                doc["page_count"] = page_count
            if parser_version is not None:
                doc["parser_version"] = parser_version

    def fake_get_document(document_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        doc = documents_db.get(document_id)
        if doc and doc["created_by"] == user_id:
            return dict(doc)
        return None

    def fake_list_documents(user_id: int) -> List[Dict[str, Any]]:
        user_docs = [
            dict(d) for d in documents_db.values() if d["created_by"] == user_id
        ]
        user_docs.sort(key=lambda d: d["document_id"], reverse=True)
        return user_docs

    def fake_insert_clauses(document_id: int, clauses: List[Clause]) -> None:
        rows = clauses_db.setdefault(document_id, [])
        for c in clauses:
            rows.append({
                "id": next_clause_id[0],
                "document_id": document_id,
                "clause_id": c.clause_id,
                "title": c.title,
                "text": c.text,
                "page_number": c.page_number,
                "section": c.section,
                "parent_clause_id": c.parent_clause_id,
                "references_json": json.dumps(c.references),
                "created_at": datetime.now(timezone.utc),
            })
            next_clause_id[0] += 1

    def fake_get_clauses(document_id: int) -> List[Dict[str, Any]]:
        rows = clauses_db.get(document_id, [])
        result = []
        for r in rows:
            row_dict = dict(r)
            if isinstance(row_dict.get("references_json"), str):
                row_dict["references_json"] = json.loads(row_dict["references_json"])
            result.append(row_dict)
        return result

    def fake_save_graph(document_id: int, graph: ClauseGraph) -> None:
        graphs_db[document_id] = {
            "id": 1,
            "document_id": document_id,
            "graph_json": graph.model_dump_json(),
            "has_cycle": bool(graph.has_cycle),
            "created_at": datetime.now(timezone.utc),
        }

    def fake_get_graph(document_id: int) -> Optional[Dict[str, Any]]:
        row = graphs_db.get(document_id)
        if row:
            row_dict = dict(row)
            if isinstance(row_dict.get("graph_json"), str):
                row_dict["graph_json"] = json.loads(row_dict["graph_json"])
            return row_dict
        return None

    def fake_add_audit(
        document_id: int,
        user_id: Optional[int],
        action: str,
        details: Optional[str] = None,
    ) -> int:
        event_id = next_audit_id[0]
        next_audit_id[0] += 1
        rows = audits_db.setdefault(document_id, [])
        rows.append({
            "event_id": event_id,
            "document_id": document_id,
            "user_id": user_id,
            "action": action,
            "details": details,
            "created_at": datetime.now(timezone.utc),
        })
        return event_id

    def fake_list_audit(document_id: int) -> List[Dict[str, Any]]:
        rows = audits_db.get(document_id, [])
        return [dict(r) for r in rows]

    monkeypatch.setattr(repository, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(repository, "create_document", fake_create_document)
    monkeypatch.setattr(repository, "update_document_status", fake_update_document_status)
    monkeypatch.setattr(repository, "get_document", fake_get_document)
    monkeypatch.setattr(repository, "list_documents", fake_list_documents)
    monkeypatch.setattr(repository, "insert_clauses", fake_insert_clauses)
    monkeypatch.setattr(repository, "get_clauses", fake_get_clauses)
    monkeypatch.setattr(repository, "save_graph", fake_save_graph)
    monkeypatch.setattr(repository, "get_graph", fake_get_graph)
    monkeypatch.setattr(repository, "add_audit", fake_add_audit)
    monkeypatch.setattr(repository, "list_audit", fake_list_audit)

    return {
        "users": users_db,
        "documents": documents_db,
        "clauses": clauses_db,
        "graphs": graphs_db,
        "audits": audits_db,
    }


@pytest.fixture
def client(tmp_path: Path, monkeypatch, doc_repo_store) -> TestClient:
    """Provide a TestClient connected to create_app(False) with UPLOAD_DIR mapped to tmp_path."""
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    app = create_app(mock_mode=False)
    return TestClient(app)


@pytest.fixture
def auth_headers_user1() -> Dict[str, str]:
    """Generate authorization header for User 1."""
    token = create_access_token(user_id=1)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2() -> Dict[str, str]:
    """Generate authorization header for User 2."""
    token = create_access_token(user_id=2)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def uploaded_doc_id(client: TestClient, auth_headers_user1: Dict[str, str]) -> int:
    """Helper fixture that uploads sample_msa.pdf and returns the created document_id."""
    with open(SAMPLE_MSA_PATH, "rb") as f:
        res = client.post(
            "/api/v1/documents",
            headers=auth_headers_user1,
            files={"file": ("sample_msa.pdf", f, "application/pdf")},
            data={"document_type": "MSA"},
        )
    assert res.status_code == 201
    return res.json()["document_id"]


def test_upload_document_201_success(client: TestClient, auth_headers_user1: Dict[str, str]):
    """POST /api/v1/documents ingests sample_msa.pdf, returning 201 DocumentOut with status PARSED."""
    with open(SAMPLE_MSA_PATH, "rb") as f:
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers_user1,
            files={"file": ("sample_msa.pdf", f, "application/pdf")},
            data={"document_type": "MSA"},
        )
    assert response.status_code == 201

    data = response.json()
    doc_out = DocumentOut.model_validate(data)
    assert doc_out.document_id == 1
    assert doc_out.file_name == "sample_msa.pdf"
    assert doc_out.document_type == DocumentType.MSA
    assert doc_out.status == DocumentStatus.PARSED
    assert doc_out.page_count is not None and doc_out.page_count >= 1
    assert doc_out.uploaded_at.tzinfo is not None


def test_list_and_get_document(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    uploaded_doc_id: int,
):
    """GET /api/v1/documents and GET /api/v1/documents/{id} retrieve uploaded documents."""
    # List documents
    list_res = client.get("/api/v1/documents", headers=auth_headers_user1)
    assert list_res.status_code == 200
    docs = [DocumentOut.model_validate(d) for d in list_res.json()]
    assert len(docs) == 1
    assert docs[0].document_id == uploaded_doc_id
    assert docs[0].file_name == "sample_msa.pdf"

    # Get document by ID
    get_res = client.get(f"/api/v1/documents/{uploaded_doc_id}", headers=auth_headers_user1)
    assert get_res.status_code == 200
    single_doc = DocumentOut.model_validate(get_res.json())
    assert single_doc.document_id == uploaded_doc_id
    assert single_doc.status == DocumentStatus.PARSED


def test_get_document_clauses(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    uploaded_doc_id: int,
):
    """GET /api/v1/documents/{id}/clauses returns 4 parsed clauses with IDs 3.1, 5.1, 8.1, 11.2."""
    response = client.get(f"/api/v1/documents/{uploaded_doc_id}/clauses", headers=auth_headers_user1)
    assert response.status_code == 200

    parsed_doc = ParsedDocument.model_validate(response.json())
    assert parsed_doc.document_id == uploaded_doc_id
    assert len(parsed_doc.clauses) == 4
    clause_ids = [c.clause_id for c in parsed_doc.clauses]
    assert clause_ids == ["3.1", "5.1", "8.1", "11.2"]


def test_get_document_graph(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    uploaded_doc_id: int,
):
    """GET /api/v1/documents/{id}/graph returns ClauseGraph with cycle=True and missing 14.3."""
    response = client.get(f"/api/v1/documents/{uploaded_doc_id}/graph", headers=auth_headers_user1)
    assert response.status_code == 200

    graph = ClauseGraph.model_validate(response.json())
    assert graph.document_id == uploaded_doc_id
    assert graph.has_cycle is True
    missing_targets = [inv.missing_target for inv in graph.invalid_references]
    assert "14.3" in missing_targets


def test_get_document_audit(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    uploaded_doc_id: int,
):
    """GET /api/v1/documents/{id}/audit records UPLOADED, PARSED, and GRAPH_BUILT actions."""
    response = client.get(f"/api/v1/documents/{uploaded_doc_id}/audit", headers=auth_headers_user1)
    assert response.status_code == 200

    events = [AuditEvent.model_validate(e) for e in response.json()]
    assert len(events) >= 3
    actions = [e.action for e in events]
    assert actions == ["UPLOADED", "PARSED", "GRAPH_BUILT"]

    for event in events:
        assert event.document_id == uploaded_doc_id
        assert event.created_at.tzinfo is not None


def test_unauthenticated_requests_401(client: TestClient):
    """Endpoints 5-9 and 15 reject requests lacking Bearer token with 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/v1/documents"),
        ("GET", "/api/v1/documents/1"),
        ("GET", "/api/v1/documents/1/clauses"),
        ("GET", "/api/v1/documents/1/graph"),
        ("GET", "/api/v1/documents/1/audit"),
    ]
    for method, path in endpoints:
        res = client.request(method, path)
        assert res.status_code == 401
        assert "detail" in res.json()

    post_res = client.post("/api/v1/documents", files={"file": ("test.pdf", b"content", "application/pdf")})
    assert post_res.status_code == 401


def test_upload_invalid_extension_400(client: TestClient, auth_headers_user1: Dict[str, str]):
    """POST /api/v1/documents with .txt file returns 400 Bad Request."""
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers_user1,
        files={"file": ("contract.txt", io.BytesIO(b"Plain text contract content"), "text/plain")},
        data={"document_type": "MSA"},
    )
    assert response.status_code == 400
    err = response.json()
    assert "detail" in err
    assert "unsupported file format" in err["detail"].lower()


def test_other_user_document_404(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    auth_headers_user2: Dict[str, str],
    uploaded_doc_id: int,
):
    """Requesting another user's or non-existent document returns 404 {"detail": "Document not found"}."""
    # User 2 accesses User 1's document
    paths = [
        f"/api/v1/documents/{uploaded_doc_id}",
        f"/api/v1/documents/{uploaded_doc_id}/clauses",
        f"/api/v1/documents/{uploaded_doc_id}/graph",
        f"/api/v1/documents/{uploaded_doc_id}/audit",
    ]
    for path in paths:
        res = client.get(path, headers=auth_headers_user2)
        assert res.status_code == 404
        assert res.json() == {"detail": "Document not found"}

    # Non-existent document 99999
    res_non_existent = client.get("/api/v1/documents/99999", headers=auth_headers_user1)
    assert res_non_existent.status_code == 404
    assert res_non_existent.json() == {"detail": "Document not found"}


def test_parser_failure_422_status_failed_audit_failed(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    doc_repo_store: Dict[str, Any],
    monkeypatch,
):
    """Parser ValueError triggers 422 error, marks status as FAILED, and logs FAILED audit."""
    error_message = "Corrupt PDF stream: unreadable clause boundaries"

    def faulty_parse(file_path: str, document_type: str):
        raise ValueError(error_message)

    monkeypatch.setattr("backend.app.pipeline.parse_document", faulty_parse)

    with open(SAMPLE_MSA_PATH, "rb") as f:
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers_user1,
            files={"file": ("corrupt.pdf", f, "application/pdf")},
            data={"document_type": "MSA"},
        )
    assert response.status_code == 422
    assert error_message in response.json()["detail"]

    # Verify document status updated to FAILED in repository
    created_id = list(doc_repo_store["documents"].keys())[0]
    doc_record = doc_repo_store["documents"][created_id]
    assert doc_record["status"] == "FAILED"

    # Verify audit log includes FAILED event with error message
    audits = doc_repo_store["audits"][created_id]
    audit_actions = [a["action"] for a in audits]
    assert "UPLOADED" in audit_actions
    assert "FAILED" in audit_actions

    failed_event = next(a for a in audits if a["action"] == "FAILED")
    assert error_message in failed_event["details"]


def test_upload_file_size_exceeded_413(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    monkeypatch,
):
    """File exceeding MAX_UPLOAD_MB returns 413 Request Entity Too Large."""
    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)

    # 1.5 MB payload
    large_payload = b"A" * int(1.5 * 1024 * 1024)
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers_user1,
        files={"file": ("oversized.pdf", io.BytesIO(large_payload), "application/pdf")},
        data={"document_type": "MSA"},
    )
    assert response.status_code == 413
    assert "exceeds maximum upload size" in response.json()["detail"]


def test_upload_invalid_document_type_422(client: TestClient, auth_headers_user1: Dict[str, str]):
    """POST /api/v1/documents with invalid document_type returns 422 Unprocessable Entity."""
    with open(SAMPLE_MSA_PATH, "rb") as f:
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers_user1,
            files={"file": ("sample_msa.pdf", f, "application/pdf")},
            data={"document_type": "NON_EXISTENT_TYPE"},
        )
    assert response.status_code == 422
    assert "invalid document_type" in response.json()["detail"].lower()


def test_graph_not_built_404(
    client: TestClient,
    auth_headers_user1: Dict[str, str],
    doc_repo_store: Dict[str, Any],
):
    """GET /api/v1/documents/{id}/graph returns 404 when graph is missing."""
    # Create document without graph in repo store
    doc_repo_store["documents"][99] = {
        "document_id": 99,
        "file_name": "no_graph.pdf",
        "document_type": "MSA",
        "status": "UPLOADED",
        "page_count": None,
        "stored_path": "/tmp/no_graph.pdf",
        "parser_version": "0.1.0",
        "uploaded_at": datetime.now(timezone.utc),
        "created_by": 1,
    }

    response = client.get("/api/v1/documents/99/graph", headers=auth_headers_user1)
    assert response.status_code == 404
    assert "clause graph not found" in response.json()["detail"].lower()
