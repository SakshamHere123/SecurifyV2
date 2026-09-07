import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import apiClient from "../api/client";
import DiffViewer from "../components/DiffViewer";
import DownloadButtons from "../components/DownloadButtons";
import UsageSummary from "../components/UsageSummary";

// Same keyword-matching approach as ScanHistory's statusBadge -- Checkov's
// exact severity strings (e.g. "HIGH" vs "High") live in static_scan.py /
// findings.py, which weren't included in this upload, so matching on
// substrings keeps this working regardless of exact casing/wording.
function severityBadge(severity) {
  const s = (severity || "").toLowerCase();
  if (s.includes("crit") || s.includes("high")) {
    return "bg-rose-500/10 text-rose-400 border border-rose-500/30";
  }
  if (s.includes("med") || s.includes("moderate")) {
    return "bg-amber-500/10 text-amber-400 border border-amber-500/30";
  }
  return "bg-slate-800/80 text-slate-400 border border-slate-700/60"; // low/info/unknown
}

function statusBadge(status) {
  const s = (status || "").toLowerCase();
  if (s.includes("fail") || s.includes("error")) {
    return "bg-rose-500/10 text-rose-400 border border-rose-500/30";
  }
  if (s.includes("complete") || s.includes("success") || s.includes("done")) {
    return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
  }
  return "bg-amber-500/10 text-amber-400 border border-amber-500/30";
}

// Findings' `resolved` / `static_tool_confirmed` fields are strings
// ("true"/"false") per the Finding model, not booleans -- this normalizes
// either that or an actual boolean, in case the API layer ever changes it.
function isTruthy(v) {
  return v === true || v === "true";
}

export default function ScanDetail() {
  const { scanId } = useParams();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .get(`/scan/${scanId}`)
      .then((res) => {
        if (!cancelled) setScan(res.data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err.response?.status === 404
              ? "Scan not found."
              : "Couldn't load this scan."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [scanId]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 py-12 font-mono text-sm text-slate-400">
        <span className="w-4 h-4 border-2 rounded-full border-cyan-400/30 border-t-cyan-400 animate-spin" />
        <span>Loading scan telemetry...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md space-y-4">
        <div className="flex items-start gap-3 p-4 border rounded-xl bg-rose-500/10 border-rose-500/20">
          <span className="w-2 h-2 rounded-full bg-rose-400 mt-1 shrink-0 shadow-[0_0_8px_rgba(244,63,94,0.7)]" />
          <p className="font-mono text-xs font-medium leading-relaxed text-rose-300">
            {error}
          </p>
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-1 font-mono text-xs transition-colors text-cyan-400 hover:text-cyan-300"
        >
          &larr; Back to dashboard
        </Link>
      </div>
    );
  }

  const filename = scan.input_tf_path ? scan.input_tf_path.split("/").pop() : "—";
  const findings = scan.findings || [];

  return (
    <div className="max-w-5xl space-y-8 font-sans text-slate-100">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-cyan-400 transition-colors"
        >
          &larr; Back to dashboard
        </Link>
      </div>

      {/* Summary header */}
      <div className="relative p-6 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent pointer-events-none" />

        <div className="flex flex-col gap-4 pb-5 mb-6 border-b sm:flex-row sm:items-start sm:justify-between border-slate-800/80">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.7)]" />
              <h1 className="font-mono text-base font-semibold tracking-tight sm:text-lg text-slate-100">
                {filename}
              </h1>
            </div>
            <p className="text-[11px] font-mono text-slate-500 tracking-wider">
              SCAN_ID: <span className="text-slate-400">{scan.scan_id}</span>
            </p>
          </div>

          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium uppercase tracking-wider self-start sm:self-auto ${statusBadge(
              scan.status
            )}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current shadow-[0_0_6px_currentColor]" />
            {scan.status}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4 sm:gap-6">
          <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
            <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
              Findings
            </dt>
            <dd className="font-mono text-base font-semibold text-slate-100">
              {findings.length}
            </dd>
          </div>
          <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
            <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
              Remediation Attempts
            </dt>
            <dd className="font-mono text-base font-semibold text-slate-100">
              {scan.retry_count}
            </dd>
          </div>
          <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
            <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
              Started
            </dt>
            <dd className="font-mono text-xs text-slate-300">
              {scan.created_at ? new Date(scan.created_at).toLocaleString() : "—"}
            </dd>
          </div>
          <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
            <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
              Completed
            </dt>
            <dd className="font-mono text-xs text-slate-300">
              {scan.completed_at ? new Date(scan.completed_at).toLocaleString() : "—"}
            </dd>
          </div>
        </dl>
      </div>

      {/* Findings table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-xs font-semibold tracking-widest uppercase text-slate-300">
              Detected Findings
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800/80 text-cyan-400 border border-slate-700/60">
              {findings.length} issues
            </span>
          </div>
        </div>

        {findings.length === 0 ? (
          <div className="p-8 text-center border bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
            <p className="font-mono text-xs text-slate-400">
              No security findings or policy violations detected for this configuration.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="border-b bg-slate-950/80 border-slate-800/80">
                  <tr>
                    <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                      Resource
                    </th>
                    <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                      Issue
                    </th>
                    <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                      Severity
                    </th>
                    <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                      Policy
                    </th>
                    <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="font-sans text-xs divide-y divide-slate-800/60">
                  {findings.map((f, i) => (
                    <tr
                      key={i}
                      className="align-top transition-colors hover:bg-slate-800/30"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-200 whitespace-nowrap">
                        <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                          {f.resource}
                        </span>
                      </td>
                      <td className="max-w-sm px-4 py-3 leading-relaxed text-slate-300">
                        {f.issue}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider ${severityBadge(
                            f.severity
                          )}`}
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400">
                        {f.policy_reference ? (
                          <span className="text-slate-400">{f.policy_reference}</span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider border ${
                            isTruthy(f.resolved)
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              : "bg-slate-800/60 text-slate-400 border-slate-700/60"
                          }`}
                        >
                          <span
                            className={`w-1 h-1 rounded-full ${
                              isTruthy(f.resolved) ? "bg-emerald-400" : "bg-slate-500"
                            }`}
                          />
                          {isTruthy(f.resolved) ? "Resolved" : "Unresolved"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* LLM usage & cost */}
      <div className="space-y-3">
        <h2 className="font-mono text-xs font-semibold tracking-widest uppercase text-slate-300">
          LLM Usage &amp; Cost
        </h2>
        <UsageSummary usage={scan.usage} />
      </div>

      {/* Diff viewer */}
      <div className="space-y-3">
        <h2 className="font-mono text-xs font-semibold tracking-widest uppercase text-slate-300">
          Remediation Diff
        </h2>
        <div className="p-5 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
          <DiffViewer scanId={scan.scan_id} hasOutput={!!scan.output_tf_path} />
        </div>
      </div>

      {/* Downloads */}
      <div className="space-y-3">
        <h2 className="font-mono text-xs font-semibold tracking-widest uppercase text-slate-300">
          Artifacts & Downloads
        </h2>
        <div className="p-5 border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
          <DownloadButtons
            scanId={scan.scan_id}
            hasOutput={!!scan.output_tf_path}
            hasReport={!!scan.report_path}
          />
        </div>
      </div>
    </div>
  );
}