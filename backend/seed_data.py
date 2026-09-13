"""Seed realistic pothole records across multiple authorities and workflow states."""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, init_db
from app.models.pothole import PotholeRecord, PotholeReport, PotholeStatusHistory, PotholeStatus, ReportStatus, SeverityLevel
from app.services.authorities import resolve_authority
from app.services.reporting import generate_pothole_report, dispatch_report


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing if any
    db.query(PotholeStatusHistory).delete()
    db.query(PotholeReport).delete()
    db.query(PotholeRecord).delete()
    db.commit()

    now = datetime.now(timezone.utc)

    samples = [
        {
            "frame_id": "cam_mum_0102",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "altitude": 14.5,
            "speed_kmh": 42.0,
            "heading_deg": 185.0,
            "timestamp": now - timedelta(hours=3),
            "confidence": 0.94,
            "severity": SeverityLevel.CRITICAL.value,
            "severity_score": 9.2,
            "bounding_box": {"x1": 320, "y1": 540, "x2": 680, "y2": 790, "width": 360, "height": 250, "pixel_area": 90000},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.REPORTED.value,
            "notes": "Large crater near Bandra Kurla Complex junction. High risk of vehicle axle damage.",
        },
        {
            "frame_id": "cam_del_0421",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "altitude": 215.0,
            "speed_kmh": 36.5,
            "heading_deg": 90.0,
            "timestamp": now - timedelta(hours=5),
            "confidence": 0.88,
            "severity": SeverityLevel.HIGH.value,
            "severity_score": 7.8,
            "bounding_box": {"x1": 150, "y1": 300, "x2": 450, "y2": 520, "width": 300, "height": 220, "pixel_area": 66000},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.ACKNOWLEDGED.value,
            "notes": "Barakhamba Road intersection. Municipal inspection crew notified.",
        },
        {
            "frame_id": "cam_blr_0812",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "altitude": 920.0,
            "speed_kmh": 28.0,
            "heading_deg": 270.0,
            "timestamp": now - timedelta(hours=14),
            "confidence": 0.91,
            "severity": SeverityLevel.CRITICAL.value,
            "severity_score": 8.9,
            "bounding_box": {"x1": 200, "y1": 420, "x2": 580, "y2": 710, "width": 380, "height": 290, "pixel_area": 110200},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.IN_PROGRESS.value,
            "notes": "Near MG Road metro station. Road cutting repair team on site.",
        },
        {
            "frame_id": "cam_mum_0984",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "altitude": 18.0,
            "speed_kmh": 50.0,
            "heading_deg": 10.0,
            "timestamp": now - timedelta(days=1, hours=2),
            "confidence": 0.79,
            "severity": SeverityLevel.MEDIUM.value,
            "severity_score": 5.4,
            "bounding_box": {"x1": 400, "y1": 600, "x2": 620, "y2": 760, "width": 220, "height": 160, "pixel_area": 35200},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.RESOLVED.value,
            "notes": "Western Express Highway flyover ramp. Cold mix asphalt patched and roller flattened.",
        },
        {
            "frame_id": "cam_sf_0055",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 16.0,
            "speed_kmh": 32.0,
            "heading_deg": 45.0,
            "timestamp": now - timedelta(days=2),
            "confidence": 0.85,
            "severity": SeverityLevel.HIGH.value,
            "severity_score": 7.2,
            "bounding_box": {"x1": 280, "y1": 480, "x2": 520, "y2": 660, "width": 240, "height": 180, "pixel_area": 43200},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.IN_PROGRESS.value,
            "notes": "Market Street bikeway hazard. SF Public Works asphalt team dispatched.",
        },
        {
            "frame_id": "cam_del_0771",
            "latitude": 28.5355,
            "longitude": 77.2600,
            "altitude": 220.0,
            "speed_kmh": 45.0,
            "heading_deg": 120.0,
            "timestamp": now - timedelta(days=3),
            "confidence": 0.72,
            "severity": SeverityLevel.LOW.value,
            "severity_score": 2.8,
            "bounding_box": {"x1": 350, "y1": 500, "x2": 470, "y2": 590, "width": 120, "height": 90, "pixel_area": 10800},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.RESOLVED.value,
            "notes": "Minor surface raveling near Nehru Place. Filled during scheduled maintenance.",
        },
        # --- Small City & Tier-2/3 Town Test Samples ---
        {
            "frame_id": "cam_alwar_0012",
            "latitude": 27.5530,
            "longitude": 76.6346,
            "altitude": 268.0,
            "speed_kmh": 34.0,
            "heading_deg": 140.0,
            "timestamp": now - timedelta(hours=6),
            "confidence": 0.92,
            "severity": SeverityLevel.CRITICAL.value,
            "severity_score": 9.0,
            "bounding_box": {"x1": 220, "y1": 460, "x2": 610, "y2": 720, "width": 390, "height": 260, "pixel_area": 101400},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.REPORTED.value,
            "notes": "Deep asphalt depression on SH13 passing Arya Nagar, Alwar. High risk for two-wheelers.",
        },
        {
            "frame_id": "cam_hathras_0045",
            "latitude": 27.5968,
            "longitude": 78.0519,
            "altitude": 178.0,
            "speed_kmh": 26.0,
            "heading_deg": 210.0,
            "timestamp": now - timedelta(hours=10),
            "confidence": 0.86,
            "severity": SeverityLevel.HIGH.value,
            "severity_score": 7.4,
            "bounding_box": {"x1": 180, "y1": 380, "x2": 490, "y2": 610, "width": 310, "height": 230, "pixel_area": 71300},
            "image_evidence_url": "/static/evidence/sample_pothole.jpg",
            "annotated_evidence_url": "/static/evidence/sample_pothole_annotated.jpg",
            "status": PotholeStatus.ACKNOWLEDGED.value,
            "notes": "Madan Lal Banswale stretch, Hathras. Nagar Palika maintenance desk notified.",
        },
    ]

    for item in samples:
        auth = resolve_authority(item["latitude"], item["longitude"])
        item["assigned_authority"] = auth.name
        item["authority_code"] = auth.code
        item["location_name"] = auth.location_name or auth.region
        item["city_district"] = auth.city or auth.region
        
        # Create record
        rec = PotholeRecord(**item)
        db.add(rec)
        db.commit()
        db.refresh(rec)

        # Generate report and ticket
        report_data = generate_pothole_report(rec, authority=auth)
        dispatch_log = dispatch_report(report_data, channel="SIMULATED_API")

        rep_obj = PotholeReport(
            ticket_id=report_data["ticket_id"],
            pothole_id=rec.id,
            authority_name=auth.name,
            authority_code=auth.code,
            channel="SIMULATED_API",
            status=dispatch_log.get("status", ReportStatus.REPORTED.value),
            report_data=report_data,
            dispatch_log=dispatch_log,
        )
        db.add(rep_obj)
        
        # Link ticket to pothole
        rec.ticket_id = report_data["ticket_id"]
        rec.report_status = dispatch_log.get("status", ReportStatus.REPORTED.value)
        db.add(rec)
        db.commit()

        # Seed realistic lifecycle status transitions
        target_status = rec.status
        t0 = rec.timestamp

        # Step 1: Initial detection is always logged
        hist_events = [
            PotholeStatusHistory(
                pothole_id=rec.id,
                from_status=None,
                to_status=PotholeStatus.REPORTED.value,
                actor="System (YOLO AI Detector)",
                notes="Automated road surface defect detected from dashcam frame.",
                changed_at=t0,
            )
        ]

        # Step 2: Acknowledgment
        if target_status in [PotholeStatus.ACKNOWLEDGED.value, PotholeStatus.IN_PROGRESS.value, PotholeStatus.RESOLVED.value]:
            hist_events.append(
                PotholeStatusHistory(
                    pothole_id=rec.id,
                    from_status=PotholeStatus.REPORTED.value,
                    to_status=PotholeStatus.ACKNOWLEDGED.value,
                    actor=f"Control Room Officer ({auth.code})",
                    notes="Ticket assigned to Sub-Division Maintenance Team.",
                    changed_at=t0 + timedelta(hours=1),
                )
            )

        # Step 3: In Progress
        if target_status in [PotholeStatus.IN_PROGRESS.value, PotholeStatus.RESOLVED.value]:
            hist_events.append(
                PotholeStatusHistory(
                    pothole_id=rec.id,
                    from_status=PotholeStatus.ACKNOWLEDGED.value,
                    to_status=PotholeStatus.IN_PROGRESS.value,
                    actor="Contractor Maintenance Crew #4",
                    notes="Excavation and base layer aggregate filling underway.",
                    changed_at=t0 + timedelta(hours=4),
                )
            )

        # Step 4: Resolved
        if target_status == PotholeStatus.RESOLVED.value:
            hist_events.append(
                PotholeStatusHistory(
                    pothole_id=rec.id,
                    from_status=PotholeStatus.IN_PROGRESS.value,
                    to_status=PotholeStatus.RESOLVED.value,
                    actor="Executive Engineer (Quality Audit)",
                    notes="Surface bitumen restored and verified clear for traffic.",
                    changed_at=t0 + timedelta(hours=9),
                )
            )

        for h in hist_events:
            db.add(h)
        db.commit()

    print(f"Successfully seeded {len(samples)} realistic pothole incidents with civic tickets and lifecycle histories!")


if __name__ == "__main__":
    seed()

