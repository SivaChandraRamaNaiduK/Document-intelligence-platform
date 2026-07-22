"""
Chat endpoint: runs the LangGraph multi-agent pipeline and logs the
interaction (query, route taken, answer, latency) for observability.
"""
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import get_graph
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import SearchResult

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
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