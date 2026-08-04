/**
 * Chat API — consumes the SSE stream from POST /chat/stream.
 *
 * Uses the native fetch API rather than axios, since axios doesn't support
 * reading a streaming response body incrementally in the browser. This
 * means it bypasses the axios client's auto-refresh interceptor, so we
 * read the access token directly and let the caller handle 401s.
 *
 * onMeta(route, sources)  — called once, as soon as routing/retrieval finish
 * onToken(text)            — called for each incremental chunk of the answer
 * onDone(latencyMs)        — called when the stream completes
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function streamChat(message, documentIds, { onMeta, onToken, onDone, onError }) {
  const accessToken = localStorage.getItem("access_token");

  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      message,
      document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    onError?.(errorBody.detail || `Request failed (${response.status})`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line ("\n\n")
    const events = buffer.split("\n\n");
    buffer = events.pop(); // last part may be incomplete, keep it for next chunk

    for (const rawEvent of events) {
      const line = rawEvent.trim();
      if (!line.startsWith("data: ")) continue;

      const jsonStr = line.slice("data: ".length);
      const event = JSON.parse(jsonStr);

      if (event.type === "meta") {
        onMeta?.(event.route, event.sources);
      } else if (event.type === "token") {
        onToken?.(event.text);
      } else if (event.type === "done") {
        onDone?.(event.latency_ms);
      }
    }
  }
}