"""
Pure rule-evaluation functions for contracts and clause graphs.
Maps clause content and graph anomalies to deterministic RiskFindings.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from ai_engine.playbook_loader import PlaybookRule, get_rule_by_id
from shared.contracts import (
    Clause,
    ClauseGraph,
    Evidence,
    EvidenceSource,
    ReviewStatus,
    RiskCategory,
    RiskFinding,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# --- Payment Patterns ---
PAYMENT_DAY_PATTERNS = [
    # Match net terms: "net 60", "Net-60", "NET 30"
    re.compile(r"\bnet\s*[-–—]?\s*(\d+)\b", re.IGNORECASE),
    # Match parenthesized days: "(60) days", "( 60 ) days", "sixty (60) days"
    re.compile(r"\(\s*(\d+)\s*\)\s*(?:calendar\s+|business\s+)?days\b", re.IGNORECASE),
    # Match direct days: "60 days", "30 calendar days", "within 60 days"
    re.compile(r"\b(\d+)\s*(?:calendar\s+|business\s+)?days\b", re.IGNORECASE),
]

WORD_DAYS: dict[str, int] = {
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty-five": 45,
    "forty five": 45,
    "sixty": 60,
    "ninety": 90,
    "one hundred twenty": 120,
}

WORD_DAY_PATTERN = re.compile(
    r"\b(ten|fifteen|twenty|thirty|forty-five|forty\s+five|sixty|ninety|one\s+hundred\s+twenty)\s*(?:calendar\s+|business\s+)?days\b",
    re.IGNORECASE,
)

# --- Liability Patterns ---
LIABILITY_RED_FLAGS = [
    re.compile(r"\bunlimited\b", re.IGNORECASE),
    re.compile(r"\bshall\s+not\s+be\s+limited\b", re.IGNORECASE),
    re.compile(r"\bno\s+cap\b", re.IGNORECASE),
    re.compile(r"\buncapped\b", re.IGNORECASE),
]

# --- Termination Patterns ---
NOTICE_DAY_PATTERNS = [
    re.compile(r"\(\s*(\d+)\s*\)\s*(?:calendar\s+|business\s+)?days\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*(?:calendar\s+|business\s+)?days\b", re.IGNORECASE),
]

NOTICE_WORD_PATTERN = re.compile(
    r"\b(five|seven|ten|fourteen|fifteen|twenty|thirty)\s*(?:calendar\s+|business\s+)?days\b",
    re.IGNORECASE,
)


def _extract_snippet(text: str, max_length: int = 250) -> str:
    """Return a clean text snippet for evidence quote."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip() + "..."


def extract_payment_days(text: str) -> Optional[int]:
    """
    Extract payment terms duration in days from text expressions.
    Recognizes formats like '(60) days', '60 days', 'net 60', 'net-60'.

    Args:
        text: Clause text.

    Returns:
        Integer number of days if detected, otherwise None.
    """
    for pattern in PAYMENT_DAY_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))

    word_match = WORD_DAY_PATTERN.search(text)
    if word_match:
        word = word_match.group(1).lower().replace("  ", " ")
        if word in WORD_DAYS:
            return WORD_DAYS[word]

    return None


def extract_notice_days(text: str) -> Optional[int]:
    """
    Extract termination notice duration in days from text.
    Returns 0 if 'immediately' or 'immediate' is present.

    Args:
        text: Clause text.

    Returns:
        Integer number of days if detected, otherwise None.
    """
    if re.search(r"\bimmediate(?:ly)?\b", text, re.IGNORECASE):
        return 0

    for pattern in NOTICE_DAY_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))

    word_match = NOTICE_WORD_PATTERN.search(text)
    if word_match:
        word = word_match.group(1).lower()
        if word in WORD_DAYS:
            return WORD_DAYS[word]

    return None


