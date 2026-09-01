import { useState, useRef, useEffect } from "react";
import apiClient from "../api/client";

const STAGES = [
  "Parsing Terraform",
  "Running static analysis",
  "Analyzing with AI",
  "Remediating violations",
  "Validating fixes",
];

const STAGE_INTERVAL_MS = 3500;

export default function ScanUploadForm({ onScanComplete }) {
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    return () => stopStageTimer();
  }, []);

  function startStageTimer() {
    setStageIndex(0);
    intervalRef.current = setInterval(() => {
      setStageIndex((i) => (i < STAGES.length - 1 ? i + 1 : i));
    }, STAGE_INTERVAL_MS);
  }

  function stopStageTimer() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setScanning(true);
    startStageTimer();

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiClient.post("/scan/run", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onScanComplete?.(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Scan failed. Check that your file is valid Terraform.");
    } finally {
      stopStageTimer();
      setScanning(false);
    }
  }

  return (
    <div className="p-6 bg-white border border-slate-200 rounded-xl">
      <h2 className="mb-1 text-sm font-semibold text-slate-900">Upload Terraform to scan</h2>
      <p className="mb-4 text-sm text-slate-500">A single .tf file. This can take up to a minute.</p>

      {!scanning ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            ref={inputRef}
            type="file"
            accept=".tf"
            onChange={(e) => setFile(e.target.files[0] || null)}
            className="block w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={!file}
            className="px-4 py-2 text-sm font-medium text-white rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50"
          >
            Run scan
          </button>
        </form>
      ) : (
        <ScanProgress stageIndex={stageIndex} />
      )}
    </div>
  );
}

function ScanProgress({ stageIndex }) {
  return (
    <div>
      <div className="mb-3 space-y-2">
        {STAGES.map((label, i) => {
          const state = i < stageIndex ? "done" : i === stageIndex ? "active" : "pending";
          return (
            <div key={label} className="flex items-center gap-3">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  state === "done"
                    ? "bg-green-500"
                    : state === "active"
                    ? "bg-slate-900 animate-pulse"
                    : "bg-slate-200"
                }`}
              />
              <span className={`text-sm ${state === "pending" ? "text-slate-400" : "text-slate-700"}`}>
                {label}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-slate-400">
        Processing may take longer than shown above -- this reflects typical progress, not a live signal.
      </p>
    </div>
  );
}