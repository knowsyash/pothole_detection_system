"""FastAPI application initialization and middleware configuration."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("okdriver.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan events."""
    logger.info("Starting up okDRIVER Pothole Management API...")
    init_db()

    # Pre-load PotholeDetector singleton and warm up to prevent first-request lag
    try:
        from okdriver import PotholeDetector
        import numpy as np

        logger.info("Pre-loading PotholeDetector singleton in memory...")
        detector = PotholeDetector(auto_download=True)
        # Model warmup with a dummy array to initialize PyTorch/CUDA execution graphs
        dummy_frame = np.zeros((480, 480, 3), dtype=np.uint8)
        detector.detect(dummy_frame, auto_extract_gps=False)
        app.state.detector = detector
        logger.info(f"PotholeDetector initialized and warmed up on {detector.device.upper()}.")
    except Exception as exc:
        logger.warning(f"Could not pre-load PotholeDetector during startup: {exc}")
        app.state.detector = None

    yield
    logger.info("Shutting down okDRIVER Pothole Management API...")



app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-ready backend API for okDRIVER pothole detection and lifecycle management. "
        "Ingests telemetry, bounding boxes, and image evidence from Phase 1 detections, "
        "and provides rich CRUD and analytics endpoints."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Mount evidence static files for image downloads and browser preview
app.mount(
    settings.STATIC_URL_PREFIX,
    StaticFiles(directory=str(settings.UPLOAD_DIR)),
    name="evidence",
)

# Register master API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["System"])
def root():
    """Root welcoming endpoint with quick links."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1": settings.API_V1_PREFIX,
        "health": f"{settings.API_V1_PREFIX}/health",
        "potholes": f"{settings.API_V1_PREFIX}/potholes",
    }
