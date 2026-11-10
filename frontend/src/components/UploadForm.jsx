import { useState } from "react";
import api from "../api/endpoints.js";

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB limit
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

export default function UploadForm({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("MSA");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0] || null;
    setError(null);
    setSuccess(null);

    if (!selected) {
      setFile(null);
      return;
    }

    const dotIndex = selected.name.lastIndexOf(".");
    const ext = dotIndex !== -1 ? selected.name.substring(dotIndex).toLowerCase() : "";

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file format '${ext || "unknown"}'. Only .pdf and .docx files are permitted.`);
      setFile(null);
      e.target.value = "";
      return;
    }

    if (selected.size > MAX_FILE_SIZE_BYTES) {
      setError("File exceeds maximum allowed size of 25 MB.");
      setFile(null);
      e.target.value = "";
      return;
    }

    setFile(selected);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!file) {
      setError("Please select a .pdf or .docx file to upload.");
      return;
    }

    setUploading(true);

    try {
      const result = await api.uploadDocument(file, documentType);
      setSuccess(`Document '${result.file_name || file.name}' uploaded and parsed successfully.`);
      setFile(null);
      e.target.reset();
      if (onUploaded) {
        onUploaded(result);
      }
    } catch (err) {
      const errorMsg =
        err?.detail ||
        (err?.message && err.message.toLowerCase().includes("fetch")
          ? "Unable to connect to backend server at http://localhost:8000. Please ensure the backend is running."
          : err?.message) ||
        "Upload failed. Please verify the document format and try again.";
      setError(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-card">
      <div className="upload-card-header">
        <h3>Upload Contract Document</h3>
        <p>Supported formats: PDF, DOCX (Max 25 MB)</p>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">!</span>
          <span className="alert-text">{error}</span>
        </div>
      )}

      {success && (
        <div className="alert alert-success" role="status">
          <span className="alert-icon-success">✓</span>
          <span className="alert-text">{success}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="upload-form">
        <div className="upload-form-row">
          <div className="form-group file-group">
            <label htmlFor="file-input">Contract File (.pdf, .docx)</label>
            <input
              id="file-input"
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              disabled={uploading}
              required
            />
            {file && (
              <span className="file-selected-info">
                Selected: <strong>{file.name}</strong> ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </span>
            )}
          </div>

          <div className="form-group type-group">
            <label htmlFor="doc-type-select">Document Type</label>
            <select
              id="doc-type-select"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              disabled={uploading}
            >
              <option value="MSA">MSA (Master Services Agreement)</option>
              <option value="SOW">SOW (Statement of Work)</option>
              <option value="OTHER">OTHER</option>
            </select>
          </div>

          <div className="form-group submit-group">
            <label className="invisible-label" aria-hidden="true">Upload Action</label>
            <button
              type="submit"
              className="btn btn-primary btn-upload"
              disabled={uploading || !file}
            >
              {uploading ? "Uploading & Parsing..." : "Upload & Parse"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

