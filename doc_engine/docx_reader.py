"""
DOCX extraction module using python-docx.
Extracts document paragraphs and table cell contents in reading order.
DOCX files do not have fixed page layouts, so text is returned as page 1.
"""
from __future__ import annotations

import logging
from pathlib import Path

import docx

logger = logging.getLogger(__name__)


def extract_docx_text(path: str) -> list[tuple[int, str]]:
    """
    Extract text from a DOCX document in sequential order.

    Paragraphs and table cell contents are extracted in reading order and
    returned as a single page tuple (1, text) because DOCX files lack
    intrinsic physical page numbering.

    Args:
        path: Path to the target .docx file.

    Returns:
        List containing a single tuple [(1, full_text)].

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be opened as a valid DOCX document.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"DOCX file not found: '{path}'")

    try:
        doc = docx.Document(str(file_path))
    except Exception as exc:
        logger.error("python-docx failed to open %s: %s", path, exc)
        raise ValueError(f"Unreadable DOCX document '{path}': {exc}") from exc

    lines: list[str] = []

    try:
        # 1. Paragraphs in order
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                lines.append(text)

        # 2. Table cell contents in order
        for table in doc.tables:
            for row in table.rows:
                row_cells_text = [
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                ]
                if row_cells_text:
                    lines.append(" | ".join(row_cells_text))
    except Exception as exc:
        logger.error("Error reading contents from %s: %s", path, exc)
        raise ValueError(f"Failed to extract text from DOCX '{path}': {exc}") from exc

    full_text = "\n".join(lines).strip()
    logger.debug("Extracted %d lines from DOCX %s", len(lines), path)
    return [(1, full_text)]

