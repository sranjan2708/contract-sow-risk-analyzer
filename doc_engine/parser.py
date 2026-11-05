"""
Document parsing engine module.
STUB — owner replaces body, keep signature.
"""
from __future__ import annotations

import logging
from pathlib import Path

from shared.contracts import DocumentType, ParsedDocument
from shared.samples import sample_msa, sample_sow

logger = logging.getLogger(__name__)


def parse_document(file_path: str, document_type: str) -> ParsedDocument:
    """
    Parse a PDF or DOCX contract document into structured clauses.

    STUB — owner replaces body, keep signature.

    Args:
        file_path: Path to the target contract document (.pdf or .docx).
        document_type: String representation of DocumentType ('MSA', 'SOW', 'OTHER').

    Returns:
        ParsedDocument: Validated parsed document contract model.

    Raises:
        ValueError: If document_type is invalid or file extension is not supported.
    """
    doc_type = DocumentType(document_type)

    path = Path(file_path)
    extension = path.suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise ValueError(f"Unsupported file format '{extension}'. Only .pdf and .docx are supported.")

    logger.warning("STUB: parse_document is returning sample stub data for %s", file_path)

    base = sample_msa() if doc_type == DocumentType.MSA else sample_sow()
    doc_copy = base.model_copy(deep=True)
    doc_copy.document_id = None
    doc_copy.file_name = path.name
    doc_copy.document_type = doc_type
    return doc_copy

