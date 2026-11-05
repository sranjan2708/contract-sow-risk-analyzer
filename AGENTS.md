# AGENTS.md — Development Rules for AI Agents and Human Developers

## 1. Project
Contract & SOW Risk Analyzer is a dual-developer hackathon application designed to ingest Master Services Agreements (MSAs) and Statements of Work (SOWs), parse individual clauses, map cross-clause dependencies into directed graphs, flag risk exposure against a legal playbook, detect inter-document contradictions (e.g. payment terms, liability caps), suggest surgical redlines, and provide a full human-in-the-loop review audit trail.

## 2. Ownership & Boundaries
Two developers collaborate on this project using different AI assistants. Each agent must strictly operate within its owner's boundaries.

| Domain | Assigned Developer | Folders Owned |
| :--- | :--- | :--- |
| **Backend & AI Engine** | **Sudhansu** | `backend/`, `ai_engine/` |
| **Frontend, Parser & Graph** | **Pratyush** | `frontend/`, `doc_engine/`, `graph_engine/` |
| **Shared Contracts & Governance** | **Both** | `shared/`, `docs/`, `tests/`, `.github/` |

> **STRICT ISOLATION RULE**:
> - An AI working for **Sudhansu** must NOT modify `doc_engine/`, `graph_engine/`, or `frontend/`.
> - An AI working for **Pratyush** must NOT modify `backend/` or `ai_engine/`.
> - Request necessary changes from the other developer in the Pull Request description instead of making cross-boundary edits.

## 3. Tech Stack: Approved vs Forbidden

| Component | Approved ("Use") | Strictly Forbidden ("Never Use") |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.11, Node 20 LTS | Python <3.11, TypeScript (plain JS only) |
| **Web Framework** | FastAPI + Uvicorn | Flask, Django, Tornado |
| **Validation** | Pydantic v2 (Strict BaseModel) | Marshmallow, Pydantic v1 |
| **Database & SQL** | MySQL 8, PyMySQL with raw parameterized `%s` SQL | SQLAlchemy, ORMs, raw string formatting / f-string SQL |
| **Auth** | JWT via `python-jose` + `passlib[bcrypt]` | Session cookies, external OAuth daemons |
| **Document Processing** | PyMuPDF, python-docx, pytesseract | pdfplumber, PyPDF2, textract |
| **Graph Construction** | NetworkX | Neo4j, graph-tool, igraph |
| **Embeddings & Vector** | sentence-transformers (`all-MiniLM-L6-v2`), ChromaDB | FAISS, Pinecone, Weaviate, Milvus |
| **LLM Provider Calls** | Strictly inside `ai_engine/llm.py` via `LLM_PROVIDER` | Direct OpenAI/Anthropic/Gemini SDK calls outside `llm.py` |
| **Frontend Framework** | React 18 + Vite (JavaScript) + plain CSS | Next.js, Remix, Tailwind (unless team agrees), styled-components |
| **HTTP Client** | `httpx` (Python), standard `fetch` via `frontend/src/api/client.js` | `requests` (Python), `axios` scattered in UI components |
| **Testing** | `pytest` + `httpx.ASGITransport` / `TestClient` | `unittest`, manual mocking scripts |

*Note: Adding any new dependency requires explicit written justification in the PR.*

## 4. Frozen Contracts & Function Signatures
All data structures passing module boundaries are frozen in `shared/contracts.py`.

### The 3 Core Contracts
1. **Contract 1: ParsedDocument** (`doc_engine` -> `backend` / `ai_engine`)
2. **Contract 2: ClauseGraph** (`graph_engine` -> `backend` / `ai_engine`)
3. **Contract 3: API Responses** (`backend` -> `frontend`, see `docs/api_contracts.md`)

