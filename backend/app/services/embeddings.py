"""
Embedding generation via Cohere's embed-english-v3.0 model.

Cohere's embed models require an `input_type` — "search_document" for text
being stored/indexed, "search_query" for text being searched with. Using
the wrong one silently degrades retrieval quality, so this distinction
matters and is not just a formality.
"""
import cohere

from app.core.config import get_settings

settings = get_settings()

_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

EMBEDDING_MODEL = "embed-english-v3.0"
BATCH_SIZE = 96  # Cohere's per-request limit for embed-v3


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of chunk texts for storage. Batches requests to stay
    under Cohere's per-call limit.
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = _client.embed(
            texts=batch,
            model=EMBEDDING_MODEL,
            input_type="search_document",
            embedding_types=["float"],
        )
        all_embeddings.extend(response.embeddings.float_)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    response = _client.embed(
        texts=[text],
        model=EMBEDDING_MODEL,
        input_type="search_query",
        embedding_types=["float"],
    )
    return response.embeddings.float_[0]