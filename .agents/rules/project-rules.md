# Project Hard Rules

Always read and follow @AGENTS.md before making any changes.

1. **Strict Ownership**: Never modify directories outside your owner's domain (Sudhansu: `backend/`, `ai_engine/`; Pratyush: `frontend/`, `doc_engine/`, `graph_engine/`).
2. **Never Edit Shared Alone**: Do not modify `shared/contracts.py` or public contracts without an agreed `CONTRACT CHANGE` issue and joint approval.
3. **Frozen Public Signatures**: Pure engine function signatures (`parse_document`, `build_graph`, `analyze_document`, `compare_documents`, `complete`) must never be altered.
4. **Approved Tech Stack Only**: Stick strictly to the approved tech stack in AGENTS.md (no SQLAlchemy, no ORM, no unauthorized libraries).
5. **Raw Parameterized SQL**: All database operations must use raw PyMySQL with `%s` parameters; string formatting or f-strings in queries are strictly forbidden.
6. **Import Contracts Directly**: Import models only from `shared.contracts` and return validated Pydantic instances rather than dictionaries.
7. **Green Test Suite**: Always run and pass `pytest` before declaring any task complete or committing changes.
8. **Feature Branches Only**: Never commit directly to `main` or `develop`; always create a feature branch (`feature/<owner>-<task>`) from updated `develop`.

