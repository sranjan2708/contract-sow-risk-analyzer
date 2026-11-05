/**
 * API Endpoints mapping to Contract 3 specifications.
 * All requests and payloads strictly use snake_case field names.
 */
import { request } from "./client.js";

export const api = {
  // Auth
  register: ({ email, password, full_name }) =>
    request("/auth/register", {
      method: "POST",
      body: { email, password, full_name },
    }),

  login: ({ email, password }) =>
    request("/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  me: () =>
    request("/auth/me", {
      method: "GET",
    }),

  // Documents
  uploadDocument: (file, document_type) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", document_type);
    return request("/documents", {
      method: "POST",
      body: formData,
    });
  },

  listDocuments: () =>
    request("/documents", {
      method: "GET",
    }),

  getDocument: (id) =>
    request(`/documents/${id}`, {
      method: "GET",
    }),

  getClauses: (id) =>
    request(`/documents/${id}/clauses`, {
      method: "GET",
    }),

  getGraph: (id) =>
    request(`/documents/${id}/graph`, {
      method: "GET",
    }),

  // Analysis & Comparison
  analyzeDocument: (id) =>
    request(`/documents/${id}/analyze`, {
      method: "POST",
    }),

  getAnalysis: (id) =>
    request(`/documents/${id}/analysis`, {
      method: "GET",
    }),

  compare: ({ msa_document_id, sow_document_id }) =>
    request("/compare", {
      method: "POST",
      body: { msa_document_id, sow_document_id },
    }),

  // Reviews
  reviewFinding: (id, { review_status, comment = null, modified_redline = null }) =>
    request(`/findings/${id}/review`, {
      method: "PATCH",
      body: { review_status, comment, modified_redline },
    }),

  reviewContradiction: (id, { review_status, comment = null, modified_redline = null }) =>
    request(`/contradictions/${id}/review`, {
      method: "PATCH",
      body: { review_status, comment, modified_redline },
    }),

  // Audit
  getAudit: (id) =>
    request(`/documents/${id}/audit`, {
      method: "GET",
    }),
};

export default api;
