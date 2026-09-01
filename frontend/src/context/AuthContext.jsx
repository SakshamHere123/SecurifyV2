import { createContext, useContext, useState, useEffect } from "react";
import apiClient from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("securify_user");
    if (stored) {
      setUser(JSON.parse(stored));
    }
    setLoading(false);
  }, []);

  function _persistSession(data) {
    localStorage.setItem("securify_token", data.access_token);
    const userInfo = { org_id: data.org_id, user_id: data.user_id, role: data.role };
    localStorage.setItem("securify_user", JSON.stringify(userInfo));
    setUser(userInfo);
  }

  async function login(email, password) {
    const res = await apiClient.post("/auth/login", { email, password });
    _persistSession(res.data);
    return res.data;
  }

  async function signup(orgName, email, password) {
    const res = await apiClient.post("/auth/signup", {
      org_name: orgName,
      email,
      password,
    });
    _persistSession(res.data);
    return res.data;
  }

  function logout() {
    localStorage.removeItem("securify_token");
    localStorage.removeItem("securify_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}