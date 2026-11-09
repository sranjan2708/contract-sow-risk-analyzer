"""
PDF extraction module using PyMuPDF (fitz).
Extracts raw page text along with 1-based page numbers.
"""
from __future__ import annotations

import logging
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


def extract_pages(path: str) -> list[tuple[int, str]]:
    """
    Extract text from each page of a PDF document.

    Args:
        path: Path to the PDF file.

    Returns:
        List of (page_number, text) tuples, with page_number starting at 1.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be opened as a valid PDF.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        logger.error("PyMuPDF failed to open %s: %s", path, exc)
        raise ValueError(f"Unreadable PDF document '{path}': {exc}") from exc

    pages: list[tuple[int, str]] = []
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text()
            pages.append((page_index + 1, text))
    except Exception as exc:
        logger.error("Error extracting text from %s: %s", path, exc)
        raise ValueError(f"Failed to extract pages from '{path}': {exc}") from exc
    finally:
        doc.close()

    logger.debug("Extracted %d pages from %s", len(pages), path)
    return pages

