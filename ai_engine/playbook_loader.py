"""
Playbook rule loader and query interface.
Loads playbook.json once and provides lookups by rule_id and category.
"""
from __future__ import annotations

from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict

from shared.contracts import RiskCategory, RiskLevel

logger = logging.getLogger(__name__)

PLAYBOOK_PATH = Path(__file__).resolve().parent / "playbook" / "playbook.json"


class PlaybookRule(BaseModel):
    """Playbook rule definition loaded from playbook.json."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    risk_category: RiskCategory
    standard: str
    red_flags: list[str]
    risk_level_if_violated: RiskLevel
    fallback_language: str


@lru_cache(maxsize=1)
def load_playbook(path_str: Optional[str] = None) -> list[PlaybookRule]:
    """
    Load playbook rules from JSON once and cache the result.

    Args:
        path_str: Optional file path string override for the playbook JSON.

    Returns:
        List of validated PlaybookRule instances.
    """
    path = Path(path_str) if path_str else PLAYBOOK_PATH
    logger.info("Loading playbook rules from %s", path)
    with path.open("r", encoding="utf-8") as f:
        raw_rules = json.load(f)

    rules = [PlaybookRule.model_validate(r) for r in raw_rules]
    return rules


def get_rule_by_id(rule_id: str, path_str: Optional[str] = None) -> Optional[PlaybookRule]:
    """
    Lookup a playbook rule by its unique rule_id.

    Args:
        rule_id: Rule identifier, e.g. 'PB-LIAB-01'.
        path_str: Optional file path string override.

    Returns:
        Matching PlaybookRule or None if not found.
    """
    rules = load_playbook(path_str)
    for rule in rules:
        if rule.rule_id == rule_id:
            return rule
    return None


def get_rules_by_category(
    category: Union[RiskCategory, str], path_str: Optional[str] = None
) -> list[PlaybookRule]:
    """
    Return all playbook rules belonging to the specified risk category.

    Args:
        category: RiskCategory enum or string (case-insensitive).
        path_str: Optional file path string override.

    Returns:
        List of matching PlaybookRule instances.
    """
    cat_str = category.value if isinstance(category, RiskCategory) else str(category).upper()
    rules = load_playbook(path_str)
    return [r for r in rules if r.risk_category.value == cat_str]

