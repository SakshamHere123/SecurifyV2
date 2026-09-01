import { useState } from "react";
import PolicyUploadForm from "../components/PolicyUploadForm";
import PolicyList from "../components/PolicyList";

export default function Admin() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Admin panel</h1>
        <p className="text-sm text-slate-500">Manage your organization's security policies.</p>
      </div>

      <PolicyUploadForm onUploaded={() => setRefreshKey((k) => k + 1)} />

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Uploaded policies</h2>
        <PolicyList refreshKey={refreshKey} />
      </div>
    </div>
  );
}