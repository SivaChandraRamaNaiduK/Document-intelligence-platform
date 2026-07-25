"""
Chat endpoint: runs the LangGraph multi-agent pipeline and logs the
interaction (query, route taken, answer, latency) for observability.
"""
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


from app.agents.graph import get_graph
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import SearchResult

import json

from fastapi.responses import StreamingResponse

from app.agents.graph import build_prompt, retrieval_node, router_node, _client, CHAT_MODEL

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    start = time.perf_counter()

    graph = get_graph()
    result = await graph.ainvoke(
        {
            "query": payload.message,
            "user_id": current_user.id,
            "document_ids": payload.document_ids,
            "db": db,
            "route": "",
            "retrieved": [],
            "answer": "",
        }
    )

    latency_ms = int((time.perf_counter() - start) * 1000)

    db.add(
        Interaction(
            user_id=current_user.id,
            query=payload.message,
            route=result["route"],
            answer=result["answer"],
            latency_ms=latency_ms,
        )
    )
    await db.commit()

    return ChatResponse(
        answer=result["answer"],
        route=result["route"],
        sources=[SearchResult(**r) for r in result["retrieved"]],
        latency_ms=latency_ms,
    )

@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Streams the answer token-by-token via Server-Sent Events (SSE).
    Routing and retrieval happen first (fast), then the LLM's completion
    is streamed as it's generated.
    """
    start = time.perf_counter()

    state = {
        "query": payload.message,
        "user_id": current_user.id,
        "document_ids": payload.document_ids,
        "db": db,
        "route": "",
        "retrieved": [],
        "answer": "",
    }

    state = await router_node(state)
    state = await retrieval_node(state)

    prompt = build_prompt(state["route"], state["query"], state["retrieved"])

    async def event_generator():
        full_answer_parts = []

 # First event: route + sources, so the frontend can render citations
        # immediately while the answer streams in afterward. UUIDs must be
        # converted to strings — json.dumps can't serialize them directly.
        serializable_sources = [
            {**r, "chunk_id": str(r["chunk_id"]), "document_id": str(r["document_id"])}
            for r in state["retrieved"]
        ]
        meta = {
            "type": "meta",
            "route": state["route"],
            "sources": serializable_sources,
        }
        yield f"data: {json.dumps(meta)}\n\n"
        
        stream = _client.chat_stream(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
        for event in stream:
            if event.type == "content-delta":
                delta = event.delta.message.content.text
                full_answer_parts.append(delta)
                yield f"data: {json.dumps({'type': 'token', 'text': delta})}\n\n"

        answer = "".join(full_answer_parts)
        latency_ms = int((time.perf_counter() - start) * 1000)

        db.add(
            Interaction(
                user_id=current_user.id,
                query=payload.message,
                route=state["route"],
                answer=answer,
                latency_ms=latency_ms,
            )
        )
        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")