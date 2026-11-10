"""
Document processing pipeline.
Implements the 8-step contract ingestion, storage, parsing, graphing, and audit trail.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from fastapi import HTTPException, UploadFile, status

from backend.app import repository
from backend.app.config import get_settings
from doc_engine import parse_document
from graph_engine import build_graph
from shared.contracts import DocumentOut, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1MB chunk size for streaming


def process_upload(
    upload_file: UploadFile,
    document_type: Union[DocumentType, str],
    user_id: int,
) -> DocumentOut:
    """
    Execute the sequential 8-step document upload and processing pipeline.

    Steps:
        1. Validate format (.pdf/.docx), size (< MAX_UPLOAD_MB), and document_type.
        2. Safely save stream to UPLOAD_DIR/<uuid>_<filename>.
        3. Insert record into documents table with status UPLOADED and record audit UPLOADED.
        4. Parse document into clauses via doc_engine.parse_document, update status to PARSED,
           record page_count and parser_version, and log audit PARSED.
        5. Batch insert extracted clauses into database within a transaction.
        6. Build clause dependency graph via graph_engine.build_graph, persist to database,
           and record audit GRAPH_BUILT.
        7. On any failure post-insert: set status to FAILED, record audit FAILED with error text,
           and raise HTTPException (422 for ValueError, 500 otherwise).
        8. Return validated DocumentOut contract model.

    Args:
        upload_file: Uploaded contract file.
        document_type: Contract type string or DocumentType enum.
        user_id: ID of the authenticated user uploading the document.

    Raises:
        HTTPException:
            - 400: If file extension is unsupported or filename is missing.
            - 413: If file size exceeds MAX_UPLOAD_MB.
            - 422: If document_type is invalid or parsing fails with ValueError.
            - 500: If file writing or pipeline execution encounters an unexpected error.

    Returns:
        DocumentOut: Validated document output model.
    """
    # 1. Validate document_type
    if isinstance(document_type, DocumentType):
        doc_type = document_type
    else:
        try:
            doc_type = DocumentType(str(document_type))
        except ValueError as exc:
            logger.warning("Invalid document_type '%s'", document_type)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid document_type '{document_type}'. Must be one of: {[e.value for e in DocumentType]}",
            ) from exc

    # 1. Validate file extension
    raw_filename = upload_file.filename or ""
    if not raw_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename",
        )

    file_suffix = Path(raw_filename).suffix.lower()
    if file_suffix not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_suffix}'. Only .pdf and .docx files are supported.",
        )

    # 2. Save file stream safely to UPLOAD_DIR
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(raw_filename).name
    unique_filename = f"{uuid.uuid4()}_{safe_filename}"
    destination_path = upload_dir / unique_filename

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    total_bytes = 0

    try:
        upload_file.file.seek(0)
        with open(destination_path, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    break
                buffer.write(chunk)
    except Exception as exc:
        if destination_path.exists():
            destination_path.unlink(missing_ok=True)
        logger.exception("Failed to write uploaded file to disk: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write uploaded file: {exc}",
        ) from exc

    if total_bytes > max_bytes:
        if destination_path.exists():
            destination_path.unlink(missing_ok=True)
        logger.warning(
            "Upload rejected: %s (%d bytes) exceeds %d MB limit",
            safe_filename,
            total_bytes,
            settings.MAX_UPLOAD_MB,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_MB} MB",
        )

    # 3. Insert document record and log UPLOADED audit
    document_id = repository.create_document(
        file_name=safe_filename,
        document_type=doc_type.value,
        stored_path=str(destination_path),
        user_id=user_id,
    )
    repository.add_audit(
        document_id=document_id,
        user_id=user_id,
        action="UPLOADED",
        details=f"Document uploaded successfully to {destination_path.name}",
    )

    # 4-6. Pipeline execution with atomic error handling
    try:
        # Step 4: Parse clauses
        parsed_doc = parse_document(str(destination_path), doc_type.value)
        repository.update_document_status(
            document_id=document_id,
            status=DocumentStatus.PARSED.value,
            page_count=parsed_doc.page_count,
            parser_version=parsed_doc.parser_version,
        )
        repository.add_audit(
            document_id=document_id,
            user_id=user_id,
            action="PARSED",
            details=(
                f"Document parsed successfully into {len(parsed_doc.clauses)} "
                f"clauses across {parsed_doc.page_count} pages"
            ),
        )

        # Step 5: Store clauses in database
        repository.insert_clauses(document_id, parsed_doc.clauses)

        # Step 6: Build clause dependency graph and persist
        parsed_doc.document_id = document_id
        graph = build_graph(parsed_doc)
        graph.document_id = document_id
        repository.save_graph(document_id, graph)
        repository.add_audit(
            document_id=document_id,
            user_id=user_id,
            action="GRAPH_BUILT",
            details=(
                f"Clause dependency graph constructed with {len(graph.nodes)} "
                f"nodes, {len(graph.edges)} edges, has_cycle={graph.has_cycle}"
            ),
        )

    except Exception as exc:
        logger.exception("Pipeline failure for document_id %d: %s", document_id, exc)
        try:
            repository.update_document_status(
                document_id=document_id,
                status=DocumentStatus.FAILED.value,
            )
            repository.add_audit(
                document_id=document_id,
                user_id=user_id,
                action="FAILED",
                details=str(exc),
            )
        except Exception as audit_err:
            logger.error(
                "Failed to update document %d status/audit to FAILED: %s",
                document_id,
                audit_err,
            )

        if isinstance(exc, ValueError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # Retrieve saved document row to return DocumentOut
    doc_record = repository.get_document(document_id, user_id)
    if doc_record is not None:
        uploaded_at = doc_record["uploaded_at"]
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        return DocumentOut(
            document_id=doc_record["document_id"],
            file_name=doc_record["file_name"],
            document_type=DocumentType(doc_record["document_type"]),
            status=DocumentStatus(doc_record["status"]),
            page_count=doc_record["page_count"],
            uploaded_at=uploaded_at,
        )

    return DocumentOut(
        document_id=document_id,
        file_name=safe_filename,
        document_type=doc_type,
        status=DocumentStatus.PARSED,
        page_count=parsed_doc.page_count,
        uploaded_at=datetime.now(timezone.utc),
    )

