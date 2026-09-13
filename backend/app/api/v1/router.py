"""API v1 master router."""

from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.potholes import router as potholes_router
from app.api.v1.endpoints.reports import router as reports_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(potholes_router, prefix="/potholes", tags=["Potholes"])
api_router.include_router(reports_router, tags=["Civic Reports & Authorities"])

