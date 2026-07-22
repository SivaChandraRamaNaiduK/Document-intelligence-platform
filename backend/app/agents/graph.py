"""
Multi-agent RAG graph built with LangGraph.

Flow:
  router node -> classifies the query as qa / summarize / analyze
  retrieval node -> embeds the query, fetches relevant chunks via pgvector
  agent node (one of qa_agent / summarizer_agent / analysis_agent) -> generates the answer

The router and generation nodes both call Cohere's chat API. Retrieval
reuses the exact same search logic as the /documents/search endpoint,
just invoked directly against the DB session instead of over HTTP.
"""
import uuid
from typing import Literal, TypedDict

import cohere
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.embeddings import embed_query

settings = get_settings()
_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

CHAT_MODEL = "command-r-plus-08-2024"


class GraphState(TypedDict):
    query: str
    user_id: uuid.UUID
    document_ids: list[uuid.UUID] | None
    db: AsyncSession
    route: str
    retrieved: list[dict]   # chunk_id, document_id, filename, chunk_index, content, similarity_score
    answer: str


# ---------- Router node ----------

async def router_node(state: GraphState) -> GraphState:
    prompt = f"""Classify the following user query into exactly one category.
Respond with only one word: qa, summarize, or analyze.

- qa: a specific question expecting a direct answer
- summarize: asking for an overview or summary of document(s)
- analyze: asking for themes, entities, comparisons, or deeper analysis

Query: {state["query"]}"""

    response = _client.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    route = response.message.content[0].text.strip().lower()

    if route not in ("qa", "summarize", "analyze"):
        route = "qa"  # safe default if the model returns something unexpected

    return {**state, "route": route}


def route_decision(state: GraphState) -> Literal["qa", "summarize", "analyze"]:
    return state["route"]  # type: ignore[return-value]


# ---------- Retrieval node ----------

async def retrieval_node(state: GraphState) -> GraphState:
    # Summarization needs full document coverage, not a similarity match to
    # a vague instruction like "summarize this" — pull chunks in document
    # order instead, capped to keep the prompt a reasonable size.
    if state["route"] == "summarize" and state["document_ids"]:
        stmt = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.chunk_index,
                Chunk.content,
                Document.filename,
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.user_id == state["user_id"])
            .where(Chunk.document_id.in_(state["document_ids"]))
            .order_by(Chunk.document_id, Chunk.chunk_index)
            .limit(60)  # cap to keep the prompt within a reasonable token budget
        )
        result = await state["db"].execute(stmt)
        rows = result.all()

        retrieved = [
            {
                "chunk_id": row.id,
                "document_id": row.document_id,
                "filename": row.filename,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "similarity_score": 1.0,  # not similarity-ranked; full-document pass
            }
            for row in rows
        ]
        return {**state, "retrieved": retrieved}

    # Default path: qa / analyze, or summarize with no document specified
    query_vector = embed_query(state["query"])

    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.chunk_index,
            Chunk.content,
            Document.filename,
            Chunk.embedding.cosine_distance(query_vector).label("distance"),
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.user_id == state["user_id"])
        .where(Chunk.embedding.is_not(None))
    )

    if state["document_ids"]:
        stmt = stmt.where(Chunk.document_id.in_(state["document_ids"]))

    stmt = stmt.order_by("distance").limit(8)

    result = await state["db"].execute(stmt)
    rows = result.all()

    retrieved = [
        {
            "chunk_id": row.id,
            "document_id": row.document_id,
            "filename": row.filename,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "similarity_score": 1 - row.distance,
        }
        for row in rows
    ]

    return {**state, "retrieved": retrieved}


# ---------- Generation nodes ----------

def _build_context(retrieved: list[dict]) -> str:
    if not retrieved:
        return "No relevant document content was found."
    return "\n\n".join(
        f"[Source: {r['filename']}, chunk {r['chunk_index']}]\n{r['content']}" for r in retrieved
    )


async def qa_agent(state: GraphState) -> GraphState:
    context = _build_context(state["retrieved"])
    prompt = f"""Answer the question using ONLY the context below. If the context doesn't
contain the answer, say so clearly instead of guessing.

Context:
{context}

Question: {state["query"]}

Answer:"""

    response = _client.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    return {**state, "answer": response.message.content[0].text.strip()}


async def summarizer_agent(state: GraphState) -> GraphState:
    context = _build_context(state["retrieved"])
    prompt = f"""Summarize the following document content clearly and concisely,
covering the main points a reader would need to understand it.

Content:
{context}

Summary:"""

    response = _client.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    return {**state, "answer": response.message.content[0].text.strip()}


async def analysis_agent(state: GraphState) -> GraphState:
    context = _build_context(state["retrieved"])
    prompt = f"""Analyze the following document content in response to the user's request.
Identify key themes, entities, arguments, or comparisons as relevant.

Content:
{context}

Request: {state["query"]}

Analysis:"""

    response = _client.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    return {**state, "answer": response.message.content[0].text.strip()}


# ---------- Graph assembly ----------

def build_graph():
    from langgraph.graph import StateGraph, END

    graph = StateGraph(GraphState)

    graph.add_node("router", router_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("qa", qa_agent)
    graph.add_node("summarize", summarizer_agent)
    graph.add_node("analyze", analysis_agent)

    graph.set_entry_point("router")
    graph.add_edge("router", "retrieval")
    graph.add_conditional_edges(
        "retrieval",
        lambda state: state["route"],
        {"qa": "qa", "summarize": "summarize", "analyze": "analyze"},
    )
    graph.add_edge("qa", END)
    graph.add_edge("summarize", END)
    graph.add_edge("analyze", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph