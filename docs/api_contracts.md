# API Contracts (Contract 3 Specification)

All client-server communications between the React frontend and FastAPI backend must strictly adhere to the contracts defined below.

## 1. Global API Rules
1. **Naming Convention**: All JSON field names MUST use `snake_case`. CamelCase keys will trigger validation failures.
2. **Enum Formatting**: All enum string literals MUST be in `UPPERCASE` (e.g. `"MSA"`, `"CRITICAL"`, `"PENDING"`).
3. **Date/Time Standard**: All timestamps must be serialized in ISO-8601 UTC format (e.g. `"2026-11-01T10:00:00Z"`).
4. **Standard Error Schema**: All HTTP 4xx and 5xx errors return a JSON object with a single `detail` field:
   ```json
   {
     "detail": "Descriptive human-readable error explanation"
   }
   ```
5. **Identifier Types**:
   - `document_id`, `finding_id`, `contradiction_id`, `user_id`: Integers (`int`).
   - `clause_id`: String (`str`), e.g. `"3.1"`, `"8.1"`.

---

## 2. The 15 REST Endpoints

| # | Method | Path | Request Body / Params | Response Model | HTTP Status | Auth Required |
| :- | :--- | :--- | :--- | :--- | :- | :- |
| 1 | `GET` | `/api/v1/health` | None | `{status, mock_mode, contract_version}` | `200 OK` | No |
| 2 | `POST` | `/api/v1/auth/register` | `UserRegister` (JSON) | `UserOut` | `201 Created` | No |
| 3 | `POST` | `/api/v1/auth/login` | `UserLogin` (JSON) | `TokenResponse` | `200 OK` | No |
| 4 | `GET` | `/api/v1/auth/me` | None | `UserOut` | `200 OK` | Yes |
| 5 | `POST` | `/api/v1/documents` | Multipart (`file`, `document_type`) | `DocumentOut` | `201 Created` | Yes |
| 6 | `GET` | `/api/v1/documents` | None | `list[DocumentOut]` | `200 OK` | Yes |
| 7 | `GET` | `/api/v1/documents/{id}` | Path: `id: int` | `DocumentOut` | `200 OK` | Yes |
| 8 | `GET` | `/api/v1/documents/{id}/clauses` | Path: `id: int` | `ParsedDocument` | `200 OK` | Yes |
| 9 | `GET` | `/api/v1/documents/{id}/graph` | Path: `id: int` | `ClauseGraph` | `200 OK` | Yes |
| 10 | `POST` | `/api/v1/documents/{id}/analyze` | Path: `id: int` | `AnalysisResult` | `200 OK` | Yes |
| 11 | `GET` | `/api/v1/documents/{id}/analysis` | Path: `id: int` | `AnalysisResult` | `200 OK` | Yes |
| 12 | `POST` | `/api/v1/compare` | `CompareRequest` (JSON) | `ComparisonResult` | `200 OK` | Yes |
| 13 | `PATCH` | `/api/v1/findings/{id}/review` | Path: `id: int`, `ReviewUpdate` (JSON) | `RiskFinding` | `200 OK` | Yes |
| 14 | `PATCH` | `/api/v1/contradictions/{id}/review` | Path: `id: int`, `ReviewUpdate` (JSON) | `Contradiction` | `200 OK` | Yes |
| 15 | `GET` | `/api/v1/documents/{id}/audit` | Path: `id: int` | `list[AuditEvent]` | `200 OK` | Yes |

*Note: In `MOCK_MODE=true`, token checks are bypassed to enable frontend rapid prototyping.*

---

## 3. Document Upload Orchestration Steps
When a document is uploaded via `POST /api/v1/documents`, the backend pipeline executes these 8 steps sequentially:

1. **Validate**:
   - Check file format (`.pdf` or `.docx` only).
   - Check file size against `MAX_UPLOAD_MB`.
   - Validate `document_type` is one of `DocumentType` enum values.
2. **Save**:
   - Write file stream safely to `UPLOAD_DIR/<uuid>_<filename>`.
3. **Insert Document**:
   - Create record in `documents` table with `status = 'UPLOADED'`.
4. **Parse Clauses**:
   - Call `doc_engine.parse_document(stored_path, document_type)`.
   - Update document `status = 'PARSED'` and record `page_count`.
5. **Store Clauses**:
   - Batch insert extracted clauses into `clauses` table within a transaction.
6. **Build Clause Graph**:
   - Call `graph_engine.build_graph(parsed_document)`.
   - Persist graph topology and cycle flags in `clause_graphs` table.
7. **Audit Record**:
   - Insert audit records with actions `UPLOADED`, `PARSED`, and `GRAPH_BUILT`.
8. **Error Handling**:
   - If an exception occurs at any stage, update document `status = 'FAILED'`, log an audit event with action `FAILED` and error details, and return an appropriate 4xx/5xx `ErrorResponse`.
