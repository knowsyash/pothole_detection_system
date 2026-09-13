import asyncio
import gc
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pothole import PotholeRecord, PotholeStatus, ReportStatus, SeverityLevel
from app.schemas.pothole import (
    PotholeCreate,
    PotholeUpdate,
    PotholeResponse,
    PotholeListResponse,
    PotholeStatusHistoryResponse,
    PotholeStatusUpdateRequest,
    Phase1IngestRequest,
    Phase1IngestResponse,
    PotholeStatsResponse,
    ReportCreateRequest,
    PotholeReportResponse,
    BatchReportResponse,
)
from app.crud import pothole as crud_pothole
from app.services.storage import storage_service
from app.services.authorities import resolve_authority, get_authority_by_code
from app.services.reporting import generate_pothole_report, dispatch_report

logger = logging.getLogger("okdriver.api.potholes")
router = APIRouter()


def _parse_timestamp(ts_str: str) -> datetime:
    """Safely parse an ISO string or arbitrary timestamp into a datetime object."""
    try:
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now(timezone.utc)


_fallback_detector: Optional[Any] = None


def _get_detector(request: Request, conf_threshold: Optional[float] = None) -> Any:
    """Retrieve pre-warmed PotholeDetector singleton from app state, or initialize fallback."""
    global _fallback_detector
    detector = getattr(request.app.state, "detector", None) if hasattr(request, "app") else None
    if detector is None:
        if _fallback_detector is None:
            from okdriver import PotholeDetector
            _fallback_detector = PotholeDetector(conf_threshold=conf_threshold or 0.25, auto_download=True)
        detector = _fallback_detector

    if conf_threshold is not None:
        detector.conf_threshold = conf_threshold
    return detector


# ============================================================================
# Phase 1 Ingestion Endpoints
# ============================================================================

@router.post(
    "/ingest",
    response_model=Phase1IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Phase 1 detection result JSON",
    description="Receives output from okdriver Phase 1 detector, persists telemetry, bounding boxes, and metadata.",
)
def ingest_phase1_result(
    payload: Phase1IngestRequest,
    db: Session = Depends(get_db),
):
    """Directly ingest a Phase 1 PotholeDetectionResult JSON payload."""
    if not payload.gps:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phase 1 detection payload must include GPS coordinates (latitude, longitude).",
        )

    ts = _parse_timestamp(payload.timestamp)
    # Automatically resolve civic authority for this GPS coordinate
    authority = resolve_authority(payload.gps.latitude, payload.gps.longitude)
    records_to_create = []

    for det in payload.detections:
        # Map severity safely
        try:
            sev_level = SeverityLevel(det.severity.upper()).value
        except (ValueError, AttributeError):
            sev_level = SeverityLevel.LOW.value

        rec_dict = {
            "frame_id": payload.frame_id,
            "latitude": payload.gps.latitude,
            "longitude": payload.gps.longitude,
            "altitude": payload.gps.altitude,
            "speed_kmh": payload.gps.speed_kmh,
            "heading_deg": payload.gps.heading_deg,
            "location_name": authority.location_name or authority.region,
            "city_district": authority.city or authority.region,
            "assigned_authority": authority.name,
            "authority_code": authority.code,
            "report_status": ReportStatus.UNREPORTED.value,
            "timestamp": ts,
            "confidence": det.confidence,
            "severity": sev_level,
            "severity_score": det.severity_score,
            "bounding_box": det.bbox.model_dump(),
            "image_evidence_url": payload.image_evidence_url,
            "annotated_evidence_url": payload.annotated_evidence_url,
            "status": PotholeStatus.DETECTED.value,
        }
        records_to_create.append(rec_dict)

    created_records = crud_pothole.create_potholes_bulk(db, records_to_create)
    logger.info(f"Ingested {len(created_records)} potholes from frame {payload.frame_id}")

    return Phase1IngestResponse(
        message=f"Successfully ingested {len(created_records)} pothole detections.",
        frame_id=payload.frame_id,
        potholes_recorded=len(created_records),
        records=[PotholeResponse.model_validate(r) for r in created_records],
    )


@router.post(
    "/ingest/upload",
    response_model=Phase1IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image evidence with Phase 1 detection metadata",
    description="Receives an image file upload along with Phase 1 detection JSON, saves image evidence to disk, and stores pothole records.",
)
async def ingest_with_evidence_upload(
    image: UploadFile = File(..., description="Captured road image or annotated frame"),
    detection_data: str = Form(..., description="JSON string corresponding to Phase 1 PotholeDetectionResult"),
    db: Session = Depends(get_db),
):
    """Ingest Phase 1 detection metadata with accompanying image evidence upload."""
    try:
        data_dict = json.loads(detection_data)
        payload = Phase1IngestRequest.model_validate(data_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid detection_data JSON: {str(exc)}",
        )

    # Save evidence file
    evidence_url = await storage_service.save_upload_file(image, prefix="evidence")
    payload.image_evidence_url = evidence_url

    return ingest_phase1_result(payload=payload, db=db)


