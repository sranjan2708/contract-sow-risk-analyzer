import { useAuth } from "../context/useAuth.js";

export default function DocumentsPage() {
  const { user } = useAuth();

  return (
    <div className="documents-page-container">
      <div className="page-header">
        <div>
          <h1>Documents</h1>
          <p className="subtitle">
            Upload Master Services Agreements (MSAs) and Statements of Work (SOWs) for risk analysis.
          </p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn btn-primary" disabled>
            + Upload Document
          </button>
        </div>
      </div>

      <div className="dashboard-banner">
        <div className="banner-content">
          <h3>Welcome, {user?.full_name || user?.email || "Analyst"}!</h3>
          <p>
            Your session is authenticated. You can view parsed documents, cross-clause dependency graphs, risk findings, and contradiction reports once documents are ingested.
          </p>
        </div>
      </div>

      <div className="documents-placeholder-card">
        <div className="placeholder-icon">📄</div>
        <h3>No documents analyzed yet</h3>
        <p>
          Document upload and parsing pipeline integration will display your contract repository and risk score breakdown here.
        </p>
      </div>
    </div>
  );
}
