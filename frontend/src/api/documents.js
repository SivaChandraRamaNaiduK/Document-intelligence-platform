/**
 * Document API calls: upload, list, delete.
 */
import client from "./client";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments() {
  const { data } = await client.get("/documents");
  return data;
}

export async function deleteDocument(documentId) {
  await client.delete(`/documents/${documentId}`);
}