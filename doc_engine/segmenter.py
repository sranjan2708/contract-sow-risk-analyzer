"""
Clause segmentation module.
Parses page text into structured Clause objects using heading patterns.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from shared.contracts import Clause

logger = logging.getLogger(__name__)

# Matches numbered headings such as "3.1 Scope", "Section 8.1: Limitation", "11.2. Termination"
HEADING_PATTERN = re.compile(
    r"^(?:(?:Section|Clause)\s+)?(\d+(?:\.\d+)+)(?:[.:\-]\s*|\s+)?(.*)$",
    re.IGNORECASE,
)

# Matches cross-clause references like "Section 8.1", "Section 14.3", "Sections 3.1"
REFERENCE_PATTERN = re.compile(
    r"\bSections?\s+(\d+(?:\.\d+)+)",
    re.IGNORECASE,
)


def _compute_parent_clause_id(clause_id: str) -> Optional[str]:
    """
    Compute parent clause ID if depth is 3 or more (e.g. "3.1.2" -> "3.1", "3.1" -> None).
    """
    parts = clause_id.split(".")
    if len(parts) > 2:
        return ".".join(parts[:-1])
    return None


def _extract_references(text: str, current_clause_id: str) -> list[str]:
    """
    Extract referenced clause IDs from text (e.g. 'Section 8.1'), excluding current_clause_id.
    """
    matches = REFERENCE_PATTERN.findall(text)
    unique_refs: list[str] = []
    for ref in matches:
        if ref != current_clause_id and ref not in unique_refs:
            unique_refs.append(ref)
    return unique_refs


def segment(pages: list[tuple[int, str]]) -> list[Clause]:
    """
    Segment extracted pages into a list of unique Clause models.

    Args:
        pages: List of (page_number, text) tuples (1-based page numbers).

    Returns:
        List of unique Clause contract models, keeping the first occurrence of each clause_id.
    """
    raw_clauses: list[dict] = []
    current: Optional[dict] = None

    for page_num, page_text in pages:
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            match = HEADING_PATTERN.match(line)
            if match:
                # Finalize previous clause if present
                if current is not None:
                    raw_clauses.append(current)

                clause_id = match.group(1).strip()
                raw_title = match.group(2).strip()
                title = raw_title if raw_title else None

                current = {
                    "clause_id": clause_id,
                    "title": title,
                    "text_lines": [],
                    "page_number": max(page_num, 1),
                }
            else:
                if current is not None:
                    current["text_lines"].append(line)

    if current is not None:
        raw_clauses.append(current)

    clauses: list[Clause] = []
    seen_ids: set[str] = set()

    for item in raw_clauses:
        clause_id = str(item["clause_id"])
        if clause_id in seen_ids:
            logger.debug("Skipping duplicate clause_id '%s'", clause_id)
            continue

        title = item["title"]
        body_text = " ".join(item["text_lines"]).strip()
        # Ensure text is non-empty
        text = body_text if body_text else (title if title else clause_id)

        section = clause_id.split(".")[0]
        parent_clause_id = _compute_parent_clause_id(clause_id)
        references = _extract_references(f"{title or ''} {text}", clause_id)

        clause = Clause(
            clause_id=clause_id,
            title=title,
            text=text,
            page_number=item["page_number"],
            section=section,
            parent_clause_id=parent_clause_id,
            references=references,
        )
        clauses.append(clause)
        seen_ids.add(clause_id)

    logger.debug("Segmented %d unique clauses", len(clauses))
    return clauses

