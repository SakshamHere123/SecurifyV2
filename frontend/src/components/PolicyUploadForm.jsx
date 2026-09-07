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
    <div className="relative p-6 overflow-hidden border shadow-2xl bg-slate-900/60 border-slate-800/80 rounded-xl backdrop-blur-sm">
      {/* Subtle background glow effect */}
      <div className="absolute w-48 h-48 rounded-full pointer-events-none -top-24 -right-24 bg-cyan-500/5 blur-3xl" />

      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <h2 className="font-mono text-sm font-semibold tracking-wide uppercase text-slate-100">
              Upload Security Policy
            </h2>
          </div>
          <p className="text-xs leading-relaxed text-slate-400">
            Supported formats: <span className="font-mono text-cyan-300">.pdf</span>,{" "}
            <span className="font-mono text-cyan-300">.md</span>,{" "}
            <span className="font-mono text-cyan-300">.txt</span>. Re-uploading an existing file version increments the policy iteration rather than overwriting.
          </p>
        </div>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        <div className="relative group">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.md,.txt"
            onChange={(e) => setFile(e.target.files[0] || null)}
            className="block w-full text-xs text-slate-300 font-mono file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border file:border-slate-700/80 file:text-xs file:font-semibold file:bg-slate-800/90 file:text-cyan-300 hover:file:bg-slate-700/80 hover:file:border-cyan-500/40 file:transition-all cursor-pointer bg-slate-950/50 rounded-xl border border-slate-800/90 p-2 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {file && (
          <div className="flex items-center justify-between px-3 py-2 font-mono text-xs border rounded-lg bg-slate-800/40 border-slate-800 text-slate-300">
            <div className="flex items-center gap-2 truncate">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span className="truncate">{file.name}</span>
            </div>
            <span className="text-[11px] text-slate-500 whitespace-nowrap ml-2">
              {(file.size / 1024).toFixed(1)} KB
            </span>
          </div>
        )}

        {message && (
          <div
            className={`p-3 rounded-lg text-xs font-mono flex items-start gap-2.5 border ${
              message.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/20 text-rose-400"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                message.type === "success" ? "bg-emerald-400" : "bg-rose-400"
              }`}
            />
            <span className="leading-relaxed">{message.text}</span>
          </div>
        )}

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={!file || uploading}
            className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-xs font-semibold tracking-wide uppercase transition-all duration-150 bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 disabled:hover:bg-cyan-500 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/10 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
          >
            {uploading ? (
              <>
                <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                <span>Indexing Chunks...</span>
              </>
            ) : (
              <span>Upload Policy</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}