@router.post(
    "/detect-and-store",
    response_model=Phase1IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Direct live image or dashcam video detection and storage",
    description="Runs okdriver YOLO model on an uploaded image or dashcam video (MP4, MOV, AVI, WEBM), extracts and annotates frames, and writes all detections into the database.",
)
async def detect_and_store(
    request: Request,
    image: Optional[UploadFile] = File(None, description="Input road image file (JPG/PNG)"),
    file: Optional[UploadFile] = File(None, description="Input road image or dashcam video file (JPG/PNG/MP4/MOV/AVI/WEBM)"),
    latitude: float = Form(..., ge=-90.0, le=90.0, description="Vehicle Latitude"),
    longitude: float = Form(..., ge=-180.0, le=180.0, description="Vehicle Longitude"),
    altitude: Optional[float] = Form(None, description="Altitude in meters"),
    speed_kmh: Optional[float] = Form(None, ge=0.0, description="Vehicle speed in km/h"),
    heading_deg: Optional[float] = Form(None, ge=0.0, le=360.0, description="Compass heading (0-360)"),
    conf_threshold: Optional[float] = Form(None, ge=0.05, le=1.0, description="Confidence threshold"),
    db: Session = Depends(get_db),
):
    """Run detection pipeline on uploaded image or video footage and automatically record findings."""
    try:
        from okdriver import GPSCoordinate, annotate_frame
        import cv2
        import numpy as np
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"okdriver or OpenCV dependencies not available: {e}",
        )

    upload_item = file or image
    if not upload_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No image or video file uploaded.")

    filename = (upload_item.filename or "").lower()
    content_type = (upload_item.content_type or "").lower()
    is_video = (
        content_type.startswith("video/")
        or filename.endswith((".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"))
    )

    gps = GPSCoordinate(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        speed_kmh=speed_kmh,
        heading_deg=heading_deg,
    )

    threshold = conf_threshold if conf_threshold is not None else 0.25
    detector = _get_detector(request, conf_threshold=threshold)
    is_cpu = getattr(detector, "device", "cpu") == "cpu"

    authority = resolve_authority(gps.latitude, gps.longitude)
    records_to_create = []
    primary_frame_id = None

    if is_video:
        # Write video to temporary file for cv2.VideoCapture
        suffix = Path(filename).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_vid:
            tmp_path = tmp_vid.name
            while chunk := await upload_item.read(1024 * 1024):
                tmp_vid.write(chunk)

        try:
            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to open uploaded video stream.")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            # Adaptive video sampling: on CPU (Render free tier), sample every ~1.5s (max 10 frames) to stay within 100s timeout.
            # On GPU, sample every ~0.75s (max 25 frames).
            sample_interval = max(1, int(fps * (1.5 if is_cpu else 0.75)))
            max_samples = 10 if is_cpu else 25

            frame_idx = 0
            sampled_count = 0

            while cap.isOpened() and sampled_count < max_samples:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_interval == 0:
                    sampled_count += 1
                    sec_offset = frame_idx / fps
                    frame_ts = datetime.now(timezone.utc)
                    # Run inference on threadpool so FastAPI event loop stays responsive
                    result = await asyncio.to_thread(detector.detect, frame, gps=gps, is_bgr=True)

                    if result.detections:
                        if not primary_frame_id:
                            primary_frame_id = result.frame_id

                        # Encode and save frames for this defect
                        _, encoded_raw = cv2.imencode(".jpg", frame)
                        evidence_url = storage_service.save_bytes(encoded_raw.tobytes(), prefix=f"vid_f{frame_idx}", extension=".jpg")

                        annotated_frame = annotate_frame(frame, result, is_bgr=True)
                        _, encoded_annotated = cv2.imencode(".jpg", annotated_frame)
                        annotated_url = storage_service.save_bytes(encoded_annotated.tobytes(), prefix=f"vid_ann_f{frame_idx}", extension=".jpg")

                        for det in result.detections:
                            rec_dict = {
                                "frame_id": f"vid_{result.frame_id}_{frame_idx}",
                                "latitude": gps.latitude,
                                "longitude": gps.longitude,
                                "altitude": gps.altitude,
                                "speed_kmh": gps.speed_kmh,
                                "heading_deg": gps.heading_deg,
                                "location_name": authority.location_name or authority.region,
                                "city_district": authority.city or authority.region,
                                "assigned_authority": authority.name,
                                "authority_code": authority.code,
                                "report_status": ReportStatus.UNREPORTED.value,
                                "timestamp": frame_ts,
                                "confidence": det.confidence,
                                "severity": det.severity.value,
                                "severity_score": det.severity_score,
                                "bounding_box": det.bbox.to_dict(),
                                "image_evidence_url": evidence_url,
                                "annotated_evidence_url": annotated_url,
                                "status": PotholeStatus.DETECTED.value,
                                "notes": f"Detected in dashcam footage at +{sec_offset:.1f}s offset",
                            }
                            records_to_create.append(rec_dict)

                frame_idx += 1
            cap.release()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not primary_frame_id:
            primary_frame_id = f"video_{int(datetime.now().timestamp())}"

    else:
        # Standard Single Image Pipeline
        image_bytes = await upload_item.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to decode image.")

        # Run inference on threadpool so FastAPI event loop stays responsive
        result = await asyncio.to_thread(detector.detect, frame, gps=gps, is_bgr=True)
        primary_frame_id = result.frame_id

        # Save original raw image
        evidence_url = storage_service.save_bytes(image_bytes, prefix="raw_frame", extension=".jpg")

        # Generate and save annotated visual overlay
        annotated_frame = annotate_frame(frame, result, is_bgr=True)
        _, encoded_annotated = cv2.imencode(".jpg", annotated_frame)
        annotated_url = storage_service.save_bytes(encoded_annotated.tobytes(), prefix="annotated", extension=".jpg")

        ts = _parse_timestamp(result.timestamp)
        for det in result.detections:
            rec_dict = {
                "frame_id": result.frame_id,
                "latitude": gps.latitude,
                "longitude": gps.longitude,
                "altitude": gps.altitude,
                "speed_kmh": gps.speed_kmh,
                "heading_deg": gps.heading_deg,
                "location_name": authority.location_name or authority.region,
                "city_district": authority.city or authority.region,
                "assigned_authority": authority.name,
                "authority_code": authority.code,
                "report_status": ReportStatus.UNREPORTED.value,
                "timestamp": ts,
                "confidence": det.confidence,
                "severity": det.severity.value,
                "severity_score": det.severity_score,
                "bounding_box": det.bbox.to_dict(),
                "image_evidence_url": evidence_url,
                "annotated_evidence_url": annotated_url,
                "status": PotholeStatus.DETECTED.value,
            }
            records_to_create.append(rec_dict)

    created_records = crud_pothole.create_potholes_bulk(db, records_to_create)

    # Force Python GC to reclaim temporary frame buffers immediately (critical for Render 512MB limit)
    gc.collect()

    item_desc = "video frames" if is_video else "image"
    return Phase1IngestResponse(
        message=f"Analyzed {item_desc} and recorded {len(created_records)} pothole defects.",
        frame_id=primary_frame_id,
        potholes_recorded=len(created_records),
        records=[PotholeResponse.model_validate(r) for r in created_records],
    )


