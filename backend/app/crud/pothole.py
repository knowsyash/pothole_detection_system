"""Database CRUD operations for pothole records."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select, desc, asc
from sqlalchemy.orm import Session

from app.models.pothole import PotholeRecord, PotholeReport, PotholeStatusHistory, PotholeStatus, ReportStatus, SeverityLevel
from app.schemas.pothole import PotholeCreate, PotholeUpdate


def create_pothole(db: Session, pothole_in: PotholeCreate) -> PotholeRecord:
    """Insert a single new pothole record into the database and create initial status history."""
    pothole_data = pothole_in.model_dump()
    # Serialize nested bounding box model to dict for JSON column
    if isinstance(pothole_data.get("bounding_box"), dict):
        pothole_data["bounding_box"] = pothole_in.bounding_box.model_dump()
    
    db_obj = PotholeRecord(**pothole_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Record initial lifecycle status event
    initial_event = PotholeStatusHistory(
        pothole_id=db_obj.id,
        from_status=None,
        to_status=db_obj.status,
        actor="System (YOLO AI Detector)",
        notes=db_obj.notes or "Initial defect logged and geo-referenced.",
        changed_at=db_obj.created_at,
    )
    db.add(initial_event)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_potholes_bulk(db: Session, potholes_in: List[Dict[str, Any]]) -> List[PotholeRecord]:
    """Insert multiple pothole records in a single database transaction with status history."""
    records = []
    for item in potholes_in:
        db_obj = PotholeRecord(**item)
        db.add(db_obj)
        records.append(db_obj)
    
    db.commit()
    for rec in records:
        db.refresh(rec)
        initial_event = PotholeStatusHistory(
            pothole_id=rec.id,
            from_status=None,
            to_status=rec.status,
            actor="System (YOLO AI Detector)",
            notes=rec.notes or "Initial defect logged and geo-referenced.",
            changed_at=rec.created_at,
        )
        db.add(initial_event)
    
    db.commit()
    for rec in records:
        db.refresh(rec)
    return records


def get_pothole_by_id(db: Session, pothole_id: int) -> Optional[PotholeRecord]:
    """Retrieve a single pothole record by primary key."""
    return db.query(PotholeRecord).filter(PotholeRecord.id == pothole_id).first()


def get_potholes(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[PotholeStatus] = None,
    severity: Optional[SeverityLevel] = None,
    min_confidence: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    frame_id: Optional[str] = None,
    authority_code: Optional[str] = None,
    report_status: Optional[str] = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
) -> Tuple[int, List[PotholeRecord]]:
    """Query potholes with comprehensive filtering, spatial bounding, sorting, and pagination."""
    query = db.query(PotholeRecord)

    # Filtering
    if status is not None:
        query = query.filter(PotholeRecord.status == status.value if hasattr(status, "value") else str(status))
    if report_status is not None:
        query = query.filter(PotholeRecord.report_status == report_status.upper())
    if authority_code is not None:
        query = query.filter(PotholeRecord.authority_code == authority_code.upper())
    if severity is not None:
        query = query.filter(PotholeRecord.severity == severity.value if hasattr(severity, "value") else str(severity))
    if min_confidence is not None:
        query = query.filter(PotholeRecord.confidence >= min_confidence)
    if start_time is not None:
        query = query.filter(PotholeRecord.timestamp >= start_time)
    if end_time is not None:
        query = query.filter(PotholeRecord.timestamp <= end_time)
    if min_lat is not None:
        query = query.filter(PotholeRecord.latitude >= min_lat)
    if max_lat is not None:
        query = query.filter(PotholeRecord.latitude <= max_lat)
    if min_lon is not None:
        query = query.filter(PotholeRecord.longitude >= min_lon)
    if max_lon is not None:
        query = query.filter(PotholeRecord.longitude <= max_lon)
    if frame_id is not None:
        query = query.filter(PotholeRecord.frame_id == frame_id)

    # Total count matching criteria
    total = query.count()

    # Sorting
    sort_column_map = {
        "id": PotholeRecord.id,
        "timestamp": PotholeRecord.timestamp,
        "confidence": PotholeRecord.confidence,
        "severity_score": PotholeRecord.severity_score,
        "created_at": PotholeRecord.created_at,
        "latitude": PotholeRecord.latitude,
        "longitude": PotholeRecord.longitude,
    }
    col = sort_column_map.get(sort_by.lower(), PotholeRecord.timestamp)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(col))
    else:
        query = query.order_by(desc(col))

    # Pagination
    items = query.offset(skip).limit(limit).all()
    return total, items


def update_pothole(db: Session, db_obj: PotholeRecord, update_in: PotholeUpdate) -> PotholeRecord:
    """Update fields on an existing pothole record and log status transitions."""
    update_data = update_in.model_dump(exclude_unset=True)
    old_status = db_obj.status
    actor = update_data.pop("actor", None) or "Municipal Road Officer"
    
    # Handle enum to string conversion if needed
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else str(update_data["status"])
    if "severity" in update_data and update_data["severity"] is not None:
        update_data["severity"] = update_data["severity"].value if hasattr(update_data["severity"], "value") else str(update_data["severity"])

    new_status = update_data.get("status")
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    # If status changed, record transition audit entry
    if new_status and new_status != old_status:
        history_entry = PotholeStatusHistory(
            pothole_id=db_obj.id,
            from_status=old_status,
            to_status=new_status,
            actor=actor,
            notes=update_data.get("notes") or db_obj.notes or f"Status transitioned from {old_status} to {new_status}",
            changed_at=datetime.now(timezone.utc),
        )
        db.add(history_entry)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_pothole(db: Session, db_obj: PotholeRecord) -> None:
    """Remove a pothole record from the database."""
    db.delete(db_obj)
    db.commit()


def get_pothole_stats(db: Session) -> Dict[str, Any]:
    """Calculate summary metrics and distributions across the pothole dataset."""
    total = db.query(PotholeRecord).count()

    # Status distribution
    status_counts = (
        db.query(PotholeRecord.status, func.count(PotholeRecord.id))
        .group_by(PotholeRecord.status)
        .all()
    )
    by_status = {status: count for status, count in status_counts}

    # Severity distribution
    sev_counts = (
        db.query(PotholeRecord.severity, func.count(PotholeRecord.id))
        .group_by(PotholeRecord.severity)
        .all()
    )
    by_severity = {sev: count for sev, count in sev_counts}

    # Averages
    averages = db.query(
        func.avg(PotholeRecord.confidence),
        func.avg(PotholeRecord.severity_score)
    ).first()

    avg_conf = float(averages[0]) if averages and averages[0] is not None else 0.0
    avg_score = float(averages[1]) if averages and averages[1] is not None else 0.0

    return {
        "total_potholes": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "avg_confidence": round(avg_conf, 4),
        "avg_severity_score": round(avg_score, 2),
    }


# ============================================================================
# Report & Ticket CRUD Helpers
# ============================================================================

def create_pothole_report(db: Session, report_dict: Dict[str, Any]) -> PotholeReport:
    """Save an audit record of a dispatched civic report."""
    report_obj = PotholeReport(**report_dict)
    db.add(report_obj)
    db.commit()
    db.refresh(report_obj)
    return report_obj


def get_report_by_ticket_id(db: Session, ticket_id: str) -> Optional[PotholeReport]:
    """Look up a report by its unique municipal ticket ID."""
    return db.query(PotholeReport).filter(PotholeReport.ticket_id == ticket_id).first()


def get_reports(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    pothole_id: Optional[int] = None,
    authority_code: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[int, List[PotholeReport]]:
    """Retrieve dispatched reports with optional filters."""
    query = db.query(PotholeReport)

    if pothole_id is not None:
        query = query.filter(PotholeReport.pothole_id == pothole_id)
    if authority_code is not None:
        query = query.filter(PotholeReport.authority_code == authority_code.upper())
    if status is not None:
        query = query.filter(PotholeReport.status == status.upper())

    total = query.count()
    items = query.order_by(PotholeReport.dispatched_at.desc()).offset(skip).limit(limit).all()
    return total, items


def get_unreported_potholes(
    db: Session,
    severity_levels: Optional[List[str]] = None,
) -> List[PotholeRecord]:
    """Retrieve potholes that have not yet been reported to civic authorities."""
    query = db.query(PotholeRecord).filter(PotholeRecord.report_status == ReportStatus.UNREPORTED.value)
    if severity_levels:
        query = query.filter(PotholeRecord.severity.in_(severity_levels))
    return query.all()


# ============================================================================
# Status Change History Helpers
# ============================================================================

def create_status_history(
    db: Session,
    pothole_id: int,
    to_status: str,
    from_status: Optional[str] = None,
    actor: str = "Municipal Road Officer",
    notes: Optional[str] = None,
    changed_at: Optional[datetime] = None,
) -> PotholeStatusHistory:
    """Explicitly create and persist a lifecycle transition audit record."""
    entry = PotholeStatusHistory(
        pothole_id=pothole_id,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        notes=notes,
        changed_at=changed_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_pothole_status_history(db: Session, pothole_id: int) -> List[PotholeStatusHistory]:
    """Retrieve complete chronological lifecycle transition history for a pothole."""
    return (
        db.query(PotholeStatusHistory)
        .filter(PotholeStatusHistory.pothole_id == pothole_id)
        .order_by(PotholeStatusHistory.changed_at.asc())
        .all()
    )


