/**
 * Central API Client for Contract & SOW Risk Analyzer.
 * Rule: This is the ONLY file in the frontend repository permitted to invoke window.fetch.
 */

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const BASE_URL =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE_URL) ||
  "http://localhost:8000/api/v1";

/**
 * Base request dispatcher.
 * Handles Bearer token injection, multipart vs JSON payload encoding,
 * and standard error parsing.
 *
 * @param {string} endpoint - API path relative to BASE_URL (e.g. '/documents')
 * @param {Object} options - Fetch options including method, headers, body, params
 */
export async function request(endpoint, options = {}) {
  const { method = "GET", headers = {}, body, params } = options;

  let url = `${BASE_URL.replace(/\/+$/, "")}/${endpoint.replace(/^\/+/, "")}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const finalHeaders = { ...headers };

  // Inject authentication token if available
  if (typeof window !== "undefined" && window.localStorage) {
    const token = window.localStorage.getItem("access_token");
    if (token && !finalHeaders["Authorization"]) {
      finalHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

  let finalBody = body;
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  if (body && !isFormData && typeof body === "object") {
    finalHeaders["Content-Type"] = "application/json";
    finalBody = JSON.stringify(body);
  }

  const response = await fetch(url, {
    method,
    headers: finalHeaders,
    body: finalBody,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail !== undefined) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Body was not JSON, fallback to response status text
    }
    throw new ApiError(response.status, errorDetail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

