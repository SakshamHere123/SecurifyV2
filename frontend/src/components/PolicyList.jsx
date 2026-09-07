import { useState, useEffect } from "react";
import apiClient from "../api/client";

export default function PolicyList({ refreshKey }) {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Refetches whenever refreshKey changes -- the Admin page bumps this
  // after a successful upload, so a newly-added policy (or version) shows
  // up immediately without the user having to manually reload the page.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .get("/policies")
      .then((res) => {
        if (!cancelled) setPolicies(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load policies.");
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
      <div className="flex items-center gap-3 px-4 py-6 font-mono text-xs border bg-slate-950/40 border-slate-800/60 rounded-xl text-slate-400">
        <span className="w-3.5 h-3.5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
        <span>Retrieving active policy definitions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0 shadow-[0_0_6px_rgba(244,63,94,0.6)]" />
        <p className="font-mono text-xs font-medium leading-relaxed text-rose-300">
          {error}
        </p>
      </div>
    );
  }

  if (policies.length === 0) {
    return (
      <div className="p-8 text-center border bg-slate-950/40 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <p className="font-mono text-xs text-slate-400">
          No policies uploaded yet. Ingest OPA / Rego manifests above to establish guardrails.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden border shadow-xl bg-slate-950/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="border-b bg-slate-950/90 border-slate-800/80">
            <tr>
              <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                Filename
              </th>
              <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                Version
              </th>
              <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                Uploaded
              </th>
            </tr>
          </thead>
          <tbody className="font-sans text-xs divide-y divide-slate-800/60">
            {policies.map((p) => (
              <tr
                key={p.policy_id}
                className="align-middle transition-colors hover:bg-slate-800/30"
              >
                <td className="px-4 py-3 font-mono text-xs text-slate-200 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/80 shadow-[0_0_6px_rgba(34,211,238,0.6)]" />
                    <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
                      {p.filename}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    v{p.version}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}