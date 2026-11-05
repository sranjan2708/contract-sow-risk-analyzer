"""
AI engine analysis and comparison module.
STUB — owner replaces body, keep signature.
"""
from __future__ import annotations

import logging
from typing import Optional

from shared.contracts import (
    AnalysisResult,
    ClauseGraph,
    ComparisonResult,
    Evidence,
    EvidenceSource,
    ParsedDocument,
    ReviewStatus,
    RiskCategory,
    RiskFinding,
    RiskLevel,
)

logger = logging.getLogger(__name__)


def analyze_document(
    document: ParsedDocument,
    graph: Optional[ClauseGraph] = None,
) -> AnalysisResult:
    """
    Analyze a parsed contract document and optional clause graph against playbook rules.

    STUB — owner replaces body, keep signature.

    Args:
        document: Validated ParsedDocument contract model.
        graph: Optional validated ClauseGraph contract model.

    Returns:
        AnalysisResult: Validated risk findings and score.
    """
    logger.warning("STUB: analyze_document using stub implementation.")
    findings: list[RiskFinding] = []

    if graph is not None:
        for index, inv in enumerate(graph.invalid_references, start=1):
            finding = RiskFinding(
                finding_id=index,
                clause_id=inv.clause_id,
                risk_level=RiskLevel.MEDIUM,
                risk_category=RiskCategory.OTHER,
                explanation=f"Clause {inv.clause_id} references missing clause {inv.missing_target}.",
                evidence=[
                    Evidence(
                        source=EvidenceSource.GRAPH,
                        reference=f"{inv.clause_id}->{inv.missing_target}",
                        quote=f"Invalid reference to non-existent clause {inv.missing_target}.",
                        page_number=None,
                    )
                ],
                suggested_redline=None,
                review_status=ReviewStatus.PENDING,
            )
            findings.append(finding)

    n = len(findings)
    score = float(min(100, 25 * n))
    summary = f"Stub analysis completed for {len(document.clauses)} clauses. Found {n} risk issues."

    return AnalysisResult(
        document_id=document.document_id,
        overall_risk_score=score,
        summary=summary,
        findings=findings,
        model_used="stub",
    )


def compare_documents(
    msa: ParsedDocument,
    sow: ParsedDocument,
) -> ComparisonResult:
    """
    Compare MSA and SOW documents to detect contradictory clauses and scope misalignments.

    STUB — owner replaces body, keep signature.

    Args:
        msa: Validated ParsedDocument representing the Master Services Agreement.
        sow: Validated ParsedDocument representing the Statement of Work.

    Returns:
        ComparisonResult: Validated contradiction findings.
    """
    logger.warning("STUB: compare_documents using stub implementation.")
    return ComparisonResult(
        msa_document_id=msa.document_id,
        sow_document_id=sow.document_id,
        contradictions=[],
        model_used="stub",
    )

