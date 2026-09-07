import { useState } from "react";
import apiClient from "../api/client";

// Pulls a filename out of a Content-Disposition header if the backend sent
// one (both download endpoints do, via FileResponse's `filename=` arg).
// Falls back to a sensible default if the header is missing or unparseable.
function filenameFromHeaders(headers, fallback) {
  const disposition = headers?.["content-disposition"];
  if (!disposition) return fallback;
  const match = disposition.match(/filename="?([^";]+)"?/);
  return match ? match[1] : fallback;
}

// Both download endpoints are auth-protected, so a plain <a href> can't be
// used directly -- it wouldn't carry the JWT the interceptor attaches.
// Instead we fetch the file as a blob through the shared apiClient, then
// hand the browser a throwaway object URL to save it.
async function triggerBlobDownload(url, fallbackFilename, onError) {
  try {
    const res = await apiClient.get(url, { responseType: "blob" });
    const blobUrl = window.URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filenameFromHeaders(res.headers, fallbackFilename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (err) {
    onError(
      err.response?.status === 404
        ? "That file isn't available for this scan."
        : "Download failed. Try again."
    );
  }
}

function DownloadButton({ label, downloading, disabled, disabledReason, onClick }) {
  const button = (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || downloading}
      className={`relative group inline-flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-xs font-mono font-medium tracking-wide transition-all duration-150 border ${
        disabled || downloading
          ? "bg-slate-900/40 text-slate-600 border-slate-800/60 opacity-50 cursor-not-allowed shadow-none"
          : "bg-slate-900/80 hover:bg-slate-800/80 active:bg-slate-850 text-slate-200 hover:text-cyan-300 border-slate-700/80 hover:border-cyan-500/40 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] cursor-pointer"
      }`}
    >
      {downloading ? (
        <span className="w-3.5 h-3.5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin shrink-0" />
      ) : (
        <svg
          className={`w-4 h-4 transition-colors shrink-0 ${
            disabled ? "text-slate-600" : "text-cyan-400/80 group-hover:text-cyan-300"
          }`}
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M10 3v10m0 0-3.5-3.5M10 13l3.5-3.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M4 15v1a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-1" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      <span>{downloading ? "Preparing…" : label}</span>
    </button>
  );

  if (!disabled || !disabledReason) return button;

  return (
    <span title={disabledReason} className="inline-block cursor-not-allowed">
      {button}
    </span>
  );
}

export default function DownloadButtons({ scanId, hasOutput, hasReport }) {
  const [downloadingTf, setDownloadingTf] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [error, setError] = useState(null);

  const handleDownloadTf = async () => {
    setError(null);
    setDownloadingTf(true);
    await triggerBlobDownload(`/scan/${scanId}/download/tf`, `${scanId}-remediated.tf`, setError);
    setDownloadingTf(false);
  };

  const handleDownloadReport = async () => {
    setError(null);
    setDownloadingReport(true);
    await triggerBlobDownload(`/scan/${scanId}/download/report`, `securify-report-${scanId}.pdf`, setError);
    setDownloadingReport(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <DownloadButton
          label="Download remediated .tf"
          downloading={downloadingTf}
          disabled={!hasOutput}
          disabledReason="No remediated Terraform file for this scan."
          onClick={handleDownloadTf}
        />
        <DownloadButton
          label="Download report (PDF)"
          downloading={downloadingReport}
          disabled={!hasReport}
          disabledReason="No report has been generated for this scan."
          onClick={handleDownloadReport}
        />
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 max-w-md">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0 shadow-[0_0_6px_rgba(244,63,94,0.6)]" />
          <p className="font-mono text-xs font-medium leading-relaxed text-rose-300">
            {error}
          </p>
        </div>
      )}
    </div>
  );
}