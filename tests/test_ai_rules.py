"""
Unit and integration tests for AI engine deterministic playbook rules and risk scoring.
"""
from __future__ import annotations

import pytest

from ai_engine import analyze_document
from ai_engine.playbook_loader import (
    PlaybookRule,
    get_rule_by_id,
    get_rules_by_category,
    load_playbook,
)
from ai_engine.rules import (
    check_clause_rules,
    check_liability_clause,
    check_payment_clause,
    check_termination_clause,
    extract_notice_days,
    extract_payment_days,
)
from ai_engine.scoring import compute_risk_score
from graph_engine import build_graph
from shared.contracts import (
    AnalysisResult,
    Clause,
    EvidenceSource,
    ReviewStatus,
    RiskCategory,
    RiskFinding,
    RiskLevel,
)
from shared.samples import sample_msa, sample_sow


# ============================================================================
# 1. Playbook Loader Tests
# ============================================================================
def test_playbook_loader_loads_rules_and_caches():
    """playbook_loader loads playbook.json and caches the result."""
    rules = load_playbook()
    assert len(rules) == 3
    for r in rules:
        assert isinstance(r, PlaybookRule)
        assert r.rule_id in {"PB-LIAB-01", "PB-PAY-01", "PB-TERM-01"}
        assert len(r.fallback_language) > 0

    # Test cache returns identical object
    rules_again = load_playbook()
    assert rules is rules_again


def test_playbook_loader_get_by_id_and_category():
    """get_rule_by_id and get_rules_by_category return expected rules."""
    liab = get_rule_by_id("PB-LIAB-01")
    assert liab is not None
    assert liab.risk_category == RiskCategory.LIABILITY
    assert liab.risk_level_if_violated == RiskLevel.CRITICAL

    pay = get_rule_by_id("PB-PAY-01")
    assert pay is not None
    assert pay.risk_category == RiskCategory.PAYMENT
    assert pay.risk_level_if_violated == RiskLevel.HIGH

    term = get_rule_by_id("PB-TERM-01")
    assert term is not None
    assert term.risk_category == RiskCategory.TERMINATION
    assert term.risk_level_if_violated == RiskLevel.MEDIUM

    assert get_rule_by_id("NON_EXISTENT") is None

    # Test get_rules_by_category with enum and string
    cat_rules = get_rules_by_category(RiskCategory.LIABILITY)
    assert len(cat_rules) == 1
    assert cat_rules[0].rule_id == "PB-LIAB-01"

    cat_rules_str = get_rules_by_category("payment")
    assert len(cat_rules_str) == 1
    assert cat_rules_str[0].rule_id == "PB-PAY-01"

    assert get_rules_by_category("UNKNOWN") == []


# ============================================================================
# 2. Day Extraction Unit Tests
# ============================================================================
@pytest.mark.parametrize(
    ("input_text", "expected_days"),
    [
        ("(60) days", 60),
        ("60 days", 60),
        ("net 60", 60),
        ("Net 60", 60),
        ("net-60", 60),
        ("within thirty (30) days of receipt", 30),
        ("Customer shall pay each invoice within sixty (60) days of receipt.", 60),
        ("net 30", 30),
        ("Net 30", 30),
        ("net 90", 90),
        ("within 45 calendar days", 45),
        ("within 15 business days", 15),
        ("pay when paid", None),
        ("Supplier shall provide the Services described herein.", None),
    ],
)
def test_extract_payment_days(input_text: str, expected_days: int | None):
    """extract_payment_days parses '(60) days', '60 days', 'net 60', etc."""
    assert extract_payment_days(input_text) == expected_days


@pytest.mark.parametrize(
    ("input_text", "expected_days"),
    [
        ("upon fifteen (15) days written notice", 15),
        ("upon 15 days notice", 15),
        ("immediately upon written notice", 0),
        ("immediate notice is required", 0),
        ("upon thirty (30) days notice", 30),
        ("no mention of notice", None),
    ],
)
def test_extract_notice_days(input_text: str, expected_days: int | None):
    """extract_notice_days extracts notice duration in days or 0 for immediate."""
    assert extract_notice_days(input_text) == expected_days


