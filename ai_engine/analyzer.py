"""
AI engine analysis and comparison module.
Executes deterministic playbook rules and graph anomaly detection.
"""
from __future__ import annotations

import logging
from typing import Optional

from ai_engine.rules import check_clause_rules, check_graph_rules
from ai_engine.scoring import compute_risk_score
from shared.contracts import (
    AnalysisResult,
    ClauseGraph,
    ComparisonResult,
    ParsedDocument,
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

    Runs clause rules always, and graph rules only if graph is not None.

    Args:
        document: Validated ParsedDocument contract model.
        graph: Optional validated ClauseGraph contract model.

    Returns:
        AnalysisResult: Validated risk findings and score.
    """
    logger.info("Analyzing document %s (id: %s)", document.file_name, document.document_id)
    findings: list[RiskFinding] = []

    # 1. Clause rules are executed always
    for clause in document.clauses:
        clause_findings = check_clause_rules(clause)
        findings.extend(clause_findings)

    # 2. Graph rules are executed only if graph is provided
    if graph is not None:
        graph_findings = check_graph_rules(graph)
        findings.extend(graph_findings)

    # 3. Deterministic risk score
    score = compute_risk_score(findings)

    # 4. Summary counts per risk level
    level_counts = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH: 0,
        RiskLevel.MEDIUM: 0,
        RiskLevel.LOW: 0,
    }
    for f in findings:
        level_counts[f.risk_level] = level_counts.get(f.risk_level, 0) + 1

    summary = (
        f"Analyzed {len(document.clauses)} clauses. Found {len(findings)} risk issues: "
        f"{level_counts[RiskLevel.CRITICAL]} CRITICAL, {level_counts[RiskLevel.HIGH]} HIGH, "
        f"{level_counts[RiskLevel.MEDIUM]} MEDIUM, {level_counts[RiskLevel.LOW]} LOW."
    )

    return AnalysisResult(
        document_id=document.document_id,
        overall_risk_score=score,
        summary=summary,
        findings=findings,
        model_used="playbook-rules-v1",
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
