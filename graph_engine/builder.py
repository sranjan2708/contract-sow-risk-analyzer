"""
Graph engine module for building clause dependency graphs.
STUB — owner replaces body, keep signature.
"""
from __future__ import annotations

import networkx as nx

from shared.contracts import (
    ClauseGraph,
    GraphEdge,
    GraphNode,
    InvalidReference,
    ParsedDocument,
    RelationType,
)


def build_graph(document: ParsedDocument) -> ClauseGraph:
    """
    Build a directed clause dependency graph from a parsed contract document.

    STUB — owner replaces body, keep signature.

    Args:
        document: Validated ParsedDocument contract model.

    Returns:
        ClauseGraph: Validated clause graph with detected edges, cycles, and invalid references.
    """
    g = nx.DiGraph()
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    invalid_references: list[InvalidReference] = []

    for clause in document.clauses:
        nodes.append(GraphNode(clause_id=clause.clause_id, title=clause.title))
        g.add_node(clause.clause_id)

    existing_ids = {clause.clause_id for clause in document.clauses}

    for clause in document.clauses:
        for ref in clause.references:
            if ref in existing_ids:
                g.add_edge(clause.clause_id, ref)
                edges.append(
                    GraphEdge(
                        source=clause.clause_id,
                        target=ref,
                        relation=RelationType.REFERENCES,
                    )
                )
            else:
                invalid_references.append(
                    InvalidReference(
                        clause_id=clause.clause_id,
                        missing_target=ref,
                    )
                )

    raw_cycles = list(nx.simple_cycles(g))
    cycles: list[list[str]] = [list(c) for c in raw_cycles]
    has_cycle = len(cycles) > 0

    return ClauseGraph(
        document_id=document.document_id,
        nodes=nodes,
        edges=edges,
        has_cycle=has_cycle,
        cycles=cycles,
        invalid_references=invalid_references,
    )