# ============================================================================
# 3. Scoring Unit Tests
# ============================================================================
def test_compute_risk_score_weights_and_cap():
    """compute_risk_score assigns correct weights and caps at 100.0."""
    # Empty
    assert compute_risk_score([]) == 0.0

    # Single levels: LOW 5, MEDIUM 10, HIGH 25, CRITICAL 40
    def make_dummy_finding(level: RiskLevel) -> RiskFinding:
        return RiskFinding(
            finding_id=None,
            clause_id="1.0",
            risk_level=level,
            risk_category=RiskCategory.OTHER,
            explanation="Test finding",
            evidence=[],
            suggested_redline=None,
            review_status=ReviewStatus.PENDING,
        )

    assert compute_risk_score([make_dummy_finding(RiskLevel.LOW)]) == 5.0
    assert compute_risk_score([make_dummy_finding(RiskLevel.MEDIUM)]) == 10.0
    assert compute_risk_score([make_dummy_finding(RiskLevel.HIGH)]) == 25.0
    assert compute_risk_score([make_dummy_finding(RiskLevel.CRITICAL)]) == 40.0

    # Additive combinations
    findings_50 = [
        make_dummy_finding(RiskLevel.CRITICAL),  # 40
        make_dummy_finding(RiskLevel.MEDIUM),    # 10
    ]
    assert compute_risk_score(findings_50) == 50.0

    findings_70 = [
        make_dummy_finding(RiskLevel.CRITICAL),  # 40
        make_dummy_finding(RiskLevel.MEDIUM),    # 10
        make_dummy_finding(RiskLevel.MEDIUM),    # 10
        make_dummy_finding(RiskLevel.MEDIUM),    # 10
    ]
    assert compute_risk_score(findings_70) == 70.0

    # Cap at 100.0: 3 CRITICAL = 120 -> 100.0
    findings_120 = [
        make_dummy_finding(RiskLevel.CRITICAL),
        make_dummy_finding(RiskLevel.CRITICAL),
        make_dummy_finding(RiskLevel.CRITICAL),
    ]
    score = compute_risk_score(findings_120)
    assert score == 100.0
    assert isinstance(score, float)

    # Extreme cap test
    findings_over = [make_dummy_finding(RiskLevel.CRITICAL) for _ in range(10)]
    assert compute_risk_score(findings_over) == 100.0


# ============================================================================
# 4. Sample MSA & SOW Analysis Tests
# ============================================================================
def test_sample_msa_analysis_without_graph():
    """
    On sample MSA without graph:
    - 8.1 LIABILITY CRITICAL
    - 11.2 TERMINATION MEDIUM
    - 5.1 NO finding (30 days compliant)
    - score == 50.0
    """
    msa_doc = sample_msa()
    result = analyze_document(msa_doc, graph=None)

    assert isinstance(result, AnalysisResult)
    assert result.document_id == msa_doc.document_id
    assert result.model_used == "playbook-rules-v1"
    assert result.overall_risk_score == 50.0

    findings_by_clause = {f.clause_id: f for f in result.findings}
    assert set(findings_by_clause.keys()) == {"8.1", "11.2"}

    # Clause 5.1 has NO finding
    assert "5.1" not in findings_by_clause

    # Clause 8.1: LIABILITY CRITICAL
    f_8_1 = findings_by_clause["8.1"]
    assert f_8_1.finding_id is None
    assert f_8_1.risk_level == RiskLevel.CRITICAL
    assert f_8_1.risk_category == RiskCategory.LIABILITY
    assert f_8_1.review_status == ReviewStatus.PENDING
    assert f_8_1.suggested_redline is not None

    sources_8_1 = {ev.source for ev in f_8_1.evidence}
    assert sources_8_1 == {EvidenceSource.CLAUSE, EvidenceSource.PLAYBOOK}
    clause_ev_8_1 = next(ev for ev in f_8_1.evidence if ev.source == EvidenceSource.CLAUSE)
    assert clause_ev_8_1.reference == "8.1"
    assert clause_ev_8_1.page_number == 7
    assert "unlimited" in (clause_ev_8_1.quote or "").lower()

    pb_ev_8_1 = next(ev for ev in f_8_1.evidence if ev.source == EvidenceSource.PLAYBOOK)
    assert pb_ev_8_1.reference == "PB-LIAB-01"

    # Clause 11.2: TERMINATION MEDIUM
    f_11_2 = findings_by_clause["11.2"]
    assert f_11_2.finding_id is None
    assert f_11_2.risk_level == RiskLevel.MEDIUM
    assert f_11_2.risk_category == RiskCategory.TERMINATION
    assert f_11_2.review_status == ReviewStatus.PENDING
    assert f_11_2.suggested_redline is not None

    sources_11_2 = {ev.source for ev in f_11_2.evidence}
    assert sources_11_2 == {EvidenceSource.CLAUSE, EvidenceSource.PLAYBOOK}
    clause_ev_11_2 = next(ev for ev in f_11_2.evidence if ev.source == EvidenceSource.CLAUSE)
    assert clause_ev_11_2.reference == "11.2"
    assert clause_ev_11_2.page_number == 10

    pb_ev_11_2 = next(ev for ev in f_11_2.evidence if ev.source == EvidenceSource.PLAYBOOK)
    assert pb_ev_11_2.reference == "PB-TERM-01"

    # Summary string check
    assert "1 CRITICAL" in result.summary
    assert "1 MEDIUM" in result.summary


