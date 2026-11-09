import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

export default function LoginPage() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/documents";

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login({
        email: formData.email.trim(),
        password: formData.password,
      });
      navigate(from, { replace: true });
    } catch (err) {
      if (err?.message?.toLowerCase().includes("failed to fetch")) {
        setError(
          "Unable to connect to backend server at http://localhost:8000. Please ensure the backend is running."
        );
      } else {
        setError(
          err?.detail ||
            err?.message ||
            "Failed to sign in. Please verify your credentials."
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        <div className="auth-card-header">
          <h2>Sign in to your account</h2>
          <p>Access your contract risk analysis dashboard and audit trail</p>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">!</span>
            <span className="alert-text">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              name="email"
              autoComplete="email"
              required
              placeholder="analyst@firm.com"
              value={formData.email}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Do not have an account?{" "}
            <Link to="/register" className="auth-link">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
