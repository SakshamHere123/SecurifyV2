import { useState } from "react";
import PolicyUploadForm from "../components/PolicyUploadForm";
import PolicyList from "../components/PolicyList";
import { useAuth } from "../context/AuthContext";

function OrgIdCard() {
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(user.org_id);
    } catch {
      // navigator.clipboard can be unavailable (older browser, non-HTTPS
      // context) -- fall back to the old execCommand trick so copy still
      // works instead of silently doing nothing.
      const el = document.createElement("textarea");
      el.value = user.org_id;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.focus();
      el.select();
      try {
        document.execCommand("copy");
      } catch {
        /* ignore -- nothing more we can do */
      }
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="relative p-5 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-amber-500/40 to-transparent pointer-events-none" />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20 uppercase tracking-wider">
              Invite teammates
            </span>
          </div>
          <p className="text-xs leading-relaxed text-slate-400">
            Share this Org ID with your team. They'll enter it on the{" "}
            <span className="text-slate-300">employee sign-up</span> page to join{" "}
            {user?.org_name ? (
              <span className="text-slate-300">{user.org_name}</span>
            ) : (
              "your organization"
            )}{" "}
            -- they'll only be able to run scans, not upload policies.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <code className="px-3 py-2 text-xs font-mono rounded-lg bg-slate-950/80 border border-slate-800 text-slate-200 max-w-[220px] sm:max-w-[260px] truncate">
            {user?.org_id}
          </code>
          <button
            type="button"
            onClick={handleCopy}
            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all duration-150 shrink-0 cursor-pointer ${
              copied
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                : "bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border-amber-500/30"
            }`}
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Admin() {
  // Bumping this after a successful upload tells PolicyList to refetch --
  // that's the whole connection between the two components below.
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="max-w-5xl space-y-8 font-sans text-slate-100">
      {/* Enterprise Security Header */}
      <div className="flex flex-col gap-4 pb-6 border-b sm:flex-row sm:items-center sm:justify-between border-slate-800/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.7)] ring-2 ring-cyan-500/20 animate-pulse" />
            <h1 className="text-xl font-semibold tracking-tight text-slate-100">
              Admin Governance Panel
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase tracking-wider">
              SecOps Core
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Configure, enforce, and audit organization-wide security policies and compliance benchmarks.
          </p>
        </div>

        {/* Status indicator badge */}
        <div className="flex items-center self-start gap-2 sm:self-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
            <span>POLICY_GUARD_ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Org ID / Invite Section */}
      <OrgIdCard />

      {/* Policy Upload Section */}
      <div className="relative p-6 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent pointer-events-none" />
        <PolicyUploadForm onUploaded={() => setRefreshKey((k) => k + 1)} />
      </div>

      {/* Uploaded Policies Audit & Management Section */}
      <div className="pt-2 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-xs font-semibold tracking-widest uppercase text-slate-300">
              Active Policy Benchmarks
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800/80 text-cyan-400 border border-slate-700/60">
              SYNC_STATE: {refreshKey}
            </span>
          </div>
        </div>

        <div className="p-5 border shadow-sm bg-slate-900/40 backdrop-blur-sm border-slate-800/80 rounded-xl ring-1 ring-white/5">
          <PolicyList refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  );
}