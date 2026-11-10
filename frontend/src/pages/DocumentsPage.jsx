import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import api from "../api/endpoints.js";
import UploadForm from "../components/UploadForm.jsx";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDocuments();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err) {
      const errorMsg =
        err?.detail ||
        (err?.message && err.message.toLowerCase().includes("fetch")
          ? "Unable to connect to backend server at http://localhost:8000. Please ensure the backend is running."
          : err?.message) ||
        "Failed to load documents list.";
      setError(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const data = await api.listDocuments();
        if (isMounted) {
          setDocuments(Array.isArray(data) ? data : []);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          const errorMsg =
            err?.detail ||
            (err?.message && err.message.toLowerCase().includes("fetch")
              ? "Unable to connect to backend server at http://localhost:8000. Please ensure the backend is running."
              : err?.message) ||
            "Failed to load documents list.";
          setError(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleUploaded = () => {
    // Refresh document list after new upload
    fetchDocuments();
  };

  return (
    <div className="documents-page-container">
      <div className="page-header">
        <div>
          <h1>Contract Documents</h1>
          <p className="subtitle">
            Ingest MSAs and SOWs, parse clauses, and inspect contract dependency structures.
          </p>
        </div>
      </div>

      {/* Upload Form Component */}
      <UploadForm onUploaded={handleUploaded} />

      {/* Documents List Table Section */}
      <div className="documents-list-section">
        <div className="section-title-row">
          <h2>Document Repository</h2>
          <span className="doc-count-tag">{documents.length} document{documents.length === 1 ? "" : "s"}</span>
        </div>

        {loading && (
          <div className="loading-state-container">
            <div className="auth-loading-spinner" />
            <p>Loading document repository...</p>
          </div>
        )}

        {!loading && error && (
          <div className="alert-with-action">
            <div className="alert alert-error">
              <span className="alert-icon">!</span>
              <span className="alert-text">{error}</span>
            </div>
            <button type="button" className="btn btn-primary" onClick={fetchDocuments}>
              Retry
            </button>
          </div>
        )}

        {!loading && !error && documents.length === 0 && (
          <div className="documents-placeholder-card">
            <div className="placeholder-icon">📄</div>
            <h3>No documents uploaded yet</h3>
            <p>
              Select an MSA or SOW document (.pdf or .docx) using the form above to begin parsing clauses.
            </p>
          </div>
        )}

        {!loading && !error && documents.length > 0 && (
          <div className="table-responsive">
            <table className="documents-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Pages</th>
                  <th>Uploaded At</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => {
                  const statusClass = `status-${(doc.status || "uploaded").toLowerCase()}`;
                  const typeClass = `badge-${(doc.document_type || "other").toLowerCase()}`;
                  return (
                    <tr key={doc.document_id} className="document-row">
                      <td>
                        <Link
                          to={`/documents/${doc.document_id}`}
                          className="document-name-link"
                          title="View document clauses"
                        >
                          <span className="doc-icon">📄</span>
                          <span className="doc-title">{doc.file_name}</span>
                        </Link>
                      </td>
                      <td>
                        <span className={`badge-type ${typeClass}`}>
                          {doc.document_type}
                        </span>
                      </td>
                      <td>
                        <span className={`badge-status ${statusClass}`}>
                          {doc.status}
                        </span>
                      </td>
                      <td>
                        <span className="page-count-val">
                          {doc.page_count != null ? doc.page_count : "—"}
                        </span>
                      </td>
                      <td>
                        <span className="date-val">
                          {doc.uploaded_at
                            ? new Date(doc.uploaded_at).toLocaleString()
                            : "—"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <Link
                          to={`/documents/${doc.document_id}`}
                          className="btn-table-action"
                        >
                          View Clauses →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
