"""
Document endpoints: upload, list, get, delete.

Upload flow: save the file, create a Document row (status="processing"),
extract text, chunk it, save Chunk rows, then flip status to "ready" or
"failed". All scoped to the authenticated user via get_current_user.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.schemas.document import ChunkRead, DocumentRead
from app.services.ingestion import (
    SUPPORTED_CONTENT_TYPES,
    UnsupportedFileTypeError,
    chunk_text,
    extract_text,
)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Supported: PDF, DOCX, TXT.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    document = Document(
        user_id=current_user.id,
        filename=file.filename or "untitled",
        content_type=file.content_type,
        file_size_bytes=len(file_bytes),
        status="processing",
    )
    db.add(document)
    await db.flush()  # assigns document.id without committing yet

    try:
        text = extract_text(file_bytes, file.content_type)
        pieces = chunk_text(text)

        if not pieces:
            document.status = "failed"
            document.error_message = "No extractable text found in file."
        else:
            for i, content in enumerate(pieces):
                db.add(Chunk(document_id=document.id, chunk_index=i, content=content))
            document.status = "ready"

    except UnsupportedFileTypeError as e:
        document.status = "failed"
        document.error_message = str(e)
    except Exception as e:
        document.status = "failed"
        document.error_message = f"Processing error: {e}"

    await db.commit()
    await db.refresh(document)
    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{document_id}/chunks", response_model=list[ChunkRead])
async def list_document_chunks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Chunk]:
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    if doc_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunk_result = await db.execute(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
    )
    return list(chunk_result.scalars().all())


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await db.delete(document)  # cascades to chunks via ondelete="CASCADE"
    await db.commit()