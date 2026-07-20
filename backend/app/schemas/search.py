"""
Pydantic schemas for semantic search requests and citation-style responses.
"""
import uuid

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    document_ids: list[uuid.UUID] | None = None  # None = search across all of the user's documents
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    content: str          # full chunk text, per your citation preference
    similarity_score: float