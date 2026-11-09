import { useState, useEffect } from "react";
import api from "../api/endpoints.js";
import { AuthContext } from "./authContextInstance.js";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage.getItem("access_token");
    }
    return null;
  });
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      const storedToken = window.localStorage.getItem("access_token");
      if (!storedToken) {
        if (isMounted) setLoading(false);
        return;
      }

      try {
        const userData = await api.me();
        if (isMounted) setUser(userData);
      } catch {
        if (isMounted) {
          window.localStorage.removeItem("access_token");
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async ({ email, password }) => {
    const res = await api.login({ email, password });
    if (res && res.access_token) {
      window.localStorage.setItem("access_token", res.access_token);
      setToken(res.access_token);
      try {
        const userData = await api.me();
        setUser(userData);
        return { user: userData, token: res.access_token };
      } catch {
        const fallbackUser = { email };
        setUser(fallbackUser);
        return { user: fallbackUser, token: res.access_token };
      }
    }
    throw new Error("Login failed: missing access token in response.");
  };

  const register = async ({ email, password, full_name }) => {
    const createdUser = await api.register({ email, password, full_name });
    return createdUser;
  };

  const logout = () => {
    window.localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
