# Database Schema Documentation

## 1. Overview
The database uses **MySQL 8** with the **InnoDB** storage engine and `utf8mb4` character encoding.
All database access uses raw parameterized SQL via PyMySQL. ORMs such as SQLAlchemy are strictly prohibited.

> **CRITICAL RULE**: Never edit an applied migration script. Always create a new sequential migration script (e.g. `002_add_field.sql`) for any future schema changes.

## 2. Table Specifications

### `users`
Stores user authentication credentials and profiles.
- `user_id`: Primary Key (AUTO_INCREMENT INT)
- `email`: Unique email address (VARCHAR 255)
- `password_hash`: Bcrypt hashed password (VARCHAR 255)
- `full_name`: User's full name (VARCHAR 255)
- `created_at`: Registration timestamp

### `documents`
Metadata and parsing status for uploaded contract files.
- `document_id`: Primary Key (AUTO_INCREMENT INT)
- `file_name`: Original file name (VARCHAR 255)
- `document_type`: ENUM(`'MSA'`, `'SOW'`, `'OTHER'`)
- `status`: ENUM(`'UPLOADED'`, `'PARSED'`, `'ANALYZED'`, `'FAILED'`)
- `page_count`: Total number of pages (INT, nullable)
- `stored_path`: Absolute or relative path on server filesystem (VARCHAR 1024)
- `parser_version`: Version string of parser used (VARCHAR 32)
- `uploaded_at`: Upload timestamp
- `created_by`: Foreign key to `users.user_id` (ON DELETE SET NULL)

### `clauses`
Extracted individual contract clauses.
- `id`: Primary Key (AUTO_INCREMENT INT)
- `document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `clause_id`: Identifier within the contract, e.g. `"3.1"` (VARCHAR 64)
- `title`: Clause section heading/title (VARCHAR 255, nullable)
- `text`: Full raw clause text (TEXT)
- `page_number`: Starting page number (INT >= 1)
- `section`: Major section designator (VARCHAR 64, nullable)
- `parent_clause_id`: Parent hierarchical clause id (VARCHAR 64, nullable)
- `references_json`: JSON array of referenced clause identifiers
- `uq_doc_clause`: Unique constraint on `(document_id, clause_id)`

### `clause_graphs`
Stored graph topology and circular dependency analysis per document.
- `id`: Primary Key (AUTO_INCREMENT INT)
- `document_id`: Foreign key to `documents.document_id` (UNIQUE, ON DELETE CASCADE)
- `graph_json`: Complete JSON representation of `ClauseGraph`
- `has_cycle`: Boolean flag indicating detected circular dependencies
- `created_at`: Graph construction timestamp

### `analyses`
High-level risk assessment results for a document.
- `analysis_id`: Primary Key (AUTO_INCREMENT INT)
- `document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `overall_risk_score`: Aggregated score from 0.00 to 100.00 (DECIMAL 5,2)
- `summary`: Executive risk summary (TEXT)
- `model_used`: Identifier of the model/playbook used (VARCHAR 128)
- `created_at`: Timestamp of analysis run

### `findings`
Individual clause-level risk findings generated against playbook rules.
- `finding_id`: Primary Key (AUTO_INCREMENT INT)
- `analysis_id`: Foreign key to `analyses.analysis_id` (ON DELETE CASCADE)
- `document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `clause_id`: Target clause identifier (VARCHAR 64)
- `risk_level`: ENUM(`'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'`)
- `risk_category`: ENUM matching 12 categories in `shared/contracts.py`
- `explanation`: Detailed explanation of risk exposure (TEXT)
- `evidence_json`: JSON array of `Evidence` objects
- `suggested_redline`: AI-suggested replacement text (TEXT, nullable)
- `review_status`: ENUM(`'PENDING'`, `'ACCEPTED'`, `'REJECTED'`, `'MODIFIED'`)

### `comparisons`
Cross-document analysis comparing an MSA and an SOW.
- `comparison_id`: Primary Key (AUTO_INCREMENT INT)
- `msa_document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `sow_document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `model_used`: Model identifier used for contradiction detection (VARCHAR 128)
- `created_at`: Comparison timestamp

### `contradictions`
Discrepancies identified between an MSA and an SOW.
- `contradiction_id`: Primary Key (AUTO_INCREMENT INT)
- `comparison_id`: Foreign key to `comparisons.comparison_id` (ON DELETE CASCADE)
- `msa_clause_id`: Contradictory clause id in MSA (VARCHAR 64)
- `sow_clause_id`: Contradictory clause id in SOW (VARCHAR 64)
- `risk_category`: Risk category ENUM
- `risk_level`: Risk level ENUM
- `description`: Explanation of the conflicting terms (TEXT)
- `evidence_json`: JSON array of quotes from both documents
- `suggested_redline`: Harmonized compromise text (TEXT, nullable)
- `review_status`: ENUM(`'PENDING'`, `'ACCEPTED'`, `'REJECTED'`, `'MODIFIED'`)

### `reviews`
Audit log of human-in-the-loop decisions on findings or contradictions.
- `review_id`: Primary Key (AUTO_INCREMENT INT)
- `finding_id`: Foreign key to `findings.finding_id` (ON DELETE CASCADE, nullable)
- `contradiction_id`: Foreign key to `contradictions.contradiction_id` (ON DELETE CASCADE, nullable)
- `user_id`: Foreign key to `users.user_id` (ON DELETE SET NULL, nullable)
- `review_status`: ENUM(`'PENDING'`, `'ACCEPTED'`, `'REJECTED'`, `'MODIFIED'`)
- `comment`: Reviewer remarks (TEXT, nullable)
- `modified_redline`: Reviewer-edited clause redline (TEXT, nullable)
- `created_at`: Review action timestamp

### `audit_log`
Immutable record of all system and document lifecycle events.
- `event_id`: Primary Key (AUTO_INCREMENT INT)
- `document_id`: Foreign key to `documents.document_id` (ON DELETE CASCADE)
- `user_id`: Foreign key to `users.user_id` (ON DELETE SET NULL, nullable)
- `action`: Specific lifecycle stage (VARCHAR 64)
- `details`: Descriptive metadata or error details (TEXT, nullable)
- `created_at`: Event timestamp

## 3. Standard Audit Actions
The following actions must be recorded in `audit_log.action`:
- `UPLOADED`: Document received and saved to disk.
- `PARSED`: Text parsed and clauses extracted.
- `GRAPH_BUILT`: Clause graph constructed and cycles analyzed.
- `ANALYZED`: Single-document playbook risk evaluation completed.
- `COMPARED`: Multi-document MSA-vs-SOW comparison completed.
- `REVIEWED`: Human reviewer updated a finding or contradiction.
- `FAILED`: Failure encountered during any processing pipeline stage.

