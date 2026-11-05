"""
Tests for shared contracts and JSON sample models.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Type

import pytest
from pydantic import BaseModel, ValidationError

from shared.contracts import (
    AnalysisResult,
    Clause,
    ClauseGraph,
    ComparisonResult,
    ParsedDocument,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / "shared" / "samples"


@pytest.mark.parametrize(
    "file_name,model_cls",
    [
        ("msa_parsed.json", ParsedDocument),
        ("sow_parsed.json", ParsedDocument),
        ("msa_graph.json", ClauseGraph),
        ("msa_analysis.json", AnalysisResult),
        ("comparison.json", ComparisonResult),
    ],
)
def test_samples_validate_against_models(file_name: str, model_cls: Type[BaseModel]):
    """Every sample JSON must cleanly validate against its corresponding contract model."""
    sample_path = SAMPLES_DIR / file_name
    assert sample_path.exists(), f"Sample file {file_name} missing"
    with sample_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    validated = model_cls.model_validate(data)
    assert validated is not None


def test_unknown_key_clause_id_camel_case_rejected():
    """Models must forbid extra keys such as camelCase 'clauseId'."""
    with pytest.raises(ValidationError):
        Clause.model_validate(
            {
                "clause_id": "1.1",
                "clauseId": "1.1",
                "text": "This clause has an invalid duplicate camelCase field.",
                "page_number": 1,
            }
        )


def test_int_clause_id_rejected():
    """Clause clause_id must strictly be a string, not an integer."""
    with pytest.raises(ValidationError):
        Clause.model_validate(
            {
                "clause_id": 101,
                "text": "Clause with integer clause_id instead of string.",
                "page_number": 1,
            }
        )
