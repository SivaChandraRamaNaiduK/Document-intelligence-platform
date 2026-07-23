import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import * as documentsApi from "../api/documents";

const STATUS_STYLES = {
  processing: "bg-yellow-500/20 text-yellow-300",
  ready: "bg-green-500/20 text-green-300",
  failed: "bg-red-500/20 text-red-300",
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const { user, logout } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const fileInputRef = useRef(null);

  async function refreshList() {
    setIsLoadingList(true);
    try {
      const docs = await documentsApi.listDocuments();
      setDocuments(docs);
    } finally {
      setIsLoadingList(false);
    }
  }

  useEffect(() => {
    refreshList();
  }, []);

  async function handleFileSelected(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError("");
    setIsUploading(true);
    try {
      await documentsApi.uploadDocument(file);
      await refreshList();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setUploadError(typeof detail === "string" ? detail : "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      e.target.value = ""; // allow re-selecting the same file
    }
  }

  async function handleDelete(documentId) {
    setDeletingId(documentId);
    try {
      await documentsApi.deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 px-4 py-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm">{user?.email}</span>
            <button
              onClick={logout}
              className="text-sm text-slate-300 hover:text-white border border-slate-600 hover:border-slate-500 px-3 py-1.5 rounded-md transition-colors"
            >
              Log out
            </button>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-6 mb-6">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileSelected}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-md transition-colors"
          >
            {isUploading ? "Uploading & processing..." : "Upload a document (PDF, DOCX, or TXT)"}
          </button>
          {uploadError && (
            <p className="text-sm text-red-400 mt-2">{uploadError}</p>
          )}
        </div>

        <div className="bg-slate-800 rounded-xl divide-y divide-slate-700">
          {isLoadingList ? (
            <p className="text-slate-400 p-6">Loading documents...</p>
          ) : documents.length === 0 ? (
            <p className="text-slate-400 p-6">
              No documents yet — upload one to get started.
            </p>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-4">
                <div className="min-w-0">
                  <p className="text-white font-medium truncate">{doc.filename}</p>
                  <p className="text-slate-400 text-sm">
                    {formatBytes(doc.file_size_bytes)} ·{" "}
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                  {doc.status === "failed" && doc.error_message && (
                    <p className="text-red-400 text-xs mt-1">{doc.error_message}</p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-4">
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_STYLES[doc.status] ?? "bg-slate-600 text-slate-300"}`}
                  >
                    {doc.status}
                  </span>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-sm text-slate-400 hover:text-red-400 disabled:opacity-50 transition-colors"
                  >
                    {deletingId === doc.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}