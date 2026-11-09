import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { register, login } = useAuth();
  const navigate = useNavigate();

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

    if (!formData.full_name.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!formData.email.trim()) {
      setError("Email address is required.");
      return;
    }
    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setSubmitting(true);

    try {
      // Register with snake_case payload
      await register({
        full_name: formData.full_name.trim(),
        email: formData.email.trim(),
        password: formData.password,
      });

      // Auto login after successful registration
      try {
        await login({
          email: formData.email.trim(),
          password: formData.password,
        });
        navigate("/documents", { replace: true });
      } catch {
        navigate("/login", {
          state: { message: "Account created successfully. Please sign in." },
        });
      }
    } catch (err) {
      if (err?.message?.toLowerCase().includes("failed to fetch")) {
        setError(
          "Unable to connect to backend server at http://localhost:8000. Please ensure the backend is running."
        );
      } else {
        setError(
          err?.detail ||
            err?.message ||
            "Registration failed. Please try again."
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
          <h2>Create your account</h2>
          <p>Join the Contract & SOW Risk Analyzer workspace</p>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">!</span>
            <span className="alert-text">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="full_name">Full name</label>
            <input
              id="full_name"
              type="text"
              name="full_name"
              autoComplete="name"
              required
              placeholder="Jane Doe"
              value={formData.full_name}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              name="email"
              autoComplete="email"
              required
              placeholder="jane.doe@firm.com"
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
              autoComplete="new-password"
              required
              placeholder="At least 8 characters"
              value={formData.password}
              onChange={handleChange}
              disabled={submitting}
            />
            <span className="form-hint">Must be 8 characters or more.</span>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting}
          >
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Already have an account?{" "}
            <Link to="/login" className="auth-link">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
