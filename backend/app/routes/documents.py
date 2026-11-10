"""
Documents API routes.
Implements real document upload, retrieval, clause inspection, dependency graph,
and audit trail endpoints (Contract 3, Endpoints 5, 6, 7, 8, 9, 15).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.app import repository
from backend.app.deps import get_current_user
from backend.app.pipeline import process_upload
from shared.contracts import (
    AuditEvent,
    Clause,
    ClauseGraph,
    DocumentOut,
    DocumentStatus,
    DocumentType,
    ParsedDocument,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Documents"])


def _to_utc(dt: Optional[datetime]) -> datetime:
    """Attach UTC tzinfo to naive MySQL datetimes if absent."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post(
    "/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a contract document",
)
def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: UserOut = Depends(get_current_user),
) -> DocumentOut:
    """
    Ingest, save, parse, and graph an uploaded contract document.

    Args:
        file: Multipart file stream (.pdf or .docx).
        document_type: Contract category ('MSA', 'SOW', 'OTHER').
        current_user: Authenticated UserOut from Bearer JWT.

    Returns:
        DocumentOut: Metadata and initial processing state.
    """
    return process_upload(
        upload_file=file,
        document_type=document_type,
        user_id=current_user.user_id,
    )


@router.get(
    "/documents",
    response_model=List[DocumentOut],
    status_code=status.HTTP_200_OK,
    summary="List all uploaded documents for the authenticated user",
)
def list_documents(
    current_user: UserOut = Depends(get_current_user),
) -> List[DocumentOut]:
    """
    Retrieve all documents uploaded by the current user, newest first.

    Args:
        current_user: Authenticated UserOut from Bearer JWT.

    Returns:
        List of DocumentOut instances.
    """
    docs = repository.list_documents(current_user.user_id)
    return [
        DocumentOut(
            document_id=d["document_id"],
            file_name=d["file_name"],
            document_type=DocumentType(d["document_type"]),
            status=DocumentStatus(d["status"]),
            page_count=d.get("page_count"),
            uploaded_at=_to_utc(d.get("uploaded_at")),
        )
        for d in docs
    ]


@router.get(
    "/documents/{id}",
    response_model=DocumentOut,
    status_code=status.HTTP_200_OK,
    summary="Get document details by ID",
)
def get_document(
    id: int,
    current_user: UserOut = Depends(get_current_user),
) -> DocumentOut:
    """
    Retrieve document metadata by document_id, scoped to current user.

    Args:
        id: Primary key document identifier.
        current_user: Authenticated UserOut from Bearer JWT.

    Raises:
        HTTPException: 404 if document is not found or owned by another user.

    Returns:
        DocumentOut: Validated document model.
    """
    doc = repository.get_document(id, current_user.user_id)
    if not doc:
        logger.warning("Document %d not found for user %d", id, current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentOut(
        document_id=doc["document_id"],
        file_name=doc["file_name"],
        document_type=DocumentType(doc["document_type"]),
        status=DocumentStatus(doc["status"]),
        page_count=doc.get("page_count"),
        uploaded_at=_to_utc(doc.get("uploaded_at")),
    )


@router.get(
    "/documents/{id}/clauses",
    response_model=ParsedDocument,
    status_code=status.HTTP_200_OK,
    summary="Get parsed clauses for a document",
)
def get_document_clauses(
    id: int,
    current_user: UserOut = Depends(get_current_user),
) -> ParsedDocument:
    """
    Retrieve extracted clauses for a document.

    Args:
        id: Primary key document identifier.
        current_user: Authenticated UserOut from Bearer JWT.

    Raises:
        HTTPException: 404 if document is not found or owned by another user.

    Returns:
        ParsedDocument: Validated parsed document contract model with document_id set.
    """
    doc = repository.get_document(id, current_user.user_id)
    if not doc:
        logger.warning("Document %d clauses requested but doc not found for user %d", id, current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    clause_rows = repository.get_clauses(id)
    clauses: List[Clause] = []
    for r in clause_rows:
        refs = r.get("references_json")
        if isinstance(refs, str):
            refs = json.loads(refs)
        elif refs is None:
            refs = []

        clauses.append(
            Clause(
                clause_id=r["clause_id"],
                title=r.get("title"),
                text=r["text"],
                page_number=r["page_number"],
                section=r.get("section"),
                parent_clause_id=r.get("parent_clause_id"),
                references=refs,
            )
        )

    return ParsedDocument(
        document_id=doc["document_id"],
        document_type=DocumentType(doc["document_type"]),
        file_name=doc["file_name"],
        page_count=doc.get("page_count") or 1,
        clauses=clauses,
        parser_version=doc.get("parser_version") or "0.1.0",
    )


@router.get(
    "/documents/{id}/graph",
    response_model=ClauseGraph,
    status_code=status.HTTP_200_OK,
    summary="Get clause dependency graph for a document",
)
def get_document_graph(
    id: int,
    current_user: UserOut = Depends(get_current_user),
) -> ClauseGraph:
    """
    Retrieve clause dependency graph topology for a document.

    Args:
        id: Primary key document identifier.
        current_user: Authenticated UserOut from Bearer JWT.

    Raises:
        HTTPException:
            - 404 if document is not found or owned by another user.
            - 404 if graph has not been built for the document.

    Returns:
        ClauseGraph: Validated clause dependency graph with document_id set.
    """
    doc = repository.get_document(id, current_user.user_id)
    if not doc:
        logger.warning("Document %d graph requested but doc not found for user %d", id, current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    graph_row = repository.get_graph(id)
    if not graph_row:
        logger.warning("Clause graph for document %d not found", id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clause graph not found",
        )

    graph_data = graph_row.get("graph_json")
    if isinstance(graph_data, str):
        graph_dict = json.loads(graph_data)
    elif isinstance(graph_data, dict):
        graph_dict = dict(graph_data)
    else:
        graph_dict = {}

    graph_dict["document_id"] = id
    return ClauseGraph.model_validate(graph_dict)


@router.get(
    "/documents/{id}/audit",
    response_model=List[AuditEvent],
    status_code=status.HTTP_200_OK,
    summary="Get audit event log history for a document",
)
def get_document_audit(
    id: int,
    current_user: UserOut = Depends(get_current_user),
) -> List[AuditEvent]:
    """
    Retrieve audit trail for a document, ordered chronologically.

    Args:
        id: Primary key document identifier.
        current_user: Authenticated UserOut from Bearer JWT.

    Raises:
        HTTPException: 404 if document is not found or owned by another user.

    Returns:
        List of AuditEvent contract models.
    """
    doc = repository.get_document(id, current_user.user_id)
    if not doc:
        logger.warning("Document %d audit requested but doc not found for user %d", id, current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    audit_rows = repository.list_audit(id)
    return [
        AuditEvent(
            event_id=r["event_id"],
            document_id=r["document_id"],
            user_id=r.get("user_id"),
            action=r["action"],
            details=r.get("details"),
            created_at=_to_utc(r.get("created_at")),
        )
        for r in audit_rows
    ]

