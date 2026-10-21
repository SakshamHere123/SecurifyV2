import { Link } from "react-router-dom";

/**
 * Role-chooser landing page. This replaces the old single generic Login
 * page as the destination for "/login" and for any unauthenticated
 * redirect (see client.js's 401 interceptor, which still points at
 * "/login" -- that still works because this page now lives there).
 *
 * It doesn't authenticate anything itself -- it just routes the person to
 * one of the four real auth pages, because admin and employee now have
 * completely separate credentials, forms, and backend endpoints.
 */
export default function Landing() {
  return (
    <div className="relative flex items-center justify-center min-h-screen px-4 overflow-hidden font-sans antialiased bg-slate-950 text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-cyan-950/20 via-slate-950 to-slate-950 pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b0a_1px,transparent_1px),linear-gradient(to_bottom,#1e293b0a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

      <div className="relative w-full max-w-2xl">
        <div className="mb-10 text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.7)] ring-2 ring-cyan-500/20 animate-pulse" />
            <span className="text-lg font-semibold tracking-wider uppercase text-slate-100">
              Securify
            </span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            Choose how you're signing in
          </h1>
          <p className="mt-1.5 text-xs text-slate-400">
            Admins and employees use separate credentials and separate portals.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {/* Admin card */}
          <div className="relative p-6 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-2xl ring-1 ring-white/5">
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-amber-500/40 to-transparent pointer-events-none" />
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20 uppercase tracking-wider">
              Admin
            </span>
            <h2 className="mt-3 text-base font-semibold text-slate-100">
              Organization admin
            </h2>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              Create a new org, or sign in to manage policies and oversee scans.
            </p>
            <div className="flex flex-col gap-2 mt-5">
              <Link
                to="/admin/login"
                className="w-full text-center bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg py-2.5 text-sm font-medium transition-all duration-150"
              >
                Admin sign in
              </Link>
              <Link
                to="/admin/signup"
                className="w-full text-center text-slate-400 hover:text-slate-200 text-xs py-1.5 transition-colors"
              >
                Create a new organization &rarr;
              </Link>
            </div>
          </div>

          {/* Employee card */}
          <div className="relative p-6 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-2xl ring-1 ring-white/5">
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent pointer-events-none" />
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 uppercase tracking-wider">
              Employee
            </span>
            <h2 className="mt-3 text-base font-semibold text-slate-100">
              Team member
            </h2>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              Join your org with the Org ID your admin shared, or sign in to run scans.
            </p>
            <div className="flex flex-col gap-2 mt-5">
              <Link
                to="/employee/login"
                className="w-full text-center bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-lg py-2.5 text-sm font-medium transition-all duration-150"
              >
                Employee sign in
              </Link>
              <Link
                to="/employee/signup"
                className="w-full text-center text-slate-400 hover:text-slate-200 text-xs py-1.5 transition-colors"
              >
                Join an organization &rarr;
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
