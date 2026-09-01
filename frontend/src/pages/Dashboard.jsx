import { useState } from "react";
import ScanUploadForm from "../components/ScanUploadForm";

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastScan, setLastScan] = useState(null);

  function handleScanComplete(scan) {
    setLastScan(scan);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Upload Terraform to scan for security issues.</p>
      </div>

      <ScanUploadForm onScanComplete={handleScanComplete} />

      {lastScan && (
        <div className="p-4 text-sm text-green-800 border border-green-200 bg-green-50 rounded-xl">
          Scan complete -- {lastScan.retry_count} remediation attempt(s). Full history table lands
          in Part 5.3, and the detail view (findings, diff, downloads) in Part 6.
        </div>
      )}
    </div>
  );
}