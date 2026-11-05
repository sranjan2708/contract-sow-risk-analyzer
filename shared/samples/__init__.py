"""
Sample data loaders returning validated Pydantic contract models.
"""
from __future__ import annotations

import json
from pathlib import Path

from shared.contracts import (
    AnalysisResult,
    ClauseGraph,
    ComparisonResult,
    ParsedDocument,
)

_SAMPLES_DIR = Path(__file__).resolve().parent


def _read_json(file_name: str) -> dict:
    file_path = _SAMPLES_DIR / file_name
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sample_msa() -> ParsedDocument:
    """Load and return the validated sample MSA ParsedDocument model."""
    data = _read_json("msa_parsed.json")
    return ParsedDocument.model_validate(data)


def sample_sow() -> ParsedDocument:
    """Load and return the validated sample SOW ParsedDocument model."""
    data = _read_json("sow_parsed.json")
    return ParsedDocument.model_validate(data)


def sample_graph() -> ClauseGraph:
    """Load and return the validated sample ClauseGraph model."""
    data = _read_json("msa_graph.json")
    return ClauseGraph.model_validate(data)


def sample_analysis() -> AnalysisResult:
    """Load and return the validated sample AnalysisResult model."""
    data = _read_json("msa_analysis.json")
    return AnalysisResult.model_validate(data)


def sample_comparison() -> ComparisonResult:
    """Load and return the validated sample ComparisonResult model."""
    data = _read_json("comparison.json")
    return ComparisonResult.model_validate(data)


__all__ = [
    "sample_msa",
    "sample_sow",
    "sample_graph",
    "sample_analysis",
    "sample_comparison",
]
