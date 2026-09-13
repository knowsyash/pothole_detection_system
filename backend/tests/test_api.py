"""Comprehensive integration tests for okDRIVER FastAPI backend."""

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from app.database import Base, get_db
from app.main import app

client = TestClient(app)



# ============================================================================
# 1. Health & Root Tests
# ============================================================================

def test_root_endpoint():
    """Verify root discovery endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "docs" in data
    assert "api_v1" in data


def test_health_check():
    """Verify health probe reports system and database status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"]["status"] == "healthy"


# ============================================================================
# 2. Phase 1 Ingestion Tests
# ============================================================================

def test_ingest_phase1_detection_json():
    """Verify ingesting a Phase 1 PotholeDetectionResult JSON payload."""
    phase1_payload = {
        "frame_id": "frame_000101",
        "timestamp": "2026-09-12T17:30:00+00:00",
        "image_dimensions": {"width": 1920, "height": 1080},
        "gps": {
            "latitude": 37.774929,
            "longitude": -122.419416,
            "altitude": 15.2,
            "speed_kmh": 45.0,
            "heading_deg": 180.5,
        },
        "total_potholes": 2,
        "has_potholes": True,
        "max_severity": "HIGH",
        "max_severity_score": 7.8,
        "processing_time_ms": 14.5,
        "detections": [
            {
                "id": 1,
                "class_name": "pothole",
                "confidence": 0.88,
                "bbox": {
                    "x1": 450.0,
                    "y1": 600.0,
                    "x2": 650.0,
                    "y2": 720.0,
                    "width": 200.0,
                    "height": 120.0,
                    "pixel_area": 24000.0,
                    "relative_area": 0.01157,
                    "normalized_xyxy": [0.234, 0.555, 0.338, 0.666],
                },
                "severity": "HIGH",
                "severity_score": 7.8,
            },
            {
                "id": 2,
                "class_name": "pothole",
                "confidence": 0.72,
                "bbox": {
                    "x1": 800.0,
                    "y1": 700.0,
                    "x2": 900.0,
                    "y2": 780.0,
                    "width": 100.0,
                    "height": 80.0,
                    "pixel_area": 8000.0,
                    "relative_area": 0.00385,
                    "normalized_xyxy": [0.416, 0.648, 0.468, 0.722],
                },
                "severity": "LOW",
                "severity_score": 2.5,
            },
        ],
    }

    response = client.post("/api/v1/potholes/ingest", json=phase1_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["potholes_recorded"] == 2
    assert data["frame_id"] == "frame_000101"

    records = data["records"]
    assert len(records) == 2
    assert records[0]["latitude"] == 37.774929
    assert records[0]["longitude"] == -122.419416
    assert records[0]["severity"] == "HIGH"
    assert records[0]["confidence"] == 0.88
    assert records[0]["status"] == "DETECTED"
    assert records[0]["bounding_box"]["x1"] == 450.0
    assert records[0]["bounding_box"]["pixel_area"] == 24000.0


def test_ingest_without_gps_fails():
    """Verify validation error when GPS coordinates are omitted."""
    payload = {
        "frame_id": "frame_no_gps",
        "timestamp": "2026-09-12T17:30:00+00:00",
        "gps": None,
        "detections": [],
    }
    response = client.post("/api/v1/potholes/ingest", json=payload)
    assert response.status_code == 422


def test_ingest_with_image_upload():
    """Verify multipart upload containing both image evidence and Phase 1 JSON metadata."""
    sample_json = {
        "frame_id": "frame_upload_01",
        "timestamp": "2026-09-12T18:00:00+00:00",
        "gps": {"latitude": 19.0760, "longitude": 72.8777, "speed_kmh": 30.0},
        "detections": [
            {
                "id": 1,
                "confidence": 0.82,
                "bbox": {"x1": 100, "y1": 150, "x2": 250, "y2": 300},
                "severity": "MEDIUM",
                "severity_score": 5.4,
            }
        ],
    }

    fake_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
    files = {"image": ("evidence.jpg", io.BytesIO(fake_image_bytes), "image/jpeg")}
    data = {"detection_data": json.dumps(sample_json)}

    response = client.post("/api/v1/potholes/ingest/upload", files=files, data=data)
    assert response.status_code == 201
    result = response.json()
    assert result["potholes_recorded"] == 1
    assert result["records"][0]["image_evidence_url"] is not None
    assert "/static/evidence/" in result["records"][0]["image_evidence_url"]


# ============================================================================
# 3. Pothole CRUD API Tests
# ============================================================================

def _create_sample_pothole() -> int:
    """Helper to create a sample pothole record."""
    create_payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "altitude": 216.0,
        "speed_kmh": 35.5,
        "heading_deg": 90.0,
        "timestamp": "2026-09-12T12:00:00Z",
        "confidence": 0.94,
        "severity": "CRITICAL",
        "severity_score": 9.2,
        "bounding_box": {
            "x1": 300.0,
            "y1": 400.0,
            "x2": 700.0,
            "y2": 800.0,
            "width": 400.0,
            "height": 400.0,
            "pixel_area": 160000.0,
        },
        "status": "DETECTED",
        "notes": "Near intersection, high risk for two-wheelers.",
        "frame_id": "manual_batch_1",
    }
    response = client.post("/api/v1/potholes/", json=create_payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_pothole_record_crud():
    """Verify manual creation of a pothole record via POST /api/v1/potholes/."""
    create_payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "altitude": 216.0,
        "speed_kmh": 35.5,
        "heading_deg": 90.0,
        "timestamp": "2026-09-12T12:00:00Z",
        "confidence": 0.94,
        "severity": "CRITICAL",
        "severity_score": 9.2,
        "bounding_box": {
            "x1": 300.0,
            "y1": 400.0,
            "x2": 700.0,
            "y2": 800.0,
            "width": 400.0,
            "height": 400.0,
            "pixel_area": 160000.0,
        },
        "status": "DETECTED",
        "notes": "Near intersection, high risk for two-wheelers.",
        "frame_id": "manual_batch_1",
    }

    response = client.post("/api/v1/potholes/", json=create_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["latitude"] == 28.6139
    assert data["longitude"] == 77.2090
    assert data["severity"] == "CRITICAL"
    assert data["severity_score"] == 9.2
    assert data["status"] == "DETECTED"
    assert data["notes"] == "Near intersection, high risk for two-wheelers."


def test_get_pothole_by_id():
    """Verify retrieving single record by ID."""
    pothole_id = _create_sample_pothole()

    response = client.get(f"/api/v1/potholes/{pothole_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pothole_id
    assert data["latitude"] == 28.6139

    # Non-existent ID returns 404
    missing_response = client.get("/api/v1/potholes/999999")
    assert missing_response.status_code == 404


def test_update_pothole_status_and_notes():
    """Verify updating operational status (e.g. from DETECTED to IN_PROGRESS and REPAIRED)."""
    pothole_id = _create_sample_pothole()

    # 1. Update status to IN_PROGRESS
    update_1 = {
        "status": "IN_PROGRESS",
        "notes": "Work order issued to municipal crew #4.",
    }
    patch_res1 = client.patch(f"/api/v1/potholes/{pothole_id}", json=update_1)
    assert patch_res1.status_code == 200
    assert patch_res1.json()["status"] == "IN_PROGRESS"
    assert "municipal crew #4" in patch_res1.json()["notes"]

    # 2. Update status to REPAIRED
    update_2 = {
        "status": "REPAIRED",
        "notes": "Filled and asphalt cured on 2026-09-12.",
    }
    patch_res2 = client.patch(f"/api/v1/potholes/{pothole_id}", json=update_2)
    assert patch_res2.status_code == 200
    assert patch_res2.json()["status"] == "REPAIRED"


def test_delete_pothole():
    """Verify deleting a pothole record."""
    pothole_id = _create_sample_pothole()

    # Delete
    del_res = client.delete(f"/api/v1/potholes/{pothole_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Subsequent GET returns 404
    get_res = client.get(f"/api/v1/potholes/{pothole_id}")
    assert get_res.status_code == 404

    # Deleting already deleted item returns 404
    del_res2 = client.delete(f"/api/v1/potholes/{pothole_id}")
    assert del_res2.status_code == 404


# ============================================================================
# 4. Query Filtering, Pagination, and Sorting Tests
# ============================================================================

def test_list_filtering_and_pagination():
    """Verify list querying with multiple criteria (status, severity, bounding box, sorting)."""
    # Seed 3 records
    items = [
        {
            "latitude": 10.0,
            "longitude": 20.0,
            "timestamp": "2026-09-10T10:00:00Z",
            "confidence": 0.90,
            "severity": "LOW",
            "severity_score": 2.0,
            "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
            "status": "DETECTED",
        },
        {
            "latitude": 12.0,
            "longitude": 22.0,
            "timestamp": "2026-09-11T12:00:00Z",
            "confidence": 0.80,
            "severity": "MEDIUM",
            "severity_score": 5.0,
            "bounding_box": {"x1": 20, "y1": 20, "x2": 60, "y2": 60},
            "status": "VERIFIED",
        },
        {
            "latitude": 15.0,
            "longitude": 25.0,
            "timestamp": "2026-09-12T14:00:00Z",
            "confidence": 0.95,
            "severity": "CRITICAL",
            "severity_score": 9.5,
            "bounding_box": {"x1": 30, "y1": 30, "x2": 80, "y2": 80},
            "status": "REPAIRED",
        },
    ]

    for item in items:
        res = client.post("/api/v1/potholes/", json=item)
        assert res.status_code == 201

    # 1. Filter by status
    res_status = client.get("/api/v1/potholes/?status=VERIFIED")
    assert res_status.status_code == 200
    assert res_status.json()["total"] == 1
    assert res_status.json()["items"][0]["severity"] == "MEDIUM"

    # 2. Filter by severity
    res_sev = client.get("/api/v1/potholes/?severity=CRITICAL")
    assert res_sev.status_code == 200
    assert res_sev.json()["total"] == 1
    assert res_sev.json()["items"][0]["latitude"] == 15.0

    # 3. Filter by min_confidence
    res_conf = client.get("/api/v1/potholes/?min_confidence=0.85")
    assert res_conf.status_code == 200
    assert res_conf.json()["total"] == 2

    # 4. Spatial bounding box filter
    res_geo = client.get("/api/v1/potholes/?min_lat=9.0&max_lat=11.0&min_lon=19.0&max_lon=21.0")
    assert res_geo.status_code == 200
    assert res_geo.json()["total"] == 1
    assert res_geo.json()["items"][0]["latitude"] == 10.0

    # 5. Pagination (limit 1, skip 1)
    res_page = client.get("/api/v1/potholes/?limit=1&skip=1&sort_by=timestamp&sort_order=asc")
    assert res_page.status_code == 200
    assert res_page.json()["total"] == 3
    assert len(res_page.json()["items"]) == 1
    assert res_page.json()["items"][0]["severity"] == "MEDIUM"


# ============================================================================
# 5. Analytics / Statistics Tests
# ============================================================================

def test_pothole_summary_statistics():
    """Verify statistics aggregation endpoint."""
    # Seed 2 records
    p1 = {
        "latitude": 30.0,
        "longitude": 70.0,
        "timestamp": "2026-09-12T10:00:00Z",
        "confidence": 0.80,
        "severity": "HIGH",
        "severity_score": 7.0,
        "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
        "status": "DETECTED",
    }
    p2 = {
        "latitude": 31.0,
        "longitude": 71.0,
        "timestamp": "2026-09-12T11:00:00Z",
        "confidence": 0.90,
        "severity": "LOW",
        "severity_score": 3.0,
        "bounding_box": {"x1": 20, "y1": 20, "x2": 60, "y2": 60},
        "status": "REPAIRED",
    }
    client.post("/api/v1/potholes/", json=p1)
    client.post("/api/v1/potholes/", json=p2)

    stats_res = client.get("/api/v1/potholes/stats/summary")
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert data["total_potholes"] == 2
    assert data["by_status"]["DETECTED"] == 1
    assert data["by_status"]["REPAIRED"] == 1
    assert data["by_severity"]["HIGH"] == 1
    assert data["by_severity"]["LOW"] == 1
    assert data["avg_confidence"] == pytest.approx(0.85, 0.01)
    assert data["avg_severity_score"] == pytest.approx(5.0, 0.1)