def check_liability_clause(
    clause: Clause, rule: Optional[PlaybookRule] = None
) -> list[RiskFinding]:
    """
    Evaluate clause against LIABILITY playbook rule (PB-LIAB-01).
    Flags clauses where liability is unlimited, uncapped, or has no cap -> CRITICAL.

    Args:
        clause: Contract clause to evaluate.
        rule: Optional preloaded PlaybookRule.

    Returns:
        List of RiskFinding instances (empty if compliant).
    """
    title = (clause.title or "").lower()
    text = clause.text.lower()

    # Must be a clause addressing liability or indemnity
    is_liability = "liability" in title or "liability" in text or "limitation of liability" in title
    if not is_liability:
        return []

    matched_flag: Optional[str] = None
    for pattern in LIABILITY_RED_FLAGS:
        m = pattern.search(clause.text) or pattern.search(clause.title or "")
        if m:
            matched_flag = m.group(0)
            break

    if not matched_flag:
        return []

    if rule is None:
        rule = get_rule_by_id("PB-LIAB-01")

    standard_quote = rule.standard if rule else "Liability must be capped at 12 months fees paid or payable."
    fallback_lang = rule.fallback_language if rule else None

    finding = RiskFinding(
        finding_id=None,
        clause_id=clause.clause_id,
        risk_level=RiskLevel.CRITICAL,
        risk_category=RiskCategory.LIABILITY,
        explanation=f"Clause contains red flag '{matched_flag}': liability must be capped under playbook standards.",
        evidence=[
            Evidence(
                source=EvidenceSource.CLAUSE,
                reference=clause.clause_id,
                quote=_extract_snippet(clause.text),
                page_number=clause.page_number,
            ),
            Evidence(
                source=EvidenceSource.PLAYBOOK,
                reference="PB-LIAB-01",
                quote=standard_quote,
                page_number=None,
            ),
        ],
        suggested_redline=fallback_lang,
        review_status=ReviewStatus.PENDING,
    )
    return [finding]


def check_payment_clause(
    clause: Clause, rule: Optional[PlaybookRule] = None
) -> list[RiskFinding]:
    """
    Evaluate clause against PAYMENT playbook rule (PB-PAY-01).
    Flags payment terms > 30 days or 'pay when paid' clauses -> HIGH.

    Args:
        clause: Contract clause to evaluate.
        rule: Optional preloaded PlaybookRule.

    Returns:
        List of RiskFinding instances (empty if compliant).
    """
    title = (clause.title or "").lower()
    text = clause.text.lower()

    # Determine if this clause governs payment/invoicing/fees
    payment_title_keywords = (
        "payment",
        "fee",
        "fees",
        "invoice",
        "invoicing",
        "billing",
        "compensation",
        "payable",
    )
    is_payment = any(k in title for k in payment_title_keywords) or any(
        phrase in text
        for phrase in (
            "pay when paid",
            "undisputed invoice",
            "payment terms",
            "net 30",
            "net 60",
            "net 90",
        )
    )

    if not is_payment:
        return []

    days = extract_payment_days(clause.text)
    is_pay_when_paid = "pay when paid" in text

    is_violation = is_pay_when_paid or (days is not None and days > 30)
    if not is_violation:
        return []

    if rule is None:
        rule = get_rule_by_id("PB-PAY-01")

    standard_quote = rule.standard if rule else "Payment terms must be net thirty (30) days or less."
    fallback_lang = rule.fallback_language if rule else None

    if is_pay_when_paid:
        explanation = "Payment clause contains contingent 'pay when paid' condition, violating payment standards."
    else:
        explanation = f"Payment terms of {days} days exceed standard threshold of 30 days."

    finding = RiskFinding(
        finding_id=None,
        clause_id=clause.clause_id,
        risk_level=RiskLevel.HIGH,
        risk_category=RiskCategory.PAYMENT,
        explanation=explanation,
        evidence=[
            Evidence(
                source=EvidenceSource.CLAUSE,
                reference=clause.clause_id,
                quote=_extract_snippet(clause.text),
                page_number=clause.page_number,
            ),
            Evidence(
                source=EvidenceSource.PLAYBOOK,
                reference="PB-PAY-01",
                quote=standard_quote,
                page_number=None,
            ),
        ],
        suggested_redline=fallback_lang,
        review_status=ReviewStatus.PENDING,
    )
    return [finding]


