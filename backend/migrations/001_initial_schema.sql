-- ============================================================================
-- Migration 001: Initial Database Schema
-- Engine: InnoDB, Charset: utf8mb4
-- All ENUM definitions strictly match shared/contracts.py
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documents (
    document_id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    document_type ENUM('MSA', 'SOW', 'OTHER') NOT NULL,
    status ENUM('UPLOADED', 'PARSED', 'ANALYZED', 'FAILED') NOT NULL DEFAULT 'UPLOADED',
    page_count INT DEFAULT NULL,
    stored_path VARCHAR(1024) NOT NULL,
    parser_version VARCHAR(32) NOT NULL DEFAULT '0.1.0',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT NULL,
    CONSTRAINT fk_documents_user FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clauses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    clause_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NULL,
    text TEXT NOT NULL,
    page_number INT NOT NULL,
    section VARCHAR(64) NULL,
    parent_clause_id VARCHAR(64) NULL,
    references_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_clauses_document FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    CONSTRAINT uq_doc_clause UNIQUE (document_id, clause_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clause_graphs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL UNIQUE,
    graph_json JSON NOT NULL,
    has_cycle BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_graphs_document FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    overall_risk_score DECIMAL(5,2) NOT NULL,
    summary TEXT NOT NULL,
    model_used VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_analyses_document FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS findings (
    finding_id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    document_id INT NOT NULL,
    clause_id VARCHAR(64) NOT NULL,
    risk_level ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    risk_category ENUM(
        'PAYMENT',
        'LIABILITY',
        'INDEMNITY',
        'TERMINATION',
        'CONFIDENTIALITY',
        'INTELLECTUAL_PROPERTY',
        'WARRANTY',
        'DATA_PROTECTION',
        'SCOPE',
        'DELIVERY',
        'GOVERNING_LAW',
        'OTHER'
    ) NOT NULL,
    explanation TEXT NOT NULL,
    evidence_json JSON NOT NULL,
    suggested_redline TEXT NULL,
    review_status ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'MODIFIED') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_findings_analysis FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE,
    CONSTRAINT fk_findings_document FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS comparisons (
    comparison_id INT AUTO_INCREMENT PRIMARY KEY,
    msa_document_id INT NOT NULL,
    sow_document_id INT NOT NULL,
    model_used VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comparisons_msa FOREIGN KEY (msa_document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    CONSTRAINT fk_comparisons_sow FOREIGN KEY (sow_document_id) REFERENCES documents(document_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contradictions (
    contradiction_id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_id INT NOT NULL,
    msa_clause_id VARCHAR(64) NOT NULL,
    sow_clause_id VARCHAR(64) NOT NULL,
    risk_category ENUM(
        'PAYMENT',
        'LIABILITY',
        'INDEMNITY',
        'TERMINATION',
        'CONFIDENTIALITY',
        'INTELLECTUAL_PROPERTY',
        'WARRANTY',
        'DATA_PROTECTION',
        'SCOPE',
        'DELIVERY',
        'GOVERNING_LAW',
        'OTHER'
    ) NOT NULL,
    risk_level ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    description TEXT NOT NULL,
    evidence_json JSON NOT NULL,
    suggested_redline TEXT NULL,
    review_status ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'MODIFIED') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contradictions_comparison FOREIGN KEY (comparison_id) REFERENCES comparisons(comparison_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    finding_id INT NULL,
    contradiction_id INT NULL,
    user_id INT NULL,
    review_status ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'MODIFIED') NOT NULL,
    comment TEXT NULL,
    modified_redline TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reviews_finding FOREIGN KEY (finding_id) REFERENCES findings(finding_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_contradiction FOREIGN KEY (contradiction_id) REFERENCES contradictions(contradiction_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_log (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    user_id INT NULL,
    action VARCHAR(64) NOT NULL,
    details TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_document FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
