"""Integration tests for civic authority assignment, reporting, and ticket tracking."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure paths are configured
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from app.database import Base, get_db
from app.main import app
from app.services.authorities import resolve_authority

client = TestClient(app)



# ============================================================================
# 1. Unit Tests: Civic Authority Resolution
# ============================================================================

def test_authority_resolution():
    """Verify GPS coordinates accurately resolve to responsible civic authorities."""
    # Mumbai (Bandra / Marine Drive) -> BMC
    mumbai_auth = resolve_authority(19.0760, 72.8777)
    assert mumbai_auth.code == "BMC"
    assert "Brihanmumbai" in mumbai_auth.name

    # Delhi (Connaught Place) -> MCD
    delhi_auth = resolve_authority(28.6139, 77.2090)
    assert delhi_auth.code == "MCD"
    assert "Delhi" in delhi_auth.name

    # Bengaluru (MG Road) -> BBMP
    blr_auth = resolve_authority(12.9716, 77.5946)
    assert blr_auth.code == "BBMP"
    assert "Bengaluru" in blr_auth.name

    # San Francisco (Market St) -> SFDPW
    sf_auth = resolve_authority(37.7749, -122.4194)
    assert sf_auth.code == "SFDPW"
    assert "San Francisco" in sf_auth.name

    # Unmapped location (e.g. London or remote rural highway) -> Fallback
    fallback_auth = resolve_authority(51.5074, -0.1278)
    assert fallback_auth.code == "PWD_CENTRAL"
    assert "Public Works" in fallback_auth.name


# ============================================================================
# 2. Automatic Authority Assignment on Ingestion & Creation
# ============================================================================

def test_automatic_authority_assignment_on_ingest():
    """Verify that ingesting Phase 1 detections automatically assigns authority."""
    payload = {
        "frame_id": "frame_mumbai_001",
        "timestamp": "2026-09-12T19:00:00Z",
        "gps": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "speed_kmh": 32.0,
        },
        "detections": [
            {
                "id": 1,
                "confidence": 0.89,
                "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
                "severity": "HIGH",
                "severity_score": 7.5,
            }
        ],
    }

    res = client.post("/api/v1/potholes/ingest", json=payload)
    assert res.status_code == 201
    records = res.json()["records"]
    assert len(records) == 1
    assert records[0]["authority_code"] == "BMC"
    assert "Brihanmumbai" in records[0]["assigned_authority"]
    assert records[0]["report_status"] == "UNREPORTED"


def test_automatic_authority_assignment_on_manual_create():
    """Verify that creating a pothole manually auto-resolves authority."""
    create_payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-12T19:15:00Z",
        "confidence": 0.92,
        "severity": "CRITICAL",
        "severity_score": 9.0,
        "bounding_box": {"x1": 50, "y1": 50, "x2": 150, "y2": 150},
    }

    res = client.post("/api/v1/potholes/", json=create_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["authority_code"] == "MCD"
    assert "Delhi" in data["assigned_authority"]
    assert data["report_status"] == "UNREPORTED"


# ============================================================================
# 3. Report Generation and Simulated Dispatch
# ============================================================================

def test_report_pothole_simulated_api():
    """Verify generating and dispatching report through simulated authority API."""
    # 1. Create a pothole in Bengaluru
    blr_pothole = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timestamp": "2026-09-12T19:30:00Z",
        "confidence": 0.95,
        "severity": "CRITICAL",
        "severity_score": 9.4,
        "bounding_box": {"x1": 10, "y1": 20, "x2": 80, "y2": 90},
        "image_evidence_url": "/static/evidence/raw_blr.jpg",
        "annotated_evidence_url": "/static/evidence/annotated_blr.jpg",
    }
    create_res = client.post("/api/v1/potholes/", json=blr_pothole)
    pothole_id = create_res.json()["id"]

    # 2. Dispatch report to BBMP via SIMULATED_API
    report_req = {
        "channel": "SIMULATED_API",
        "custom_notes": "Deep crater near metro pillar 142. Risk to buses.",
    }
    rep_res = client.post(f"/api/v1/potholes/{pothole_id}/report", json=report_req)
    assert rep_res.status_code == 201
    rep_data = rep_res.json()

    # Check generated ticket and authority
    ticket_id = rep_data["ticket_id"]
    assert ticket_id.startswith("TKT-BBMP-")
    assert rep_data["authority_code"] == "BBMP"
    assert rep_data["status"] == "ACKNOWLEDGED"

    # Check structured payload contains all required information
    inner_report = rep_data["report_data"]
    assert inner_report["location"]["latitude"] == 12.9716
    assert inner_report["detection"]["severity"] == "CRITICAL"
    assert inner_report["detection"]["confidence"] == 0.95
    assert inner_report["evidence"]["image_evidence_url"] == "/static/evidence/raw_blr.jpg"
    assert inner_report["evidence"]["annotated_evidence_url"] == "/static/evidence/annotated_blr.jpg"
    assert "email_payload" in inner_report
    assert "metro pillar 142" in inner_report["email_payload"]["body_text"]

    # Check dispatch response log
    assert rep_data["dispatch_log"]["http_status_code"] == 201
    assert "EXT-BBMP-" in rep_data["dispatch_log"]["external_reference_id"]
    assert rep_data["dispatch_log"]["acknowledged"] is True

    # 3. Verify pothole record was updated with ticket_id and report_status
    get_res = client.get(f"/api/v1/potholes/{pothole_id}")
    assert get_res.status_code == 200
    pothole_record = get_res.json()
    assert pothole_record["ticket_id"] == ticket_id
    assert pothole_record["report_status"] == "ACKNOWLEDGED"


def test_report_pothole_email_channel():
    """Verify generating and dispatching report through email channel."""
    # Create pothole in San Francisco
    sf_pothole = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp": "2026-09-12T19:45:00Z",
        "confidence": 0.88,
        "severity": "HIGH",
        "severity_score": 7.8,
        "bounding_box": {"x1": 50, "y1": 50, "x2": 150, "y2": 150},
        "image_evidence_url": "/static/evidence/sf_raw.jpg",
    }
    create_res = client.post("/api/v1/potholes/", json=sf_pothole)
    pothole_id = create_res.json()["id"]

    # Dispatch via EMAIL
    report_req = {
        "channel": "EMAIL",
        "custom_notes": "Hazard in right lane approaching highway onramp.",
    }
    rep_res = client.post(f"/api/v1/potholes/{pothole_id}/report", json=report_req)
    assert rep_res.status_code == 201
    rep_data = rep_res.json()

    assert rep_data["channel"] == "EMAIL"
    assert rep_data["status"] == "REPORTED"
    assert rep_data["authority_code"] == "SFDPW"
    assert "@okdriver.transport>" in rep_data["dispatch_log"]["message_id"]
    assert rep_data["dispatch_log"]["recipient"] == "potholes@sfdpw.org"


# ============================================================================
# 4. Report Query Endpoints
# ============================================================================

def test_list_and_get_reports_by_ticket():
    """Verify querying list of reports and fetching report by ticket ID."""
    # Create and report a pothole
    p = {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timestamp": "2026-09-12T20:00:00Z",
        "confidence": 0.91,
        "severity": "CRITICAL",
        "severity_score": 9.1,
        "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
    }
    p_id = client.post("/api/v1/potholes/", json=p).json()["id"]
    rep_res = client.post(f"/api/v1/potholes/{p_id}/report").json()
    ticket_id = rep_res["ticket_id"]

    # 1. Query all reports
    list_res = client.get("/api/v1/reports")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(item["ticket_id"] == ticket_id for item in items)

    # 2. Query reports filtered by authority
    bmc_res = client.get("/api/v1/reports?authority_code=BMC")
    assert bmc_res.status_code == 200
    assert all(item["authority_code"] == "BMC" for item in bmc_res.json())

    # 3. Get single report by ticket ID
    ticket_res = client.get(f"/api/v1/reports/{ticket_id}")
    assert ticket_res.status_code == 200
    assert ticket_res.json()["ticket_id"] == ticket_id
    assert ticket_res.json()["pothole_id"] == p_id

    # 4. Non-existent ticket returns 404
    missing_res = client.get("/api/v1/reports/TKT-INVALID-999999")
    assert missing_res.status_code == 404


# ============================================================================
# 5. Batch Auto-Reporting for Critical Hazards
# ============================================================================

def test_auto_report_critical_hazards():
    """Verify batch reporting of all un-reported critical and high severity hazards."""
    # Seed 1 critical (unreported), 1 high (unreported), and 1 low (unreported)
    p_crit = {
        "latitude": 19.1000,
        "longitude": 72.8500,
        "timestamp": "2026-09-12T20:10:00Z",
        "confidence": 0.95,
        "severity": "CRITICAL",
        "severity_score": 9.5,
        "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
    }
    p_high = {
        "latitude": 19.1200,
        "longitude": 72.8600,
        "timestamp": "2026-09-12T20:12:00Z",
        "confidence": 0.85,
        "severity": "HIGH",
        "severity_score": 7.0,
        "bounding_box": {"x1": 20, "y1": 20, "x2": 60, "y2": 60},
    }
    p_low = {
        "latitude": 19.1300,
        "longitude": 72.8700,
        "timestamp": "2026-09-12T20:15:00Z",
        "confidence": 0.60,
        "severity": "LOW",
        "severity_score": 2.0,
        "bounding_box": {"x1": 30, "y1": 30, "x2": 70, "y2": 70},
    }

    id_crit = client.post("/api/v1/potholes/", json=p_crit).json()["id"]
    id_high = client.post("/api/v1/potholes/", json=p_high).json()["id"]
    id_low = client.post("/api/v1/potholes/", json=p_low).json()["id"]

    # Trigger auto-report-critical
    batch_res = client.post("/api/v1/potholes/auto-report-critical")
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["reported_count"] == 2
    assert len(batch_data["tickets"]) == 2

    # Verify critical and high are now REPORTED / ACKNOWLEDGED
    rec_crit = client.get(f"/api/v1/potholes/{id_crit}").json()
    rec_high = client.get(f"/api/v1/potholes/{id_high}").json()
    rec_low = client.get(f"/api/v1/potholes/{id_low}").json()

    assert rec_crit["report_status"] == "ACKNOWLEDGED"
    assert rec_crit["ticket_id"] is not None
    assert rec_high["report_status"] == "ACKNOWLEDGED"
    assert rec_high["ticket_id"] is not None
    # Low hazard remains UNREPORTED
    assert rec_low["report_status"] == "UNREPORTED"
    assert rec_low["ticket_id"] is None


# ============================================================================
# 6. Authorities Registry Endpoint
# ============================================================================

def test_authorities_endpoint():
    """Verify retrieving list of all configured civic authorities and bounds."""
    res = client.get("/api/v1/authorities")
    assert res.status_code == 200
    authorities = res.json()
    assert len(authorities) >= 5

    codes = [a["code"] for a in authorities]
    assert "BMC" in codes
    assert "MCD" in codes
    assert "BBMP" in codes
    assert "SFDPW" in codes
    assert "PWD_CENTRAL" in codes

    # Verify contact email and API endpoint are present
    bmc = next(a for a in authorities if a["code"] == "BMC")
    assert bmc["contact_email"] == "roads.maintenance@mcgm.gov.in"
    assert bmc["api_endpoint"] == "https://api.mcgm.gov.in/v1/pothole-grievance"
    assert bmc["bounds"] is not None
