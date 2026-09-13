"""SQLAlchemy database model for Pothole records."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class PotholeStatus(str, enum.Enum):
    """Lifecycle status of a detected pothole supporting the Reported -> Acknowledged -> In Progress -> Resolved workflow."""
    REPORTED = "REPORTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    # Backwards compatibility
    DETECTED = "DETECTED"
    VERIFIED = "VERIFIED"
    REPAIRED = "REPAIRED"
    REJECTED = "REJECTED"


class ReportStatus(str, enum.Enum):
    """Civic authority reporting status."""
    UNREPORTED = "UNREPORTED"
    QUEUED = "QUEUED"
    REPORTED = "REPORTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"


class ReportChannel(str, enum.Enum):
    """Communication channel for civic report delivery."""
    SIMULATED_API = "SIMULATED_API"
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    WEBHOOK = "WEBHOOK"


class SeverityLevel(str, enum.Enum):
    """Categorical severity matching okdriver Phase 1 classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def utc_now():
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class PotholeRecord(Base):
    """Database representation of an individual detected pothole incident."""
    __tablename__ = "potholes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    frame_id = Column(String(100), nullable=True, index=True, doc="Video frame ID or batch identifier")
    
    # Geographic location
    latitude = Column(Float, nullable=False, index=True, doc="GPS Latitude (-90.0 to 90.0)")
    longitude = Column(Float, nullable=False, index=True, doc="GPS Longitude (-180.0 to 180.0)")
    altitude = Column(Float, nullable=True, doc="Altitude in meters")
    speed_kmh = Column(Float, nullable=True, doc="Vehicle speed in km/h at time of detection")
    heading_deg = Column(Float, nullable=True, doc="Vehicle heading compass degrees (0-360)")
    
    # Reverse Geocoded Address and Settlement
    location_name = Column(String(255), nullable=True, index=True, doc="Human-readable reverse-geocoded road or locality name")
    city_district = Column(String(100), nullable=True, index=True, doc="City, town, or district name")
    
    # Civic Authority Assignment
    assigned_authority = Column(String(150), nullable=True, index=True, doc="Responsible civic authority/department")
    authority_code = Column(String(30), nullable=True, index=True, doc="Short code of assigned authority (e.g. BMC, MCD)")
    
    # Detection metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, doc="Detection timestamp")
    confidence = Column(Float, nullable=False, doc="YOLO detection confidence (0.0 to 1.0)")
    severity = Column(String(20), nullable=False, default=SeverityLevel.LOW.value, index=True, doc="Severity level")
    severity_score = Column(Float, nullable=False, default=0.0, doc="Continuous severity score (0.0 - 10.0)")
    
    # Bounding box coordinates and footprint metrics
    bounding_box = Column(JSON, nullable=False, doc="Bounding box geometry and area metrics")
    
    # Evidence images
    image_evidence_url = Column(String(500), nullable=True, doc="URL/path to captured raw or cropped image evidence")
    annotated_evidence_url = Column(String(500), nullable=True, doc="URL/path to visually annotated frame")
    
    # Operational workflow & Reporting status
    status = Column(String(30), nullable=False, default=PotholeStatus.DETECTED.value, index=True)
    report_status = Column(String(30), nullable=False, default=ReportStatus.UNREPORTED.value, index=True)
    ticket_id = Column(String(100), nullable=True, index=True, doc="Generated municipal ticket/incident reference ID")
    notes = Column(Text, nullable=True, doc="Public works or road maintenance notes")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Status Change Audit Trail
    status_history = relationship(
        "PotholeStatusHistory",
        back_populates="pothole",
        cascade="all, delete-orphan",
        order_by="desc(PotholeStatusHistory.changed_at)",
    )

    def __repr__(self) -> str:
        return (
            f"<PotholeRecord(id={self.id}, lat={self.latitude}, lon={self.longitude}, "
            f"authority={self.authority_code}, severity={self.severity}, status={self.status})>"
        )


class PotholeReport(Base):
    """Audit log of reports and tickets dispatched to civic authorities."""
    __tablename__ = "pothole_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(String(100), nullable=False, index=True, doc="Generated ticket ID reference")
    pothole_id = Column(Integer, index=True, nullable=False, doc="ID of reported pothole")
    
    authority_name = Column(String(150), nullable=False, doc="Authority name")
    authority_code = Column(String(30), nullable=False, index=True, doc="Authority short code")
    channel = Column(String(30), nullable=False, default=ReportChannel.SIMULATED_API.value, doc="Dispatch channel")
    status = Column(String(30), nullable=False, default=ReportStatus.REPORTED.value, index=True)
    
    # Detailed payload and dispatch logs
    report_data = Column(JSON, nullable=False, doc="Structured report with location, evidence, severity")
    dispatch_log = Column(JSON, nullable=False, doc="Response metadata from authority API or email server")
    
    dispatched_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    def __repr__(self) -> str:
        return f"<PotholeReport(ticket_id={self.ticket_id}, pothole_id={self.pothole_id}, status={self.status})>"


class PotholeStatusHistory(Base):
    """Audit log of status transitions across a pothole's operational lifecycle."""
    __tablename__ = "pothole_status_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pothole_id = Column(Integer, ForeignKey("potholes.id", ondelete="CASCADE"), nullable=False, index=True, doc="Associated pothole record ID")
    from_status = Column(String(30), nullable=True, doc="Previous operational status, or None if initial detection")
    to_status = Column(String(30), nullable=False, index=True, doc="Updated operational status")
    actor = Column(String(150), nullable=False, default="System (YOLO AI)", doc="Entity or officer who executed the transition")
    notes = Column(Text, nullable=True, doc="Operational, contractor, or inspection remarks")
    changed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True, doc="Timestamp of status transition")

    # Relationship back to pothole record
    pothole = relationship("PotholeRecord", back_populates="status_history")

    def __repr__(self) -> str:
        return f"<PotholeStatusHistory(pothole_id={self.pothole_id}, {self.from_status} -> {self.to_status}, actor='{self.actor}')>"

