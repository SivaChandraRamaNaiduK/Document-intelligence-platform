"""
Application entrypoint.

Routers are registered here — as the project grows (auth, documents, chat),
each new router is one include_router line. That's the router-based design
from the resume bullet.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, chat, documents, health
from app.core.config import get_settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

MAX_REQUEST_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB — slightly above the 20 MB upload limit


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE_BYTES:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
        return await call_next(request)
    
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
# Week 2: app.include_router(auth.router)
# Week 3: app.include_router(documents.router)
# Week 5: app.include_router(chat.router)


@app.get("/")
async def root() -> dict:
    return {"app": settings.APP_NAME, "env": settings.ENVIRONMENT, "docs": "/docs"}