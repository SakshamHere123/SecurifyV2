import { useState } from "react";
import ScanUploadForm from "../components/ScanUploadForm";
import ScanHistory from "../components/ScanHistory";

export default function Dashboard() {
  // Bumping this after a completed scan tells ScanHistory to refetch --
  // same pattern as Admin's PolicyList/refreshKey.
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastScan, setLastScan] = useState(null);

  function handleScanComplete(scan) {
    setLastScan(scan);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="max-w-4xl space-y-8 font-sans text-slate-100">
      {/* Dashboard Header with Telemetry Status Badge */}
      <div className="flex flex-col gap-4 pb-6 border-b sm:flex-row sm:items-center sm:justify-between border-slate-800/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold tracking-tight text-slate-100">
              Security Dashboard
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase tracking-wider">
              IaC Analysis
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Upload and inspect Terraform manifests for misconfigurations and policy violations.
          </p>
        </div>

        <div className="flex items-center self-start gap-2 sm:self-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
            <span>SCANNER_READY</span>
          </div>
        </div>
      </div>

      {/* Upload Form Section */}
      <div className="p-6 border shadow-sm bg-slate-900/40 backdrop-blur-sm border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <ScanUploadForm onScanComplete={handleScanComplete} />
      </div>

      {/* Real-time Scan Completion Alert */}
      {lastScan && (
        <div className="relative overflow-hidden bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-4 shadow-[0_4px_20px_rgba(16,185,129,0.08)]">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 p-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-400 block shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold tracking-wide uppercase text-emerald-300">
                  Scan Execution Succeeded
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/20 text-emerald-200 border border-emerald-500/30">
                  {lastScan.retry_count} remediation attempt(s)
                </span>
              </div>
              <p className="text-xs leading-relaxed text-slate-300">
                Scan complete -- {lastScan.retry_count} remediation attempt(s). See it in the history
                below; the detail view (findings, diff, downloads) lands in Part 6.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Scan History Audit Log Section */}
      <div className="pt-2 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-200 tracking-wide uppercase font-mono text-[11px]">
              Audit Log & History
            </h2>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
              SYNC_REFRESH: {refreshKey}
            </span>
          </div>
        </div>

        <div className="p-4 border shadow-sm bg-slate-900/40 backdrop-blur-sm border-slate-800/80 rounded-xl ring-1 ring-white/5">
          <ScanHistory refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  );
}