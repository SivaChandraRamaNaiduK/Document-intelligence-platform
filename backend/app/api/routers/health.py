"""
Health endpoints.

/health       -> is the API process up?
/health/db    -> can the API reach Postgres? (uses the get_db dependency)
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": result.scalar() == 1}