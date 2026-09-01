import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [{ to: "/", label: "Dashboard" }];
  if (user?.role === "admin") {
    navItems.push({ to: "/admin", label: "Admin panel" });
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex flex-col bg-white border-r w-60 border-slate-200">
        <div className="px-6 py-5 border-b border-slate-200">
          <h1 className="text-lg font-semibold text-slate-900">Securify</h1>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="px-3 py-4 border-t border-slate-200">
          <p className="px-3 mb-2 text-xs font-medium tracking-wide uppercase text-slate-400">
            {user?.role === "admin" ? "Admin" : "Member"}
          </p>
          <button
            onClick={logout}
            className="w-full px-3 py-2 text-sm font-medium text-left rounded-lg text-slate-600 hover:bg-slate-100"
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">{children}</main>
    </div>
  );
}