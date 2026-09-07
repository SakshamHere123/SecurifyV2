import { useState, useEffect } from "react";
import apiClient from "../api/client";

// --- Shape normalization -------------------------------------------------
// diff_builder.py (build_scan_diffs) is stubbed out in this upload, so the
// exact JSON shape of each entry in `diffs` isn't known for certain. This
// normalizes the couple of shapes a per-resource line-diff builder like
// this most plausibly returns, so the component doesn't break if it's one
// or the other. If the real shape turns out to be different, only this
// function needs to change -- the rendering below just consumes
// { resource, lines: [{ type: "add"|"remove"|"context", content }] }.

function normalizeLineType(raw) {
  const t = (raw || "").toString().toLowerCase();
  if (t.startsWith("add") || t === "+" || t.startsWith("insert")) return "add";
  if (t.startsWith("remov") || t.startsWith("delet") || t === "-") return "remove";
  return "context";
}

function linesFromUnifiedDiffText(text) {
  return text
    .split("\n")
    .filter((l) => !l.startsWith("---") && !l.startsWith("+++") && !l.startsWith("@@"))
    .map((line) => {
      if (line.startsWith("+")) return { type: "add", content: line.slice(1) };
      if (line.startsWith("-")) return { type: "remove", content: line.slice(1) };
      return { type: "context", content: line.startsWith(" ") ? line.slice(1) : line };
    });
}

function normalizeDiffEntry(entry, i) {
  const resource = entry.resource || entry.resource_address || entry.name || `Resource ${i + 1}`;

  // Shape A: already line-typed, e.g. { lines: [{ type, content }] }
  if (Array.isArray(entry.lines)) {
    return {
      resource,
      lines: entry.lines.map((l) => ({
        type: normalizeLineType(l.type),
        content: l.content ?? l.text ?? "",
      })),
    };
  }

  // Shape B: raw unified-diff text, e.g. { diff: "@@ ...\n-old\n+new" }
  if (typeof entry.diff === "string") {
    return { resource, lines: linesFromUnifiedDiffText(entry.diff) };
  }

  // Shape C: full before/after blocks, no line-level diff -- fall back to
  // showing the whole old block removed and the whole new block added.
  if (typeof entry.before === "string" || typeof entry.after === "string") {
    const lines = [];
    (entry.before || "").split("\n").forEach((c) => lines.push({ type: "remove", content: c }));
    (entry.after || "").split("\n").forEach((c) => lines.push({ type: "add", content: c }));
    return { resource, lines };
  }

  // Unknown shape -- show raw JSON rather than silently dropping data.
  return { resource, lines: [{ type: "context", content: JSON.stringify(entry) }] };
}

function lineClasses(type) {
  if (type === "add") return "bg-emerald-500/10 text-emerald-300 border-l-2 border-emerald-500/80";
  if (type === "remove") return "bg-rose-500/10 text-rose-300 border-l-2 border-rose-500/80";
  return "text-slate-400 border-l-2 border-transparent hover:bg-slate-900/40";
}

function linePrefix(type) {
  if (type === "add") return "+";
  if (type === "remove") return "-";
  return " ";
}

// --- Component -------------------------------------------------------------

export default function DiffViewer({ scanId, hasOutput }) {
  const [diffs, setDiffs] = useState(null);
  const [loading, setLoading] = useState(hasOutput);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!hasOutput) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .get(`/scan/${scanId}/diff`)
      .then((res) => {
        if (!cancelled) setDiffs(res.data.diffs || []);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load the diff for this scan.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [scanId, hasOutput]);

  if (!hasOutput) {
    return (
      <div className="p-8 text-center border bg-slate-900/40 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <p className="font-mono text-xs text-slate-400">
          No remediated output for this scan -- nothing to diff.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-3 px-4 py-6 font-mono text-xs border bg-slate-950/40 border-slate-800/60 rounded-xl text-slate-400">
        <span className="w-3.5 h-3.5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
        <span>Loading unified diff telemetry...</span>
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

  const entries = (diffs || []).map(normalizeDiffEntry);

  if (entries.length === 0) {
    return (
      <div className="p-8 text-center border bg-slate-900/40 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <p className="font-mono text-xs text-slate-400">No changes to show.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map((entry, i) => (
        <div
          key={i}
          className="overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5"
        >
          <div className="px-4 py-2.5 bg-slate-950/80 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
              <span className="font-mono text-xs font-medium text-slate-200">
                {entry.resource}
              </span>
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-slate-900 border border-slate-700/60 text-slate-400">
              MODIFIED_RESOURCE
            </span>
          </div>
          <div className="py-2 overflow-x-auto font-mono text-xs bg-slate-950/90">
            {entry.lines.map((line, j) => (
              <div
                key={j}
                className={`px-4 py-0.5 whitespace-pre font-mono transition-colors leading-relaxed ${lineClasses(
                  line.type
                )}`}
              >
                <span className="inline-block w-4 font-bold opacity-75 select-none">
                  {linePrefix(line.type)}
                </span>
                {line.content}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}