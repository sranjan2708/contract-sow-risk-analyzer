# Architecture & System Design

## 1. Overview
The Contract & SOW Risk Analyzer is built around a single central FastAPI backend application that orchestrates three pure, decoupled functional engines:
- **`doc_engine`**: Extracts structured clauses from PDF/DOCX contracts.
- **`graph_engine`**: Builds directed dependency graphs and evaluates structural clause relationships.
- **`ai_engine`**: Executes playbook rules, detects contradictions, and formulates redlines.

```
                              +-------------------------+
                              |   Frontend (React+Vite) |
                              +-------------------------+
                                           | HTTP / REST (Contract 3)
                                           v
                              +-------------------------+
                              |     FastAPI Backend     |
                              +-------------------------+
                                 |         |         |
                  Contract 1    |         |         | Contract 1 & 2
                  (Parse)       v         |         v (Analyze / Compare)
        +--------------------------+      |      +--------------------------+
        |        doc_engine        |      |      |        ai_engine         |
        | (Pure: PDF/DOCX Parsing) |      |      |  (Playbook, RAG, Rules)  |
        +--------------------------+      |      +--------------------------+
                                          |                    |
                            Contract 1    |                    v
                            (Graph Build) v            +----------------+
                        +--------------------------+   |   ai_engine/   |
                        |       graph_engine       |   |     llm.py     |
                        | (Pure: NetworkX DiGraph) |   +----------------+
                        +--------------------------+           |
                                                               v
                                                      [ LLM Providers ]
                                                    (OpenAI / Gemini / Stub)
```

## 2. Component Boundaries & Isolation Table

| Engine | Inputs | Outputs | Permitted Imports | Strictly Forbidden Imports |
| :--- | :--- | :--- | :--- | :--- |
| **`doc_engine`** | File path (`str`), document type (`str`) | `ParsedDocument` | Standard library, `shared.contracts`, PyMuPDF, python-docx, pytesseract | `backend`, `fastapi`, `pymysql`, `sqlalchemy`, `graph_engine`, `ai_engine` |
| **`graph_engine`** | `ParsedDocument` | `ClauseGraph` | Standard library, `shared.contracts`, `networkx` | `backend`, `fastapi`, `pymysql`, `sqlalchemy`, `doc_engine`, `ai_engine` |
| **`ai_engine`** | `ParsedDocument`, optional `ClauseGraph` | `AnalysisResult`, `ComparisonResult` | Standard library, `shared.contracts`, sentence-transformers, chromadb, `ai_engine.llm` | `backend`, `fastapi`, `pymysql`, `sqlalchemy`, `doc_engine`, `graph_engine` |
| **`backend`** | HTTP requests, File uploads | API JSON Responses (Contract 3) | `shared.contracts`, all 3 engines, `fastapi`, `pymysql`, `passlib`, `jose` | `sqlalchemy` (Raw SQL only), frontend code |

## 3. Core Architectural Invariants
1. **Database Access Exclusivity**: ONLY `backend/` connects to the MySQL database. Engines never touch the database or hold DB connections.
2. **LLM Invocation Exclusivity**: ONLY `ai_engine/llm.py` performs LLM completion calls. No external SDK calls are permitted outside this module.
3. **Data Model Immutability**: All inter-module communication is typed using immutable models from `shared/contracts.py`.

## 4. End-to-End Orchestration Flows

### Analysis Flow (Single Document)
```mermaid
sequenceDiagram
    autonumber
    actor User as Legal Reviewer
    participant Frontend
    participant Backend as FastAPI Backend
    participant DocEngine as doc_engine
    participant GraphEngine as graph_engine
    participant AIEngine as ai_engine
    participant DB as MySQL DB

    User->>Frontend: Upload MSA/SOW Document
    Frontend->>Backend: POST /api/v1/documents
    Backend->>Backend: Save file to uploads/
    Backend->>DocEngine: parse_document(file_path, type)
    DocEngine-->>Backend: ParsedDocument
    Backend->>GraphEngine: build_graph(parsed_doc)
    GraphEngine-->>Backend: ClauseGraph
    Backend->>DB: Store Document, Clauses, Graph, Audit Log
    Backend-->>Frontend: DocumentOut (201 Created)

    User->>Frontend: Request Analysis
    Frontend->>Backend: POST /api/v1/documents/{id}/analyze
    Backend->>DB: Load ParsedDocument & ClauseGraph
    Backend->>AIEngine: analyze_document(parsed_doc, graph)
    AIEngine-->>Backend: AnalysisResult
    Backend->>DB: Persist Findings, Score, Audit Log
    Backend-->>Frontend: AnalysisResult (200 OK)
```

### Comparison Flow (MSA vs SOW)
```mermaid
sequenceDiagram
    autonumber
    actor User as Legal Reviewer
    participant Frontend
    participant Backend as FastAPI Backend
    participant AIEngine as ai_engine
    participant DB as MySQL DB

    User->>Frontend: Select MSA and SOW to compare
    Frontend->>Backend: POST /api/v1/compare {msa_id, sow_id}
    Backend->>DB: Load clauses for MSA & SOW
    Backend->>AIEngine: compare_documents(msa_doc, sow_doc)
    AIEngine-->>Backend: ComparisonResult (Contradictions)
    Backend->>DB: Persist Comparison & Contradictions
    Backend-->>Frontend: ComparisonResult (200 OK)
```

