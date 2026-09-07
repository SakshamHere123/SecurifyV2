import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

// Maps a scan's status string to a badge style. Backend status constants
// live in scan_service.py / controller_agent.py, which weren't included in
// this upload -- pattern-matching keywords here (rather than hardcoding
// exact strings like "completed") means this keeps working even if the
// backend's precise wording changes.
function statusBadge(status) {
  const s = (status || "").toLowerCase();
  if (s.includes("fail") || s.includes("error")) {
    return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
  }
  if (s.includes("complete") || s.includes("success") || s.includes("done")) {
    return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
  }
  // Anything else (queued/running/etc.) reads as in-progress.
  return "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse";
}

export default function ScanHistory({ refreshKey }) {
  const navigate = useNavigate();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Same refetch-on-refreshKey pattern as PolicyList: Dashboard bumps this
  // right after a scan finishes, so the new row shows up without a manual
  // page reload.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .get("/scans")
      .then((res) => {
        if (!cancelled) setScans(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load scan history.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-6 border rounded-xl border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="w-4 h-4 border-2 rounded-full border-cyan-500 border-t-transparent animate-spin" />
        <p className="text-sm tracking-wide text-slate-400">Loading scan history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm border rounded-xl border-rose-500/20 bg-rose-500/5 text-rose-400">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        {error}
      </div>
    );
  }

  if (scans.length === 0) {
    return (
      <div className="p-10 text-center border bg-slate-900/40 border-slate-800/80 rounded-xl backdrop-blur-sm">
        <div className="inline-flex items-center justify-center w-10 h-10 mb-3 border rounded-lg bg-slate-800/80 border-slate-700/50 text-slate-500">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-slate-300">No scans recorded</p>
        <p className="mt-1 text-xs text-slate-500">Execute a scan above to inspect findings and remediation history.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden border shadow-2xl bg-slate-900/60 border-slate-800/80 rounded-xl backdrop-blur-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/40 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
              <th className="px-5 py-3.5">File</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Findings</th>
              <th className="px-5 py-3.5">Retries</th>
              <th className="px-5 py-3.5 text-right">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {scans.map((s) => (
              <tr
                key={s.scan_id}
                onClick={() => navigate(`/scans/${s.scan_id}`)}
                className="transition-colors duration-150 cursor-pointer group hover:bg-slate-800/40"
              >
                <td className="px-5 py-3.5 font-mono text-xs text-cyan-400 group-hover:text-cyan-300 transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-500/50 group-hover:bg-cyan-400" />
                    {s.filename || "—"}
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-medium uppercase tracking-wider ${statusBadge(
                      s.status
                    )}`}
                  >
                    {s.status}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-200">
                      {s.resolved_findings}
                      <span className="text-slate-500">/{s.total_findings}</span>
                    </span>
                    <span className="text-[11px] text-slate-400 font-normal">resolved</span>
                  </div>
                </td>
                <td className="px-5 py-3.5 font-mono text-xs text-slate-400">
                  {s.retry_count}
                </td>
                <td className="px-5 py-3.5 text-right font-mono text-xs text-slate-500 whitespace-nowrap">
                  {new Date(s.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}