from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import get_db, engine
from backend.app.models import Base, Store
from backend.app.api.v1.router import api_router

# Ensure schema exists on boot
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Voice-first commerce infrastructure for neighbourhood kirana stores.",
    debug=settings.DEBUG
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint validating database connectivity and demo store availability."""
    db_ok = False
    store_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        store = db.query(Store).filter(Store.store_id == settings.DEMO_STORE_ID).first()
        if store:
            store_ok = True
    except Exception as e:
        return {
            "status": "degraded",
            "database_connected": False,
            "error": str(e)
        }

    return {
        "status": "healthy" if (db_ok and store_ok) else "initializing",
        "database_connected": db_ok,
        "demo_store_ready": store_ok,
        "demo_store_id": settings.DEMO_STORE_ID
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
