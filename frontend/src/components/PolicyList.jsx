import { useState, useEffect } from "react";
import apiClient from "../api/client";

export default function PolicyList({ refreshKey }) {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    return <p className="text-sm text-slate-500">Loading policies...</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  if (policies.length === 0) {
    return (
      <div className="p-6 text-center bg-white border border-slate-200 rounded-xl">
        <p className="text-sm text-slate-500">No policies uploaded yet.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden bg-white border border-slate-200 rounded-xl">
      <table className="w-full text-sm">
        <thead className="border-b bg-slate-50 border-slate-200">
          <tr>
            <th className="px-4 py-2 font-medium text-left text-slate-500">Filename</th>
            <th className="px-4 py-2 font-medium text-left text-slate-500">Version</th>
            <th className="px-4 py-2 font-medium text-left text-slate-500">Uploaded</th>
          </tr>
        </thead>
        <tbody>
          {policies.map((p) => (
            <tr key={p.policy_id} className="border-b border-slate-100 last:border-0">
              <td className="px-4 py-2 text-slate-900">{p.filename}</td>
              <td className="px-4 py-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                  v{p.version}
                </span>
              </td>
              <td className="px-4 py-2 text-slate-500">
                {new Date(p.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}