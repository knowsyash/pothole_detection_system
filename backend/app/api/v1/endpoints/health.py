"""Health check and diagnostic endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, engine

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Check API status and database connectivity."""
    db_status = "healthy"
    db_type = engine.dialect.name
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "ok" if "unhealthy" not in db_status else "degraded",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": {
            "status": db_status,
            "dialect": db_type,
        }
    }
