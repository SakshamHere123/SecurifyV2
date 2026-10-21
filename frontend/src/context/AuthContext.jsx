import { createContext, useContext, useState, useEffect } from "react";
import apiClient from "../api/client";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const stored = localStorage.getItem("securify_user");
    if (stored) setUser(JSON.parse(stored));
    setLoading(false);
  }, []);
  function _persistSession(data) {
    localStorage.setItem("securify_token", data.access_token);
    const userInfo = {
      org_id: data.org_id,
      org_name: data.org_name,
      user_id: data.user_id,
      role: data.role,
    };
    localStorage.setItem("securify_user", JSON.stringify(userInfo));
    setUser(userInfo);
  }

  // Admin: creates a brand new org + its first (admin) user.
  async function adminSignup(orgName, email, password) {
    const res = await apiClient.post("/auth/admin/signup", {
      org_name: orgName,
      email,
      password,
    });
    _persistSession(res.data);
    return res.data;
  }

  // Employee: joins an EXISTING org via org_id, given to them by their admin.
  async function employeeSignup(orgId, email, password) {
    const res = await apiClient.post("/auth/employee/signup", {
      org_id: orgId,
      email,
      password,
    });
    _persistSession(res.data);
    return res.data;
  }

  // Admin login -- only succeeds for users whose role is admin, in that org.
  async function adminLogin(orgId, email, password) {
    const res = await apiClient.post("/auth/admin/login", {
      org_id: orgId,
      email,
      password,
    });
    _persistSession(res.data);
    return res.data;
  }

  // Employee login -- only succeeds for non-admin users, in that org.
  async function employeeLogin(orgId, email, password) {
    const res = await apiClient.post("/auth/employee/login", {
      org_id: orgId,
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
    <AuthContext.Provider
      value={{
        user,
        loading,
        adminSignup,
        employeeSignup,
        adminLogin,
        employeeLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
