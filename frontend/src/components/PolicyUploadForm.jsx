import { useState, useRef } from "react";
import apiClient from "../api/client";

export default function PolicyUploadForm({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text }
  const inputRef = useRef(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage(null);

    // Files must go as multipart/form-data, not JSON -- FastAPI's
    // UploadFile parameter on the backend expects exactly this format.
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiClient.post("/policy/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage({
        type: "success",
        text: `Uploaded "${res.data.filename}" (version ${res.data.version}, ${res.data.chunks_indexed} chunks indexed).`,
      });
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.(); // lets the parent page refresh the policy list (Part 4.3)
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Upload failed. Try a PDF, Markdown, or .txt file.",
      });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6">
      <h2 className="text-sm font-semibold text-slate-900 mb-1">Upload a security policy</h2>
      <p className="text-sm text-slate-500 mb-4">
        PDF, Markdown, or .txt. Re-uploading the same filename creates a new version rather
        than overwriting the old one.
      </p>

      <form onSubmit={handleUpload} className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.md,.txt"
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
        />

        {message && (
          <p className={`text-sm ${message.type === "success" ? "text-green-600" : "text-red-600"}`}>
            {message.text}
          </p>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="bg-slate-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload policy"}
        </button>
      </form>
    </div>
  );
}
