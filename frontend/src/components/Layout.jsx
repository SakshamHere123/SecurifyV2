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
    <div className="flex min-h-screen font-sans antialiased bg-slate-950 text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
      <aside className="flex flex-col justify-between w-64 border-r bg-slate-900/60 backdrop-blur-xl border-slate-800/80 shrink-0">
        <div>
          {/* Brand Header */}
          <div className="flex items-center h-16 gap-3 px-6 border-b border-slate-800/80">
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.65)] ring-2 ring-cyan-500/20 animate-pulse" />
            <div className="flex items-baseline gap-2">
              <h1 className="text-base font-semibold tracking-wider uppercase text-slate-100">
                Securify
              </h1>
              <span className="text-[10px] font-mono tracking-widest text-cyan-400/80 uppercase">
                v2.4
              </span>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="p-3 space-y-1.5">
            <p className="px-3 pt-2 pb-1 text-[11px] font-semibold text-slate-500 uppercase tracking-widest">
              Navigation
            </p>
            {navItems.map((item) => {
              const active = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`group flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 border ${
                    active
                      ? "bg-cyan-500/10 text-cyan-300 border-cyan-500/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]"
                      : "text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-800/50 hover:border-slate-800"
                  }`}
                >
                  <span className="tracking-wide">{item.label}</span>
                  {active && (
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User & Session Footer */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-900/40">
          <div className="px-3 py-2.5 mb-2 rounded-md bg-slate-950/60 border border-slate-800/60 flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500">
                Security Role
              </span>
              <span className="text-xs font-medium truncate text-slate-200">
                {user?.role === "admin" ? "Super Admin" : "SecOps Member"}
              </span>
            </div>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium border uppercase tracking-wider ${
                user?.role === "admin"
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                  : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
              }`}
            >
              {user?.role === "admin" ? "Admin" : "Member"}
            </span>
          </div>

          <button
            onClick={logout}
            className="flex items-center justify-center w-full gap-2 px-3 py-2 text-xs font-medium transition-all duration-150 border border-transparent rounded-md text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 hover:border-rose-500/20"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-8 overflow-y-auto bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(15,23,42,0.6),rgba(2,6,23,1))]">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
    </div>
  );
}