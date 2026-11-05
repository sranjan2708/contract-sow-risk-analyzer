# Contract & SOW Risk Analyzer

An automated contract intelligence system for analyzing Master Services Agreements (MSAs) and Statements of Work (SOWs).
The system parses complex legal clauses, builds directed dependency graphs, checks contract terms against a standardized legal risk playbook, flags inter-document contradictions (e.g., conflicting liability caps, divergent payment terms), suggests surgical redlines, and enables legal professionals to review and approve findings with a complete audit trail.

---

## 1. Team & Ownership

| Developer | Core Domain Responsibilities | Primary Folders |
| :--- | :--- | :--- |
| **Sudhansu** | Backend architecture, FastAPI REST APIs, MySQL persistence, auth, and AI engine (ChromaDB, embeddings, playbook evaluation, contradiction detection, redline generation). | `backend/`, `ai_engine/` |
| **Pratyush** | Frontend UI (React + Vite), document ingestion (PyMuPDF, python-docx, OCR), and graph construction (NetworkX dependency resolution). | `frontend/`, `doc_engine/`, `graph_engine/` |
| **Both** | Frozen contracts, sample datasets, test suite, and architectural documentation. | `shared/`, `docs/`, `tests/` |

---

## 2. Fixed Tech Stack

- **Runtime & Language**: Python 3.11, Node.js 20 LTS
- **Backend API**: FastAPI, Uvicorn, Pydantic v2
- **Database**: MySQL 8 (InnoDB, utf8mb4), PyMySQL using raw parameterized SQL (NO ORM / NO SQLAlchemy)
- **Authentication**: JWT via `python-jose` and `passlib[bcrypt]`
- **Document Processing**: PyMuPDF (`fitz`), `python-docx`, `pytesseract`
- **Graph Engine**: NetworkX (`DiGraph`)
- **AI & Vector Engine**: `sentence-transformers` (`all-MiniLM-L6-v2`), ChromaDB, modular LLM interface (`ai_engine/llm.py`)
- **Frontend**: React 18, Vite, JavaScript, plain CSS
- **Testing & CI**: `pytest`, `httpx`, GitHub Actions

---

## 3. Repository Layout

```
contract-risk-analyzer/
  AGENTS.md                         # Critical AI & developer rules
  README.md                         # Project documentation and setup guide
  CONTRIBUTING.md                   # Collaboration and git guidelines
  .gitignore                        # Ignored files (venv, secrets, cache)
  .gitattributes                    # Line ending and binary file configuration
  .env.example                      # Sample environment variables
  requirements.txt                  # Pinned Python dependencies
  pytest.ini                        # Pytest configuration
  .agents/rules/project-rules.md    # Compact rule summary for AI agents
  .github/workflows/ci.yml          # GitHub Actions CI workflow
  .github/pull_request_template.md  # PR template with compliance checklist
  .github/CODEOWNERS                # Domain ownership definitions
  .vscode/settings.json             # Recommended editor settings
  shared/                           # Frozen data models and samples
    contracts.py                    # Frozen Pydantic models (Contracts 1, 2, 3)
    samples/                        # Validated sample contracts and graphs
  backend/                          # FastAPI REST application
    app/                            # API routes, configuration, database connector
    migrations/                     # MySQL migration scripts
  doc_engine/                       # Document parsing engine (PDF/DOCX/OCR)
  graph_engine/                     # Dependency graphing engine (NetworkX)
  ai_engine/                        # Playbook analysis & LLM abstraction
    playbook/                       # Legal playbook rules JSON
  frontend/                         # React + Vite application
    src/api/                        # Central API client and endpoints
  docs/                             # Architectural and database specifications
  tests/                            # Integration, unit, contract, and boundary tests
```

---

## 4. Prerequisites

Before installing the project, ensure you have:
1. **Git** (version 2.30+)
2. **Python 3.11**
3. **Node.js 20 LTS** & npm
4. **MySQL 8 Server**
5. **Tesseract OCR** (Required for OCR on scanned PDFs by Pratyush)
6. **VS Code** (or Antigravity IDE)
7. **Postman** or browser for REST endpoint testing

---

## 5. Local Setup Guide

### Windows (PowerShell)
```powershell
# 1. Clone repository and checkout develop
git clone <REPO_URL>
cd contract-risk-analyzer
git checkout develop

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
copy .env.example .env

# 5. Run test suite
pytest
```

### macOS / Linux (Bash)
```bash
# 1. Clone repository and checkout develop
git clone <REPO_URL>
cd contract-risk-analyzer
git checkout develop

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Run test suite
pytest
```

---

## 6. MySQL Database Setup

Log in to your local MySQL 8 instance using an admin account:

```sql
-- Create database with utf8mb4 encoding
CREATE DATABASE contract_risk_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create dedicated application user
CREATE USER 'cra_user'@'localhost' IDENTIFIED BY 'cra_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON contract_risk_analyzer.* TO 'cra_user'@'localhost';
FLUSH PRIVILEGES;
```

Run the initial schema migration:
```bash
mysql -u cra_user -p contract_risk_analyzer < backend/migrations/001_initial_schema.sql
```

*(Note: In `MOCK_MODE=true`, a running MySQL database is not required to run tests or explore the mock API).*

---

## 7. Running the Application

### Start the Backend API
From the repository root:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Start the Frontend Dev Server
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Frontend application URL: [http://localhost:5173](http://localhost:5173)

---

## 8. Development Rules & Governance

Before making any changes, review the following essential documentation:
- **[AGENTS.md](file:///d:/Contract%20&%20SOW%20Risk%20Analyzer/AGENTS.md)**: Strict ownership boundaries, frozen contracts, and banned libraries.
- **[CONTRIBUTING.md](file:///d:/Contract%20&%20SOW%20Risk%20Analyzer/CONTRIBUTING.md)**: Branching, merging, and collaboration workflows.
- **[docs/AI_SESSION_PROMPT.md](file:///d:/Contract%20&%20SOW%20Risk%20Analyzer/docs/AI_SESSION_PROMPT.md)**: Copy-paste starter prompts for AI sessions.
- **[docs/api_contracts.md](file:///d:/Contract%20&%20SOW%20Risk%20Analyzer/docs/api_contracts.md)**: Contract 3 REST endpoint specification.
- **[docs/architecture.md](file:///d:/Contract%20&%20SOW%20Risk%20Analyzer/docs/architecture.md)**: Component boundary isolation and architectural flows.

