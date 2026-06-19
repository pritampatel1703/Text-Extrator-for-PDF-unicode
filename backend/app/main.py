"""
PDF Search Platform — Main FastAPI Application.
Enterprise-grade multilingual PDF text extraction and global search.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.db.database import init_db, close_db
from app.db.elasticsearch import ElasticsearchClient
from app.api.routes import upload, documents, search, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # ── Startup ──
    logger.info(f"🚀 Starting {settings.app_name}...")

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # Initialize Elasticsearch
    try:
        await ElasticsearchClient.init_index()
        logger.info("✅ Elasticsearch initialized")
    except Exception as e:
        logger.warning(f"⚠️ Elasticsearch initialization failed (will retry): {e}")

    logger.info(f"✅ {settings.app_name} is ready!")

    yield

    # ── Shutdown ──
    logger.info("Shutting down...")
    await close_db()
    await ElasticsearchClient.close()
    logger.info("Goodbye! 👋")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise-grade multilingual PDF text extraction and global search platform. "
        "Upload PDFs, extract text from digital and scanned documents using OCR, "
        "and search across all content with full-text, semantic, and hybrid search."
    ),
    version="1.0.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# ── Rate Limiting Middleware ──
# Wrapped in try/except since Redis may not be available in dev
try:
    from app.api.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
except Exception:
    logger.warning("Rate limiting middleware not loaded (Redis may be unavailable)")

# ── Mount Static Files for uploaded PDFs ──
import os
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# ── Register API Routes ──
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)


# ── Health Check ──
@app.get("/health", tags=["Health"])
@app.get(f"{settings.api_prefix}/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    es_health = await ElasticsearchClient.health_check()

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "elasticsearch": es_health.get("status", "unknown"),
    }


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "type": type(exc).__name__,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.backend_workers,
    )
