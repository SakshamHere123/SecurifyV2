import { useState } from "react";
import PolicyUploadForm from "../components/PolicyUploadForm";
import PolicyList from "../components/PolicyList";

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