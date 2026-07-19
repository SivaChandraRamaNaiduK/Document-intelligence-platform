"""
Pydantic schemas for document upload, listing, and status responses.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkRead(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str

    model_config = {"from_attributes": True}