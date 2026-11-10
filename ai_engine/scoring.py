"""
Risk scoring module.
Calculates deterministic contract risk scores from findings.
"""
from __future__ import annotations

import logging
from typing import Sequence

from shared.contracts import RiskFinding, RiskLevel

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS: dict[RiskLevel, float] = {
    RiskLevel.CRITICAL: 40.0,
    RiskLevel.HIGH: 25.0,
    RiskLevel.MEDIUM: 10.0,
    RiskLevel.LOW: 5.0,
}


def compute_risk_score(findings: Sequence[RiskFinding]) -> float:
    """
    Compute an aggregate document risk score from risk findings:
    CRITICAL: 40, HIGH: 25, MEDIUM: 10, LOW: 5.
    The score is capped at 100.0 and returned as a float.

    Args:
        findings: Sequence of RiskFinding instances.

    Returns:
        float: Calculated score between 0.0 and 100.0.
    """
    total = sum(SEVERITY_WEIGHTS.get(f.risk_level, 0.0) for f in findings)
    capped_score = float(min(100.0, max(0.0, total)))
    return capped_score