def test_sample_msa_analysis_with_graph():
    """
    On sample MSA with graph:
    Adds 11.2->14.3 invalid ref (MEDIUM) + cycle (MEDIUM) -> score 70.0.
    """
    msa_doc = sample_msa()
    graph = build_graph(msa_doc)

    result = analyze_document(msa_doc, graph=graph)
    assert isinstance(result, AnalysisResult)
    assert result.overall_risk_score == 70.0
    assert len(result.findings) == 4

    graph_findings = [
        f for f in result.findings
        if any(ev.source == EvidenceSource.GRAPH for ev in f.evidence)
    ]
    assert len(graph_findings) == 2

    # Check invalid reference finding
    inv_finding = next((f for f in graph_findings if "14.3" in f.explanation), None)
    assert inv_finding is not None
    assert inv_finding.clause_id == "11.2"
    assert inv_finding.risk_level == RiskLevel.MEDIUM
    assert inv_finding.risk_category == RiskCategory.OTHER
    assert inv_finding.suggested_redline is None
    assert inv_finding.finding_id is None
    assert inv_finding.review_status == ReviewStatus.PENDING

    # Check cycle finding
    cycle_finding = next((f for f in graph_findings if "Circular dependency" in f.explanation), None)
    assert cycle_finding is not None
    assert cycle_finding.risk_level == RiskLevel.MEDIUM
    assert cycle_finding.risk_category == RiskCategory.OTHER
    assert "3.1" in cycle_finding.explanation
    assert "8.1" in cycle_finding.explanation
    assert cycle_finding.suggested_redline is None
    assert cycle_finding.finding_id is None
    assert cycle_finding.review_status == ReviewStatus.PENDING


def test_sample_sow_analysis():
    """
    On sample SOW:
    Clause 4.1 Fees and Payment -> PAYMENT HIGH (60 days > 30).
    Clause 2.1 -> NO finding.
    Overall risk score == 25.0.
    """
    sow_doc = sample_sow()
    result = analyze_document(sow_doc, graph=None)

    assert isinstance(result, AnalysisResult)
    assert result.overall_risk_score == 25.0
    assert len(result.findings) == 1

    finding = result.findings[0]
    assert finding.finding_id is None
    assert finding.clause_id == "4.1"
    assert finding.risk_level == RiskLevel.HIGH
    assert finding.risk_category == RiskCategory.PAYMENT
    assert finding.review_status == ReviewStatus.PENDING
    assert "60" in finding.explanation
    assert finding.suggested_redline is not None

    sources = {ev.source for ev in finding.evidence}
    assert sources == {EvidenceSource.CLAUSE, EvidenceSource.PLAYBOOK}
    clause_ev = next(ev for ev in finding.evidence if ev.source == EvidenceSource.CLAUSE)
    assert clause_ev.reference == "4.1"
    assert clause_ev.page_number == 3

    pb_ev = next(ev for ev in finding.evidence if ev.source == EvidenceSource.PLAYBOOK)
    assert pb_ev.reference == "PB-PAY-01"


# ============================================================================
# 5. Additional Edge-Case Rule Unit Tests
# ============================================================================
def test_pay_when_paid_triggers_high_finding():
    """Clause containing 'pay when paid' triggers a HIGH PAYMENT finding."""
    clause = Clause(
        clause_id="9.2",
        title="Subcontractor Compensation",
        text="Supplier will disburse compensation under pay when paid principles.",
        page_number=12,
    )
    findings = check_payment_clause(clause)
    assert len(findings) == 1
    assert findings[0].risk_level == RiskLevel.HIGH
    assert findings[0].risk_category == RiskCategory.PAYMENT
    assert "pay when paid" in findings[0].explanation.lower()


def test_immediate_termination_triggers_medium_finding():
    """Termination for convenience immediately upon notice triggers MEDIUM."""
    clause = Clause(
        clause_id="12.1",
        title="Termination for Convenience",
        text="Customer may terminate this Agreement for convenience immediately upon written notice.",
        page_number=15,
    )
    findings = check_termination_clause(clause)
    assert len(findings) == 1
    assert findings[0].risk_level == RiskLevel.MEDIUM
    assert findings[0].risk_category == RiskCategory.TERMINATION
    assert "immediate" in findings[0].explanation.lower()


def test_termination_convenience_30_days_compliant():
    """Termination for convenience with 30 days notice produces NO finding."""
    clause = Clause(
        clause_id="12.2",
        title="Termination for Convenience",
        text="Either party may terminate for convenience upon thirty (30) days prior written notice.",
        page_number=15,
    )
    findings = check_termination_clause(clause)
    assert findings == []


def test_liability_compliant_capped():
    """Liability clause with a standard cap produces NO finding."""
    clause = Clause(
        clause_id="8.2",
        title="Limitation of Liability",
        text="Each party's aggregate liability shall be limited to the total fees paid under this SOW.",
        page_number=8,
    )
    findings = check_liability_clause(clause)
    assert findings == []

