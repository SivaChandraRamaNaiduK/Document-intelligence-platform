import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as documentsApi from "../api/documents";
import { streamChat } from "../api/chat";

const ROUTE_STYLES = {
  qa: "bg-blue-500/20 text-blue-300",
  summarize: "bg-purple-500/20 text-purple-300",
  analyze: "bg-orange-500/20 text-orange-300",
};

function SourceCitation({ source }) {
  const [expanded, setExpanded] = useState(false);
  const preview = source.content.slice(0, 150);
  const isTruncated = source.content.length > 150;

  return (
    <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-slate-300 font-medium">
          {source.filename} · chunk {source.chunk_index}
        </span>
        {source.similarity_score < 1 && (
          <span className="text-slate-500 text-xs">
            {(source.similarity_score * 100).toFixed(0)}% match
          </span>
        )}
      </div>
      <p className="text-slate-400 whitespace-pre-wrap">
        {expanded ? source.content : preview}
        {!expanded && isTruncated && "..."}
      </p>
      {isTruncated && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-blue-400 hover:underline text-xs mt-1"
        >
          {expanded ? "Show less" : "Show full text"}
        </button>
      )}
    </div>
  );
}

export default function ChatPage() {
  const { user, logout } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [messages, setMessages] = useState([]); // { role, content, route, sources, latencyMs }
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    documentsApi.listDocuments().then((docs) => {
      setDocuments(docs.filter((d) => d.status === "ready"));
    });
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function toggleDocSelection(docId) {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  }

  async function handleSend(e) {
    e.preventDefault();
    const message = input.trim();
    if (!message || isStreaming) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsStreaming(true);

    // Placeholder assistant message that we'll fill in as tokens arrive
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", route: null, sources: [], latencyMs: null },
    ]);

    await streamChat(message, selectedDocIds, {
      onMeta: (route, sources) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, route, sources };
          return updated;
        });
      },
      onToken: (text) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, content: last.content + text };
          return updated;
        });
      },
      onDone: (latencyMs) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, latencyMs };
          return updated;
        });
        setIsStreaming(false);
      },
      onError: (errorMsg) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: `Error: ${errorMsg}`,
            route: null,
            sources: [],
          };
          return updated;
        });
        setIsStreaming(false);
      },
    });
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <div className="border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-bold text-white">Chat</h1>
          <Link to="/documents" className="text-sm text-slate-400 hover:text-white">
            Documents
          </Link>
        </div>
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

      <div className="flex-1 flex overflow-hidden">
        {/* Document selector sidebar */}
        <div className="w-64 border-r border-slate-800 p-4 overflow-y-auto shrink-0">
          <h2 className="text-slate-300 font-medium text-sm mb-3">
            Documents {selectedDocIds.length > 0 && `(${selectedDocIds.length} selected)`}
          </h2>
          <p className="text-slate-500 text-xs mb-3">
            {selectedDocIds.length === 0
              ? "None selected — searches across all your documents."
              : "Searching only selected documents."}
          </p>
          <div className="space-y-1">
            {documents.map((doc) => (
              <label
                key={doc.id}
                className="flex items-start gap-2 p-2 rounded hover:bg-slate-800 cursor-pointer text-sm"
              >
                <input
                  type="checkbox"
                  checked={selectedDocIds.includes(doc.id)}
                  onChange={() => toggleDocSelection(doc.id)}
                  className="mt-1"
                />
                <span className="text-slate-300 break-words">{doc.filename}</span>
              </label>
            ))}
            {documents.length === 0 && (
              <p className="text-slate-500 text-sm">
                No ready documents yet.{" "}
                <Link to="/documents" className="text-blue-400 hover:underline">
                  Upload one
                </Link>
              </p>
            )}
          </div>
        </div>

        {/* Message list */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
            {messages.length === 0 && (
              <p className="text-slate-500 text-center mt-12">
                Ask a question about your documents to get started.
              </p>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={msg.role === "user" ? "flex justify-end" : ""}>
                {msg.role === "user" ? (
                  <div className="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-lg">
                    {msg.content}
                  </div>
                ) : (
                  <div className="max-w-2xl">
                    <div className="flex items-center gap-2 mb-1.5">
                      {msg.route && (
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROUTE_STYLES[msg.route] ?? "bg-slate-600 text-slate-300"}`}
                        >
                          {msg.route}
                        </span>
                      )}
                      {msg.latencyMs != null && (
                        <span className="text-slate-500 text-xs">
                          {(msg.latencyMs / 1000).toFixed(1)}s
                        </span>
                      )}
                    </div>
                    <div className="bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3 text-slate-100 whitespace-pre-wrap">
                      {msg.content || (
                        <span className="text-slate-500">Thinking...</span>
                      )}
                    </div>

                    {msg.sources && msg.sources.length > 0 && (
                      <details className="mt-2">
                        <summary className="text-slate-400 text-sm cursor-pointer hover:text-slate-300">
                          {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
                        </summary>
                        <div className="mt-2 space-y-2">
                          {msg.sources.map((source) => (
                            <SourceCitation key={source.chunk_id} source={source} />
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="border-t border-slate-800 p-4 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={isStreaming}
              className="flex-1 rounded-md bg-slate-800 border border-slate-700 px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-5 rounded-md transition-colors"
            >
              {isStreaming ? "..." : "Send"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}