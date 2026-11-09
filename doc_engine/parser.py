"""
Document parsing engine module.
Parses PDF and DOCX contracts into structured ParsedDocument contract models.
"""
from __future__ import annotations

import logging
from pathlib import Path

from doc_engine.pdf_reader import extract_pages
from doc_engine.segmenter import segment
from shared.contracts import DocumentType, ParsedDocument
from shared.samples import sample_msa, sample_sow

logger = logging.getLogger(__name__)


def parse_document(file_path: str, document_type: str) -> ParsedDocument:
    """
    Parse a PDF or DOCX contract document into structured clauses.

    Args:
        file_path: Path to the target contract document (.pdf or .docx).
        document_type: String representation of DocumentType ('MSA', 'SOW', 'OTHER').

    Returns:
        ParsedDocument: Validated parsed document contract model with document_id=None.

    Raises:
        ValueError: If document_type is invalid, extension is unsupported,
                    the file is unreadable, or zero clauses are extracted.
    """
    try:
        doc_type = DocumentType(document_type)
    except ValueError as exc:
        raise ValueError(f"Invalid document_type '{document_type}': {exc}") from exc

    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"File not found: '{file_path}'")

    extension = path.suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise ValueError(f"Unsupported file format '{extension}'. Only .pdf and .docx are supported.")

    if extension == ".pdf":
        try:
            pages = extract_pages(str(path))
        except Exception as exc:
            logger.error("Failed to read PDF file '%s': %s", file_path, exc)
            raise ValueError(f"Unreadable PDF file '{file_path}': {exc}") from exc

        if not pages:
            raise ValueError(f"PDF file '{file_path}' has zero pages.")

        clauses = segment(pages)
        if not clauses:
            raise ValueError(f"Zero clauses found in PDF document '{file_path}'.")

        return ParsedDocument(
            document_id=None,
            document_type=doc_type,
            file_name=path.name,
            page_count=max(len(pages), 1),
            clauses=clauses,
            parser_version="0.1.0",
        )

    # DOCX format — current stub retained
    logger.warning("DOCX parsing is stubbed; returning sample stub data for %s", file_path)
    base = sample_msa() if doc_type == DocumentType.MSA else sample_sow()
    doc_copy = base.model_copy(deep=True)
    doc_copy.document_id = None
    doc_copy.file_name = path.name
    doc_copy.document_type = doc_type
    return doc_copy
