"""
Application entrypoint.

Routers are registered here — as the project grows (auth, documents, chat),
each new router is one include_router line. That's the router-based design
from the resume bullet.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
# Week 2: app.include_router(auth.router)
# Week 3: app.include_router(documents.router)
# Week 5: app.include_router(chat.router)


@app.get("/")
async def root() -> dict:
    return {"app": settings.APP_NAME, "env": settings.ENVIRONMENT, "docs": "/docs"}