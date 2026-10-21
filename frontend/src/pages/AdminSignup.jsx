import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AdminSignup() {
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { adminSignup } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await adminSignup(orgName, email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Signup failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex items-center justify-center min-h-screen px-4 overflow-hidden font-sans antialiased bg-slate-950 text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-amber-950/20 via-slate-950 to-slate-950 pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b0a_1px,transparent_1px),linear-gradient(to_bottom,#1e293b0a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

      <div className="relative w-full max-w-md bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)] ring-1 ring-white/5">
        <div className="flex items-center justify-between pb-6 mb-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.7)] ring-2 ring-amber-500/20 animate-pulse" />
            <div>
              <span className="text-base font-semibold tracking-wider uppercase text-slate-100">
                Securify
              </span>
              <span className="block text-[10px] font-mono tracking-widest text-slate-400 uppercase">
                Tenant Provisioning
              </span>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
            PROVISION_MODE
          </span>
        </div>

        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight text-slate-100">
            Create your org
          </h1>
          <p className="text-xs text-slate-400">
            Provision a new workspace. You become its admin and can upload policies
            and share the Org ID with your team afterward.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider font-mono">
              Organization Name
            </label>
            <input
              type="text"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition-all duration-150 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20"
              placeholder="e.g. Cyberdyne Systems"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider font-mono">
              Admin Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition-all duration-150 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20"
              placeholder="admin@enterprise.internal"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider font-mono">
              Password (Min 8 Chars)
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition-all duration-150 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20 font-mono"
              placeholder="••••••••••••"
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0 shadow-[0_0_6px_rgba(244,63,94,0.6)]" />
              <p className="font-mono text-xs font-medium leading-relaxed text-rose-300">
                {error}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full relative group overflow-hidden bg-amber-500/10 hover:bg-amber-500/20 active:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-lg py-2.5 text-sm font-medium transition-all duration-150 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              {submitting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
                  <span>Provisioning workspace...</span>
                </>
              ) : (
                "Initialize Organization"
              )}
            </span>
          </button>
        </form>

        <p className="mt-6 text-xs text-center text-slate-400">
          Already an admin?{" "}
          <Link
            to="/admin/login"
            className="font-medium transition-colors text-amber-400 hover:text-amber-300 hover:underline"
          >
            Sign in
          </Link>
        </p>
        <p className="mt-2 text-xs text-center text-slate-500">
          Joining an existing org as an employee?{" "}
          <Link
            to="/employee/signup"
            className="font-medium transition-colors text-cyan-400 hover:text-cyan-300 hover:underline"
          >
            Go here
          </Link>
        </p>
        <p className="mt-4 text-center">
          <Link to="/login" className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors">
            &larr; Back
          </Link>
        </p>
      </div>
    </div>
  );
}
