"""
Pydantic schemas for the /chat endpoint.
"""
import uuid

from pydantic import BaseModel

from app.schemas.search import SearchResult


class ChatRequest(BaseModel):
    message: str
    document_ids: list[uuid.UUID] | None = None  # None = search across all of the user's documents


class ChatResponse(BaseModel):
    answer: str
    route: str                       # "qa" | "summarize" | "analyze"
    sources: list[SearchResult]      # full chunk text + filename + chunk_index, for citations
    latency_ms: int