### The 4 Frozen Function Signatures
```python
# doc_engine/__init__.py
def parse_document(file_path: str, document_type: str) -> ParsedDocument: ...

# graph_engine/__init__.py
def build_graph(document: ParsedDocument) -> ClauseGraph: ...

# ai_engine/__init__.py
def analyze_document(document: ParsedDocument, graph: ClauseGraph | None = None) -> AnalysisResult: ...
def compare_documents(msa: ParsedDocument, sow: ParsedDocument) -> ComparisonResult: ...

# ai_engine/llm.py
def complete(prompt: str, system: str = "", max_tokens: int = 800) -> str: ...
```

### Data Integrity Rules
- Import models ONLY from `shared.contracts`. Never redefine contract classes.
- Public functions MUST return validated Pydantic model instances, never raw `dict`s.
- All JSON and schema keys are strictly `snake_case`.
- All Enum values are strictly `UPPERCASE` strings.
- `clause_id` is always a string (e.g. `"3.1"`, `"8.1"`). Never an integer.
- `page_number` starts at 1 (`ge=1`).
- `document_id` is an integer assigned by the backend database; parsers must initialize it as `None`.
- Missing optional values must be explicit `None` / `null`, never empty strings `""` or `"N/A"`.

## 5. Code & Architectural Rules
1. **Preserve Structure**: Do not invent new folders or restructure working code.
2. **Safe SQL**: Parameterize all queries using `%s` placeholders. Never interpolate strings or concatenate variables.
3. **Transactions**: Any operation writing across multiple tables must execute within an atomic transaction.
4. **Configuration**: Read settings solely through `backend/app/config.py`. Never access `os.environ` directly in feature modules.
5. **No Destructive Edits**: Never delete or rename existing endpoints, database columns, or function signatures.
6. **Code Quality**: Include complete type annotations and docstrings for all functions.
7. **Logging**: Use Python's standard `logging` module. Never use `print()` statements.
8. **Frontend Network Isolation**: Components must never call `window.fetch`. All calls route through `src/api/endpoints.js` -> `src/api/client.js`.

## 6. Git Workflow
- **Branch Protection**: Never commit or push directly to `main` or `develop`.
- **Branch Naming**: Branch from `develop` using `feature/<owner>-<task>` (e.g. `feature/sudhansu-auth-routes`, `feature/pratyush-pdf-ocr`).
- **Session Start**: Always start each working session with:
  ```bash
  git checkout develop && git pull origin develop
  ```
- **Commit Format**: Follow Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `test(scope): ...`, `docs(scope): ...`.
- **Pull Requests**: Open PR into `develop`. Requires green CI checks and review approval from the other developer.
- **Forbidden Commits**: Never commit `.env`, `venv/`, `node_modules/`, `uploads/`, or `chroma_data/`.

## 7. Contract-Change Process
Contracts are immutable during standard feature development. If an update is required:
1. Open a GitHub Issue titled `CONTRACT CHANGE: <description>`.
2. Both Sudhansu and Pratyush must explicitly approve the proposal.
3. Exactly **ONE atomic PR** must be created that updates:
   - `shared/contracts.py`
   - `shared/samples/*.json` and `shared/samples/__init__.py`
   - `docs/api_contracts.md`
   - `frontend/src/api/endpoints.js`
   - All affected tests across `tests/`
4. Prefer adding optional fields (`Optional[T] = None`). Never rename or delete active fields.
5. Both developers pull `develop` immediately upon merge before resuming other tasks.

## 8. Before You Say "Done" Checklist
Every AI agent must verify these 6 points before declaring any task complete:
- [ ] 1. Files modified belong strictly to the owner's assigned directory.
- [ ] 2. `shared/contracts.py` and frozen engine signatures remain untouched.
- [ ] 3. No unauthorized dependencies or libraries were introduced.
- [ ] 4. All database queries use raw parameterized SQL with `%s`.
- [ ] 5. Pure engine isolation holds (zero forbidden imports across engines/backend).
- [ ] 6. Test suite runs and passes 100% green via `pytest`.
