import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth.js";

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          <span className="brand-badge">Legal AI</span>
          <span className="brand-title">Contract & SOW Risk Analyzer</span>
        </Link>

        <nav className="navbar-nav">
          {token ? (
            <div className="nav-authenticated">
              <NavLink
                to="/documents"
                className={({ isActive }) =>
                  isActive ? "nav-link active" : "nav-link"
                }
              >
                Documents
              </NavLink>
              <div className="user-profile">
                <span className="user-avatar" aria-hidden="true">
                  {(user?.full_name || user?.email || "U")
                    .charAt(0)
                    .toUpperCase()}
                </span>
                <span className="user-name">
                  {user?.full_name || user?.email || "User"}
                </span>
              </div>
              <button
                type="button"
                className="btn-logout"
                onClick={handleLogout}
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="nav-unauthenticated">
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  isActive ? "nav-link active" : "nav-link"
                }
              >
                Login
              </NavLink>
              <NavLink
                to="/register"
                className={({ isActive }) =>
                  isActive ? "btn-primary-small active" : "btn-primary-small"
                }
              >
                Register
              </NavLink>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
