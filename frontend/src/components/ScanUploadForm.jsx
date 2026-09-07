import { useState, useRef, useEffect } from "react";
import apiClient from "../api/client";

// Keys match exactly what the backend's current_step field reports --
// this list is no longer a guess, it's the real vocabulary the pipeline
// uses (see controller_agent.py's on_step calls).
const STAGE_KEYS = ["parsing", "static_analysis", "analyzing", "remediating", "validating"];
const STAGE_LABELS = {
  parsing: "Parsing Terraform",
  static_analysis: "Running static analysis",
  analyzing: "Analyzing with AI",
  remediating: "Remediating violations",
  validating: "Validating fixes",
};

const POLL_INTERVAL_MS = 2000;

export default function ScanUploadForm({ onScanComplete }) {
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [currentStep, setCurrentStep] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    return () => stopPolling(); // avoid setState-after-unmount if the user navigates away mid-scan
  }, []);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  // Polls the REAL scan status/current_step from the backend -- this is
  // the Phase 7 change. Phase 6's version faked stage advancement with a
  // timer because /scan/run blocked until everything finished; now
  // /scan/run returns instantly and this poll is the only way to find out
  // what's actually happening, because it's genuinely still happening
  // somewhere else (the Celery worker).
  function startPolling(scanId) {
    pollRef.current = setInterval(async () => {
      try {
        const res = await apiClient.get(`/scan/${scanId}`);
        const data = res.data;

        if (data.status === "completed") {
          stopPolling();
          setScanning(false);
          onScanComplete?.(data);
        } else if (data.status === "failed") {
          stopPolling();
          setScanning(false);
          setError("Scan failed while " + (STAGE_LABELS[data.current_step] || "processing") + ".");
        } else {
          setCurrentStep(data.current_step);
        }
      } catch {
        // A transient network hiccup on one poll shouldn't kill the whole
        // scan -- just try again on the next interval tick.
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setCurrentStep(null);
    setScanning(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiClient.post("/scan/run", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      startPolling(res.data.scan_id);
    } catch (err) {
      setError(err.response?.data?.detail || "Scan failed to start. Check that your file is valid Terraform.");
      setScanning(false);
    }
  }

  return (
    <div className="relative p-6 overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
      {/* Decorative top ambient border glow */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent pointer-events-none" />

      {/* Header section with telemetry badge */}
      <div className="flex items-start justify-between gap-4 pb-4 mb-5 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-sm font-semibold tracking-wide uppercase text-slate-100">
              Upload Terraform to Scan
            </h2>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase tracking-wider">
              Static + AI
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Provide a single <span className="font-mono text-cyan-300">.tf</span> configuration file. Analysis may take up to a minute.
          </p>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium bg-slate-950/80 border border-slate-800 text-slate-400">
          <span className={`w-1.5 h-1.5 rounded-full ${scanning ? "bg-amber-400 animate-pulse" : "bg-cyan-400"}`} />
          {scanning ? "EXEC_PIPELINE" : "READY_FOR_INGEST"}
        </div>
      </div>

      {!scanning ? (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative p-4 transition-colors border border-dashed rounded-xl border-slate-700/80 bg-slate-950/50 hover:border-slate-600 focus-within:border-cyan-500/60 focus-within:ring-1 focus-within:ring-cyan-500/30">
            <input
              ref={inputRef}
              type="file"
              accept=".tf"
              onChange={(e) => setFile(e.target.files[0] || null)}
              className="block w-full font-mono text-xs cursor-pointer text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border file:border-cyan-500/30 file:text-xs file:font-semibold file:font-mono file:bg-cyan-500/10 file:text-cyan-300 hover:file:bg-cyan-500/20 hover:file:border-cyan-500/50 file:transition-colors file:cursor-pointer"
            />
            {file && (
              <div className="mt-2.5 flex items-center gap-2 pt-2.5 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                <span className="truncate text-slate-300">Selected: {file.name}</span>
                <span className="text-slate-500">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            )}
          </div>

          {error && (
            <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0 shadow-[0_0_6px_rgba(244,63,94,0.6)]" />
              <p className="font-mono text-xs font-medium leading-relaxed text-rose-300">
                {error}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={!file}
            className="w-full sm:w-auto min-w-[140px] px-4 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider font-mono transition-all duration-150 border bg-cyan-500/10 text-cyan-300 border-cyan-500/30 hover:bg-cyan-500/20 hover:border-cyan-500/50 active:bg-cyan-500/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            Run scan
          </button>
        </form>
      ) : (
        <ScanProgress currentStep={currentStep} />
      )}
    </div>
  );
}

function ScanProgress({ currentStep }) {
  // null current_step means the worker hasn't picked the job up yet, or
  // hasn't reported its first step -- render everything as still queued
  // rather than guessing stage 0 is "in progress."
  const activeIndex = currentStep ? STAGE_KEYS.indexOf(currentStep) : -1;

  return (
    <div className="space-y-4">
      <div className="p-4 space-y-3 border rounded-xl bg-slate-950/60 border-slate-800/80">
        {STAGE_KEYS.map((key, i) => {
          const state = i < activeIndex ? "done" : i === activeIndex ? "active" : "pending";
          return (
            <div
              key={key}
              className={`flex items-center justify-between p-2 rounded-lg transition-all duration-200 border ${
                state === "active"
                  ? "bg-slate-900/90 border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.08)]"
                  : state === "done"
                  ? "bg-slate-900/30 border-transparent"
                  : "bg-transparent border-transparent opacity-50"
              }`}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 transition-all duration-200 ${
                    state === "done"
                      ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                      : state === "active"
                      ? "bg-cyan-400 animate-ping shadow-[0_0_8px_rgba(34,211,238,0.9)]"
                      : "bg-slate-700"
                  }`}
                />
                <span
                  className={`text-xs font-mono tracking-wide ${
                    state === "done"
                      ? "text-slate-300 font-medium"
                      : state === "active"
                      ? "text-cyan-300 font-semibold"
                      : "text-slate-500"
                  }`}
                >
                  {STAGE_LABELS[key]}
                </span>
              </div>

              <span
                className={`text-[10px] font-mono tracking-widest uppercase px-2 py-0.5 rounded border ${
                  state === "done"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : state === "active"
                    ? "bg-cyan-500/10 text-cyan-300 border-cyan-500/30 animate-pulse"
                    : "bg-slate-800/40 text-slate-600 border-slate-800"
                }`}
              >
                {state === "done" ? "COMPLETE" : state === "active" ? "RUNNING" : "QUEUED"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-2 px-1 text-[11px] font-mono text-slate-500">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <p>
          Live status from the backend -- if remediation needs a retry, "Remediating" and
          "Validating" will light up again rather than the scan appearing stuck.
        </p>
      </div>
    </div>
  );
}