def check_termination_clause(
    clause: Clause, rule: Optional[PlaybookRule] = None
) -> list[RiskFinding]:
    """
    Evaluate clause against TERMINATION playbook rule (PB-TERM-01).
    Flags termination for convenience with notice < 30 days or 'immediately' -> MEDIUM.

    Args:
        clause: Contract clause to evaluate.
        rule: Optional preloaded PlaybookRule.

    Returns:
        List of RiskFinding instances (empty if compliant).
    """
    title = (clause.title or "").lower()
    text = clause.text.lower()
    combined = f"{title} {text}"

    is_term_for_convenience = (
        ("terminat" in title or "terminat" in text) and "convenience" in combined
    )
    if not is_term_for_convenience:
        return []

    days = extract_notice_days(clause.text)
    is_immediate = re.search(r"\bimmediate(?:ly)?\b", text) is not None

    is_violation = is_immediate or (days is not None and days < 30)
    if not is_violation:
        return []

    if rule is None:
        rule = get_rule_by_id("PB-TERM-01")

    standard_quote = (
        rule.standard
        if rule
        else "Termination for convenience must require at least thirty (30) days prior written notice."
    )
    fallback_lang = rule.fallback_language if rule else None

    if is_immediate or days == 0:
        explanation = "Termination for convenience allows immediate termination without required 30-day notice period."
    else:
        explanation = f"Termination for convenience requires at least thirty (30) days notice; found {days} days."

    finding = RiskFinding(
        finding_id=None,
        clause_id=clause.clause_id,
        risk_level=RiskLevel.MEDIUM,
        risk_category=RiskCategory.TERMINATION,
        explanation=explanation,
        evidence=[
            Evidence(
                source=EvidenceSource.CLAUSE,
                reference=clause.clause_id,
                quote=_extract_snippet(clause.text),
                page_number=clause.page_number,
            ),
            Evidence(
                source=EvidenceSource.PLAYBOOK,
                reference="PB-TERM-01",
                quote=standard_quote,
                page_number=None,
            ),
        ],
        suggested_redline=fallback_lang,
        review_status=ReviewStatus.PENDING,
    )
    return [finding]


def check_clause_rules(clause: Clause) -> list[RiskFinding]:
    """
    Evaluate a single clause against all playbook clause rules.

    Args:
        clause: Contract clause to analyze.

    Returns:
        List of all RiskFinding items flagged for the clause.
    """
    findings: list[RiskFinding] = []
    findings.extend(check_liability_clause(clause))
    findings.extend(check_payment_clause(clause))
    findings.extend(check_termination_clause(clause))
    return findings


def check_graph_rules(graph: ClauseGraph) -> list[RiskFinding]:
    """
    Evaluate clause graph anomalies (invalid references and dependency cycles).
    - Each invalid reference -> MEDIUM, category OTHER.
    - Each cycle -> MEDIUM, category OTHER, explanation lists the cycle.
    suggested_redline is None for graph findings.

    Args:
        graph: Validated ClauseGraph.

    Returns:
        List of RiskFinding instances for graph anomalies.
    """
    findings: list[RiskFinding] = []

    # 1. Invalid references
    for inv in graph.invalid_references:
        finding = RiskFinding(
            finding_id=None,
            clause_id=inv.clause_id,
            risk_level=RiskLevel.MEDIUM,
            risk_category=RiskCategory.OTHER,
            explanation=f"Clause {inv.clause_id} references missing clause {inv.missing_target}.",
            evidence=[
                Evidence(
                    source=EvidenceSource.GRAPH,
                    reference=f"{inv.clause_id}->{inv.missing_target}",
                    quote=f"Invalid reference from clause {inv.clause_id} to non-existent clause {inv.missing_target}.",
                    page_number=None,
                )
            ],
            suggested_redline=None,
            review_status=ReviewStatus.PENDING,
        )
        findings.append(finding)

    # 2. Dependency cycles
    for cycle in graph.cycles:
        clause_id = cycle[0] if cycle else "GRAPH"
        cycle_repr = " -> ".join(cycle)
        cycle_path = f"{cycle_repr} -> {cycle[0]}" if cycle else "GRAPH"
        finding = RiskFinding(
            finding_id=None,
            clause_id=clause_id,
            risk_level=RiskLevel.MEDIUM,
            risk_category=RiskCategory.OTHER,
            explanation=f"Circular dependency detected among clauses: {cycle_path}.",
            evidence=[
                Evidence(
                    source=EvidenceSource.GRAPH,
                    reference=cycle_repr,
                    quote=f"Circular dependency cycle: {cycle_repr}",
                    page_number=None,
                )
            ],
            suggested_redline=None,
            review_status=ReviewStatus.PENDING,
        )
        findings.append(finding)

    # Handle edge case: has_cycle True with empty cycles list
    if graph.has_cycle and not graph.cycles:
        findings.append(
            RiskFinding(
                finding_id=None,
                clause_id="GRAPH",
                risk_level=RiskLevel.MEDIUM,
                risk_category=RiskCategory.OTHER,
                explanation="Circular dependency detected in clause graph.",
                evidence=[
                    Evidence(
                        source=EvidenceSource.GRAPH,
                        reference="CYCLE",
                        quote="Circular dependency detected in clause graph.",
                        page_number=None,
                    )
                ],
                suggested_redline=None,
                review_status=ReviewStatus.PENDING,
            )
        )

    return findings

