"""
Tests for engine pipelines and end-to-end integration.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_engine import analyze_document, compare_documents
from doc_engine import parse_document
from graph_engine import build_graph
from shared.contracts import (
    AnalysisResult,
    ClauseGraph,
    ComparisonResult,
    ParsedDocument,
)
from shared.samples import sample_msa


def test_parse_document_returns_parsed_document_with_none_id_and_str_clauses(
    tmp_path: Path,
):
    """parse_document returns ParsedDocument with document_id None and all string clause_ids."""
    dummy_file = tmp_path / "sample_contract.pdf"
    dummy_file.write_text("Dummy contract content for parser test", encoding="utf-8")

    parsed = parse_document(str(dummy_file), "MSA")
    assert isinstance(parsed, ParsedDocument)
    assert parsed.document_id is None
    assert parsed.file_name == "sample_contract.pdf"
    assert len(parsed.clauses) > 0

    for clause in parsed.clauses:
        assert isinstance(clause.clause_id, str)
        assert len(clause.clause_id) > 0


def test_build_graph_on_sample_msa_detects_cycles_and_missing_reference():
    """build_graph on sample_msa gives has_cycle True and missing target 14.3."""
    msa_doc = sample_msa()
    graph = build_graph(msa_doc)

    assert isinstance(graph, ClauseGraph)
    assert graph.has_cycle is True
    # Verify cycle between 3.1 and 8.1
    flattened_cycle = [c for cycle in graph.cycles for c in cycle]
    assert "3.1" in flattened_cycle
    assert "8.1" in flattened_cycle

    # Verify missing reference 14.3
    missing_targets = [inv.missing_target for inv in graph.invalid_references]
    assert "14.3" in missing_targets


def test_analyze_document_with_graph_and_without_graph():
    """analyze_document must work both with a ClauseGraph and with None."""
    msa_doc = sample_msa()
    graph = build_graph(msa_doc)

    result_with_graph = analyze_document(msa_doc, graph=graph)
    assert isinstance(result_with_graph, AnalysisResult)
    assert result_with_graph.overall_risk_score >= 0
    assert len(result_with_graph.findings) > 0

    result_without_graph = analyze_document(msa_doc, graph=None)
    assert isinstance(result_without_graph, AnalysisResult)
    assert result_without_graph.overall_risk_score == 0.0
    assert len(result_without_graph.findings) == 0


def test_full_pipeline_msa_and_sow(tmp_path: Path):
    """Full pipeline execution from dummy files through to AnalysisResult and ComparisonResult."""
    dummy_msa = tmp_path / "contract_master.pdf"
    dummy_msa.write_text("Master agreement dummy content", encoding="utf-8")

    dummy_sow = tmp_path / "statement_of_work.docx"
    dummy_sow.write_text("SOW dummy content", encoding="utf-8")

    parsed_msa = parse_document(str(dummy_msa), "MSA")
    parsed_sow = parse_document(str(dummy_sow), "SOW")

    msa_graph = build_graph(parsed_msa)
    sow_graph = build_graph(parsed_sow)

    msa_analysis = analyze_document(parsed_msa, graph=msa_graph)
    sow_analysis = analyze_document(parsed_sow, graph=sow_graph)

    comparison = compare_documents(parsed_msa, parsed_sow)

    assert isinstance(msa_analysis, AnalysisResult)
    assert isinstance(sow_analysis, AnalysisResult)
    assert isinstance(comparison, ComparisonResult)