# ============================================================================
# Pothole CRUD Endpoints
# ============================================================================

@router.post(
    "/",
    response_model=PotholeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pothole record manually",
    description="Manually create a new pothole record with full telemetry, bounding box, and evidence information.",
)
def create_pothole_record(
    pothole_in: PotholeCreate,
    db: Session = Depends(get_db),
):
    """Create a single pothole record with automatic civic authority assignment."""
    # Auto-resolve civic authority & geocoded location if not provided
    if not pothole_in.assigned_authority or not pothole_in.authority_code:
        auth = resolve_authority(pothole_in.latitude, pothole_in.longitude)
        pothole_in.assigned_authority = auth.name
        pothole_in.authority_code = auth.code
        if not pothole_in.location_name:
            pothole_in.location_name = auth.location_name or auth.region
        if not pothole_in.city_district:
            pothole_in.city_district = auth.city or auth.region

    created = crud_pothole.create_pothole(db, pothole_in)
    return PotholeResponse.model_validate(created)


@router.get(
    "/",
    response_model=PotholeListResponse,
    summary="List potholes with filters and pagination",
    description="Retrieve pothole records filtered by status, severity, confidence, date range, or geographic bounds.",
)
def list_potholes(
    status: Optional[PotholeStatus] = Query(None, description="Filter by status (DETECTED, VERIFIED, IN_PROGRESS, REPAIRED, REJECTED)"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity level (LOW, MEDIUM, HIGH, CRITICAL)"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum detection confidence threshold"),
    start_time: Optional[datetime] = Query(None, description="Filter detections after this timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter detections before this timestamp"),
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Southern bounding latitude"),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Northern bounding latitude"),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Western bounding longitude"),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Eastern bounding longitude"),
    frame_id: Optional[str] = Query(None, description="Filter by frame/batch identifier"),
    authority_code: Optional[str] = Query(None, description="Filter by assigned authority short code (e.g. BMC, MCD, BBMP)"),
    report_status: Optional[str] = Query(None, description="Filter by reporting status (UNREPORTED, REPORTED, ACKNOWLEDGED)"),
    skip: int = Query(0, ge=0, description="Records to skip (pagination offset)"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    sort_by: str = Query("timestamp", description="Column to sort by (timestamp, confidence, severity_score, created_at, id)"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction (asc or desc)"),
    db: Session = Depends(get_db),
):
    """Query pothole records with pagination and filters."""
    total, items = crud_pothole.get_potholes(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        severity=severity,
        min_confidence=min_confidence,
        start_time=start_time,
        end_time=end_time,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        frame_id=frame_id,
        authority_code=authority_code,
        report_status=report_status,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return PotholeListResponse(
        total=total,
        limit=limit,
        offset=skip,
        items=[PotholeResponse.model_validate(item) for item in items],
    )


@router.get(
    "/stats/summary",
    response_model=PotholeStatsResponse,
    summary="Get aggregated pothole statistics",
    description="Calculates summary counts grouped by status, severity, and calculates average confidence and severity scores.",
)
def get_pothole_statistics(db: Session = Depends(get_db)):
    """Retrieve aggregate analytics across all pothole records."""
    stats = crud_pothole.get_pothole_stats(db)
    return PotholeStatsResponse(**stats)


@router.post(
    "/auto-report-critical",
    response_model=BatchReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Automatically report critical and high hazards to authorities",
    description="Finds all un-reported CRITICAL and HIGH severity potholes and dispatches reports to their respective civic authorities.",
)
def auto_report_critical(
    channel: str = Query("SIMULATED_API", description="Dispatch channel (SIMULATED_API or EMAIL)"),
    db: Session = Depends(get_db),
):
    """Scan and dispatch reports for all un-reported high/critical hazards."""
    unreported = crud_pothole.get_unreported_potholes(db, severity_levels=["CRITICAL", "HIGH"])
    reports = []
    tickets = []

    for pothole in unreported:
        auth = get_authority_by_code(pothole.authority_code) if pothole.authority_code else resolve_authority(pothole.latitude, pothole.longitude)
        report_data = generate_pothole_report(pothole, authority=auth)
        dispatch_log = dispatch_report(report_data, channel=channel)

        rep_record = crud_pothole.create_pothole_report(
            db,
            {
                "ticket_id": report_data["ticket_id"],
                "pothole_id": pothole.id,
                "authority_name": auth.name,
                "authority_code": auth.code,
                "channel": channel,
                "status": dispatch_log.get("status", ReportStatus.REPORTED.value),
                "report_data": report_data,
                "dispatch_log": dispatch_log,
            }
        )

        pothole.ticket_id = report_data["ticket_id"]
        pothole.report_status = dispatch_log.get("status", ReportStatus.REPORTED.value)
        pothole.assigned_authority = auth.name
        pothole.authority_code = auth.code
        if report_data["evidence"].get("annotated_evidence_url"):
            pothole.annotated_evidence_url = report_data["evidence"]["annotated_evidence_url"]
        if report_data["evidence"].get("image_evidence_url"):
            pothole.image_evidence_url = report_data["evidence"]["image_evidence_url"]
        db.add(pothole)

        reports.append(PotholeReportResponse.model_validate(rep_record))
        tickets.append(report_data["ticket_id"])

    db.commit()
    return BatchReportResponse(
        message=f"Dispatched {len(reports)} critical hazard reports to civic authorities.",
        reported_count=len(reports),
        tickets=tickets,
        reports=reports,
    )


@router.post(
    "/{pothole_id}/report",
    response_model=PotholeReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and send report to responsible civic authority",
    description="Generates an incident report with GPS, timestamp, severity, confidence, and photo evidence, and dispatches it through email or simulated authority API.",
)
def report_pothole_to_authority(
    pothole_id: int,
    report_req: Optional[ReportCreateRequest] = None,
    db: Session = Depends(get_db),
):
    """Generate and dispatch report to the responsible municipal department."""
    pothole = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not pothole:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )

    channel = report_req.channel if report_req and report_req.channel else "SIMULATED_API"
    custom_notes = report_req.custom_notes if report_req else None

    # Resolve authority
    auth = None
    if pothole.authority_code:
        auth = get_authority_by_code(pothole.authority_code)
    if not auth:
        auth = resolve_authority(pothole.latitude, pothole.longitude)
        pothole.assigned_authority = auth.name
        pothole.authority_code = auth.code

    if report_req and report_req.recipient_email:
        auth.contact_email = report_req.recipient_email

    # Generate report payload
    report_data = generate_pothole_report(pothole, authority=auth, custom_notes=custom_notes)

    # Dispatch through channel (email or simulated API)
    dispatch_log = dispatch_report(report_data, channel=channel)

    # Save report audit log
    report_record = crud_pothole.create_pothole_report(
        db,
        {
            "ticket_id": report_data["ticket_id"],
            "pothole_id": pothole.id,
            "authority_name": auth.name,
            "authority_code": auth.code,
            "channel": channel,
            "status": dispatch_log.get("status", ReportStatus.REPORTED.value),
            "report_data": report_data,
            "dispatch_log": dispatch_log,
        }
    )

    # Update pothole record status, ticket ID, and Cloudflare R2 evidence URLs
    pothole.ticket_id = report_data["ticket_id"]
    pothole.report_status = dispatch_log.get("status", ReportStatus.REPORTED.value)
    if report_data["evidence"].get("annotated_evidence_url"):
        pothole.annotated_evidence_url = report_data["evidence"]["annotated_evidence_url"]
    if report_data["evidence"].get("image_evidence_url"):
        pothole.image_evidence_url = report_data["evidence"]["image_evidence_url"]
    db.add(pothole)
    db.commit()
    db.refresh(pothole)

    return PotholeReportResponse.model_validate(report_record)


@router.get(
    "/{pothole_id}",
    response_model=PotholeResponse,
    summary="Get single pothole details",
    description="Retrieve complete metadata, telemetry, and evidence URLs for a specific pothole by ID.",
)
def get_pothole_details(
    pothole_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve pothole record by primary key."""
    record = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )
    return PotholeResponse.model_validate(record)


@router.patch(
    "/{pothole_id}",
    response_model=PotholeResponse,
    summary="Partially update a pothole record",
    description="Update pothole operational status (e.g., mark as REPAIRED or IN_PROGRESS), update notes, or correct telemetry.",
)
def patch_pothole(
    pothole_id: int,
    update_in: PotholeUpdate,
    db: Session = Depends(get_db),
):
    """Update fields of an existing pothole record."""
    record = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )
    updated = crud_pothole.update_pothole(db, record, update_in)
    return PotholeResponse.model_validate(updated)


@router.put(
    "/{pothole_id}",
    response_model=PotholeResponse,
    summary="Update a pothole record",
    description="Update pothole record fields.",
)
def update_pothole_record(
    pothole_id: int,
    update_in: PotholeUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing pothole record."""
    return patch_pothole(pothole_id, update_in, db)


@router.delete(
    "/{pothole_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a pothole record",
    description="Permanently removes a pothole record from the database.",
)
def delete_pothole_record(
    pothole_id: int,
    db: Session = Depends(get_db),
):
    """Delete a pothole record."""
    record = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )
    crud_pothole.delete_pothole(db, record)
    return {
        "status": "success",
        "message": f"Pothole record with ID {pothole_id} deleted successfully.",
        "pothole_id": pothole_id,
    }


@router.get(
    "/{pothole_id}/history",
    response_model=List[PotholeStatusHistoryResponse],
    summary="Get lifecycle status change history",
    description="Retrieve the chronological audit trail of all status transitions for a given pothole.",
)
def get_pothole_history(
    pothole_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve full lifecycle status history for this defect."""
    record = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )
    history = crud_pothole.get_pothole_status_history(db, pothole_id)
    return [PotholeStatusHistoryResponse.model_validate(h) for h in history]


@router.post(
    "/{pothole_id}/status",
    response_model=PotholeResponse,
    summary="Transition pothole lifecycle status",
    description="Advance or change operational status with an attributed actor and inspection notes.",
)
def update_pothole_status_transition(
    pothole_id: int,
    status_req: PotholeStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Execute status transition with actor audit logging."""
    record = crud_pothole.get_pothole_by_id(db, pothole_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pothole record with ID {pothole_id} not found.",
        )
    update_data = PotholeUpdate(
        status=status_req.status,
        actor=status_req.actor,
        notes=status_req.notes,
    )
    updated = crud_pothole.update_pothole(db, record, update_data)
    return PotholeResponse.model_validate(updated)

