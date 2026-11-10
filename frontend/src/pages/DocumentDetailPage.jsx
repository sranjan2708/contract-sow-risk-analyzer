import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/endpoints.js";

export default function DocumentDetailPage() {
  const { id } = useParams();
  const [document, setDocument] = useState(null);
  const [clausesDoc, setClausesDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isNotFound, setIsNotFound] = useState(false);

  const fetchDocumentData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsNotFound(false);

    try {
      const docId = parseInt(id, 10);
      if (isNaN(docId)) {
        setIsNotFound(true);
        setLoading(false);
        return;
      }

      // Fetch metadata and clauses in parallel
      const [docData, clausesData] = await Promise.all([
        api.getDocument(docId),
        api.getClauses(docId),
      ]);

      setDocument(docData);
      setClausesDoc(clausesData);
    } catch (err) {
      if (err?.status === 404 || err?.detail?.toLowerCase().includes("not found")) {
        setIsNotFound(true);
      } else {
        const errorMsg =
          err?.detail ||
          (err?.message && err.message.toLowerCase().includes("fetch")
            ? "Unable to connect to backend server at http://localhost:8000."
            : err?.message) ||
          "Failed to load document details.";
        setError(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const docId = parseInt(id, 10);
        if (isNaN(docId)) {
          if (isMounted) setIsNotFound(true);
          return;
        }

        const [docData, clausesData] = await Promise.all([
          api.getDocument(docId),
          api.getClauses(docId),
        ]);

        if (isMounted) {
          setDocument(docData);
          setClausesDoc(clausesData);
          setError(null);
          setIsNotFound(false);
        }
      } catch (err) {
        if (isMounted) {
          if (err?.status === 404 || err?.detail?.toLowerCase().includes("not found")) {
            setIsNotFound(true);
          } else {
            const errorMsg =
              err?.detail ||
              (err?.message && err.message.toLowerCase().includes("fetch")
                ? "Unable to connect to backend server at http://localhost:8000."
                : err?.message) ||
              "Failed to load document details.";
            setError(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
          }
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="detail-page-container">
        <div className="loading-state-container">
          <div className="auth-loading-spinner" />
          <p>Loading document details and clauses...</p>
        </div>
      </div>
    );
  }

  if (isNotFound) {
    return (
      <div className="detail-page-container">
        <div className="not-found-card">
          <span className="not-found-icon">🔍</span>
          <h2>Document not found</h2>
          <p>
            The requested contract document ID <strong>#{id}</strong> does not exist or has been removed.
          </p>
          <Link to="/documents" className="btn btn-primary">
            ← Back to Documents
          </Link>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="detail-page-container">
        <div className="alert alert-error">
          <span className="alert-icon">!</span>
          <span className="alert-text">{error}</span>
        </div>
        <div className="error-actions">
          <button type="button" className="btn btn-primary" onClick={fetchDocumentData}>
            Retry
          </button>
          <Link to="/documents" className="btn btn-secondary">
            Back to Documents
          </Link>
        </div>
      </div>
    );
  }

  const clauses = clausesDoc?.clauses || [];
  const statusLower = (document?.status || "uploaded").toLowerCase();

  return (
    <div className="detail-page-container">
      <div className="detail-breadcrumbs">
        <Link to="/documents" className="breadcrumb-link">
          ← Back to Documents
        </Link>
      </div>

      <div className="detail-header-card">
        <div className="detail-header-top">
          <div className="detail-title-area">
            <span className="doc-id-pill">Doc #{document?.document_id}</span>
            <h1 className="detail-filename">{document?.file_name}</h1>
          </div>
          <div className="detail-badges">
            <span className={`badge-type badge-${document?.document_type?.toLowerCase()}`}>
              {document?.document_type}
            </span>
            <span className={`badge-status status-${statusLower}`}>
              {document?.status}
            </span>
          </div>
        </div>

        <div className="metadata-grid">
          <div className="meta-item">
            <span className="meta-label">Page Count</span>
            <span className="meta-value">{document?.page_count ?? clausesDoc?.page_count ?? "—"}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Extracted Clauses</span>
            <span className="meta-value">{clauses.length}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Uploaded At</span>
            <span className="meta-value">
              {document?.uploaded_at ? new Date(document.uploaded_at).toLocaleString() : "—"}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Parser Version</span>
            <span className="meta-value">{clausesDoc?.parser_version || "0.1.0"}</span>
          </div>
        </div>
      </div>

      <div className="clauses-section">
        <div className="section-title-row">
          <h2>Structured Clauses ({clauses.length})</h2>
          <span className="section-hint">Parsed clause hierarchy and cross-references</span>
        </div>

        {clauses.length === 0 ? (
          <div className="empty-clauses-box">
            <p>No clauses have been extracted for this document.</p>
          </div>
        ) : (
          <div className="clauses-table-wrapper">
            <table className="clauses-table">
              <thead>
                <tr>
                  <th style={{ width: "90px" }}>Clause ID</th>
                  <th style={{ width: "160px" }}>Title</th>
                  <th style={{ width: "80px" }}>Page</th>
                  <th style={{ width: "140px" }}>References</th>
                  <th>Clause Text</th>
                </tr>
              </thead>
              <tbody>
                {clauses.map((clause) => (
                  <tr key={clause.clause_id} className="clause-row">
                    <td>
                      <span className="clause-id-badge">{clause.clause_id}</span>
                    </td>
                    <td>
                      <span className="clause-title">{clause.title || "—"}</span>
                    </td>
                    <td>
                      <span className="clause-page">p. {clause.page_number}</span>
                    </td>
                    <td>
                      {clause.references && clause.references.length > 0 ? (
                        <div className="reference-tags">
                          {clause.references.map((ref) => (
                            <span key={ref} className="ref-tag">
                              {ref}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="clause-text-cell">
                      <p className="clause-text-content">{clause.text}</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
