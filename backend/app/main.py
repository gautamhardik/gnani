import logging
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import get_db, engine
from backend.app.models import Base, Store
from backend.app.api.v1.router import api_router

logger = logging.getLogger("dukaansaathi.api")

# Ensure schema exists on boot
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Voice-first commerce infrastructure for neighbourhood kirana stores.",
    debug=settings.DEBUG
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# 2. Security Headers & Payload Guard Middleware (Phase 9 Hardening)
@app.middleware("http")
async def security_headers_and_payload_middleware(request: Request, call_next):
    # Guard against excessively large request bodies (e.g. >15MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 15 * 1024 * 1024:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request entity exceeds maximum allowable size of 15MB."}
        )

    response: Response = await call_next(request)

    # Standard OWASP Defensive Security Headers
    allowed_connect = " ".join(settings.ALLOWED_ORIGINS) if isinstance(settings.ALLOWED_ORIGINS, list) else str(settings.ALLOWED_ORIGINS)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "media-src 'self' blob: data:; "
        f"connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:3000 http://127.0.0.1:3000 https: {allowed_connect}; "
        "frame-ancestors 'none';"
    )

    if settings.ENABLE_HSTS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# Include API v1 Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "healthy",
        "docs_url": "/docs",
        "store_id": settings.DEMO_STORE_ID
    }


@app.get("/health", tags=["Health"])
def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Health check endpoint validating database connectivity and demo store availability.
    Returns HTTP 200 when healthy, or HTTP 503 when degraded.
    Never discloses database connection strings, passwords, or internal server versions.
    """
    db_ok = False
    store_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        store = db.query(Store).filter(Store.store_id == settings.DEMO_STORE_ID).first()
        if store:
            store_ok = True
    except Exception as e:
        logger.error(f"[HEALTH CHECK ERROR] Database connectivity failure: {type(e).__name__}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database_connected": False,
            "error": "Database connectivity check failed"
        }

    is_healthy = db_ok and store_ok
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "initializing",
        "database_connected": db_ok,
        "demo_store_ready": store_ok,
        "demo_store_id": settings.DEMO_STORE_ID
    }


@app.get("/health/live", tags=["Health"])
def liveness_probe():
    """Kubernetes / Container orchestrator liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_probe(response: Response, db: Session = Depends(get_db)):
    """Kubernetes / Container orchestrator readiness probe."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"[READINESS ERROR] Database unavailable: {type(e).__name__}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "Database connection unavailable"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
