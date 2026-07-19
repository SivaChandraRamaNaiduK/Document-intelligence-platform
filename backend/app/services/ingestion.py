"""
Document ingestion: text extraction + recursive token-aware chunking.

Chunking strategy: try to split on paragraph breaks first (keeps chunks
semantically coherent). If a paragraph is still too big, fall back to
splitting on sentences, then words. Chunk size is measured in actual LLM
tokens (via tiktoken), not characters, so chunks map predictably to what
an LLM will actually see.
"""
import re
from io import BytesIO

import tiktoken
from docx import Document as DocxDocument
from pypdf import PdfReader

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}

CHUNK_SIZE_TOKENS = 400      # target tokens per chunk
CHUNK_OVERLAP_TOKENS = 50    # tokens repeated between consecutive chunks

_encoding = tiktoken.get_encoding("cl100k_base")  # same tokenizer family as GPT-4/Claude-era models


class UnsupportedFileTypeError(Exception):
    pass


def extract_text(file_bytes: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        return _extract_pdf(file_bytes)
    elif content_type == "text/plain":
        return file_bytes.decode("utf-8", errors="ignore")
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(file_bytes)
    else:
        raise UnsupportedFileTypeError(f"Unsupported content type: {content_type}")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _token_count(text: str) -> int:
    return len(_encoding.encode(text))


def _split_on(text: str, pattern: str) -> list[str]:
    parts = re.split(pattern, text)
    return [p for p in parts if p.strip()]


def _recursive_split(text: str, max_tokens: int) -> list[str]:
    """
    Splits `text` into pieces each under max_tokens, trying progressively
    finer separators: paragraph breaks -> sentence breaks -> words.
    """
    if _token_count(text) <= max_tokens:
        return [text.strip()]

    # Try paragraph breaks first
    for pattern in [r"\n\s*\n", r"(?<=[.!?])\s+", r"\s+"]:
        pieces = _split_on(text, pattern)
        if len(pieces) > 1:
            break
    else:
        # Nothing to split on (single giant word/token) — return as-is
        return [text.strip()]

    # Recursively split any piece that's still too big
    result = []
    for piece in pieces:
        if _token_count(piece) > max_tokens:
            result.extend(_recursive_split(piece, max_tokens))
        else:
            result.append(piece.strip())
    return result


def chunk_text(
    text: str,
    chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """
    Recursively splits text into paragraph/sentence-aware pieces, then
    greedily packs those pieces into chunks up to chunk_size_tokens,
    carrying `overlap_tokens` worth of trailing content into the next
    chunk so context isn't lost at boundaries.
    """
    text = text.strip()
    if not text:
        return []

    pieces = _recursive_split(text, chunk_size_tokens)

    chunks: list[str] = []
    current_pieces: list[str] = []
    current_tokens = 0

    for piece in pieces:
        piece_tokens = _token_count(piece)

        if current_tokens + piece_tokens > chunk_size_tokens and current_pieces:
            # Flush current chunk
            chunks.append(" ".join(current_pieces))

            # Start next chunk with overlap: carry trailing pieces whose
            # combined tokens are closest to overlap_tokens
            overlap_pieces = []
            overlap_count = 0
            for p in reversed(current_pieces):
                pt = _token_count(p)
                if overlap_count + pt > overlap_tokens:
                    break
                overlap_pieces.insert(0, p)
                overlap_count += pt

            current_pieces = overlap_pieces
            current_tokens = overlap_count

        current_pieces.append(piece)
        current_tokens += piece_tokens

    if current_pieces:
        chunks.append(" ".join(current_pieces))

    return chunks