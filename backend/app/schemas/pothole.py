"""Pydantic schemas for data validation and API serialization."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.pothole import PotholeStatus, SeverityLevel


class BoundingBoxSchema(BaseModel):
    """Bounding box geometry and footprint metrics."""
    x1: float = Field(..., description="Top-left X coordinate")
    y1: float = Field(..., description="Top-left Y coordinate")
    x2: float = Field(..., description="Bottom-right X coordinate")
    y2: float = Field(..., description="Bottom-right Y coordinate")
    width: Optional[float] = Field(None, description="Bounding box width in pixels")
    height: Optional[float] = Field(None, description="Bounding box height in pixels")
    pixel_area: Optional[float] = Field(None, description="Bounding box area in pixels")
    relative_area: Optional[float] = Field(None, description="Area relative to frame (0.0 to 1.0)")
    normalized_xyxy: Optional[List[float]] = Field(None, description="Normalized coordinates [rx1, ry1, rx2, ry2]")

    @field_validator("width", mode="before")
    @classmethod
    def compute_width(cls, v, values):
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.width is None:
            self.width = max(0.0, self.x2 - self.x1)
        if self.height is None:
            self.height = max(0.0, self.y2 - self.y1)
        if self.pixel_area is None:
            self.pixel_area = self.width * self.height


class PotholeBase(BaseModel):
    """Common properties of a pothole record."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    speed_kmh: Optional[float] = Field(None, ge=0.0, description="Vehicle speed in km/h")
    heading_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Vehicle heading angle")
    
    timestamp: datetime = Field(..., description="Date and time when detection occurred")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    severity: SeverityLevel = Field(default=SeverityLevel.LOW, description="Categorical severity level")
    severity_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Continuous severity score (0-10)")
    
    bounding_box: BoundingBoxSchema = Field(..., description="Bounding box details")
    image_evidence_url: Optional[str] = Field(None, description="URL or relative path to image evidence")
    annotated_evidence_url: Optional[str] = Field(None, description="URL or relative path to annotated frame")
    status: PotholeStatus = Field(default=PotholeStatus.DETECTED, description="Operational lifecycle status")
    notes: Optional[str] = Field(None, description="Optional notes or repair information")
    frame_id: Optional[str] = Field(None, description="Video frame ID or batch identifier")
    
    # Civic authority & reporting tracking
    location_name: Optional[str] = Field(None, description="Reverse-geocoded road or street name")
    city_district: Optional[str] = Field(None, description="City, town, or district name")
    assigned_authority: Optional[str] = Field(None, description="Name of assigned civic authority")
    authority_code: Optional[str] = Field(None, description="Short code of assigned authority (e.g., BMC, MCD)")
    ticket_id: Optional[str] = Field(None, description="Generated municipal ticket/incident ID")
    report_status: Optional[str] = Field(default="UNREPORTED", description="Reporting status (UNREPORTED, REPORTED, ACKNOWLEDGED)")


class PotholeCreate(PotholeBase):
    """Schema for creating a new pothole record manually or via API."""
    pass


class PotholeStatusHistoryResponse(BaseModel):
    """Schema for an individual status transition audit log."""
    id: int
    pothole_id: int
    from_status: Optional[str] = Field(None, description="Previous status")
    to_status: str = Field(..., description="Target status")
    actor: str = Field(..., description="Entity or officer who executed transition")
    notes: Optional[str] = Field(None, description="Remarks or inspection notes")
    changed_at: datetime = Field(..., description="Timestamp of change")

    model_config = ConfigDict(from_attributes=True)


class PotholeStatusUpdateRequest(BaseModel):
    """Schema for updating the lifecycle status of a pothole."""
    status: PotholeStatus = Field(..., description="Target status (REPORTED, ACKNOWLEDGED, IN_PROGRESS, RESOLVED)")
    actor: Optional[str] = Field(default="Municipal Road Officer", description="Name/role of person or system performing the update")
    notes: Optional[str] = Field(None, description="Optional contractor or inspection remarks")


class PotholeUpdate(BaseModel):
    """Schema for updating an existing pothole record."""
    status: Optional[PotholeStatus] = Field(None, description="Updated status (VERIFIED, IN_PROGRESS, REPAIRED, etc.)")
    actor: Optional[str] = Field(None, description="Actor performing the update for audit trail")
    severity: Optional[SeverityLevel] = Field(None, description="Updated severity level")
    severity_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Updated continuous severity score")
    notes: Optional[str] = Field(None, description="Crew or inspection notes")
    image_evidence_url: Optional[str] = Field(None, description="Updated image URL")
    annotated_evidence_url: Optional[str] = Field(None, description="Updated annotated frame URL")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    city_district: Optional[str] = None
    assigned_authority: Optional[str] = None
    authority_code: Optional[str] = None
    ticket_id: Optional[str] = None
    report_status: Optional[str] = None


class PotholeResponse(PotholeBase):
    """Schema returned to client for a pothole record."""
    id: int
    created_at: datetime
    updated_at: datetime
    status_history: List[PotholeStatusHistoryResponse] = Field(default_factory=list, description="Audit log of status changes")

    model_config = ConfigDict(from_attributes=True)


class PotholeListResponse(BaseModel):
    """Paginated list of pothole records."""
    total: int = Field(..., description="Total count matching query filters")
    limit: int = Field(..., description="Maximum items requested")
    offset: int = Field(..., description="Offset items skipped")
    items: List[PotholeResponse] = Field(..., description="List of pothole records")


# --- Phase 1 Ingestion Schemas ---

class Phase1GPSCoordinate(BaseModel):
    """GPS Telemetry matching Phase 1 okdriver GPSCoordinate."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None


class Phase1DetectionItem(BaseModel):
    """Individual detection inside Phase 1 PotholeDetectionResult."""
    id: int = Field(default=1, description="Detection ID within frame")
    class_name: Optional[str] = Field(default="pothole")
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBoxSchema
    severity: str = Field(default="LOW")
    severity_score: float = Field(default=0.0)


class Phase1IngestRequest(BaseModel):
    """Matches Phase 1 PotholeDetectionResult.to_dict() serialization."""
    frame_id: str = Field(default="frame_000000")
    timestamp: str = Field(..., description="ISO 8601 or formatted timestamp from Phase 1")
    image_dimensions: Optional[Dict[str, int]] = Field(None, description="Width and height of frame")
    gps: Optional[Phase1GPSCoordinate] = Field(None, description="GPS telemetry attached in Phase 1")
    total_potholes: Optional[int] = Field(None, description="Total detected potholes in frame")
    has_potholes: Optional[bool] = Field(None)
    max_severity: Optional[str] = None
    max_severity_score: Optional[float] = None
    processing_time_ms: Optional[float] = 0.0
    detections: List[Phase1DetectionItem] = Field(default_factory=list, description="List of detected potholes")
    
    # Optional image URLs if uploaded alongside
    image_evidence_url: Optional[str] = None
    annotated_evidence_url: Optional[str] = None


class Phase1IngestResponse(BaseModel):
    """Response returned upon ingesting Phase 1 results."""
    message: str
    frame_id: str
    potholes_recorded: int
    records: List[PotholeResponse]


# --- Analytics / Statistics Schemas ---

class PotholeStatsResponse(BaseModel):
    """Summary statistics for potholes in the system."""
    total_potholes: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    avg_confidence: float
    avg_severity_score: float


# --- Reporting & Authority Schemas ---

class ReportCreateRequest(BaseModel):
    """Request payload to report a pothole to its civic authority."""
    channel: Optional[str] = Field("SIMULATED_API", description="Dispatch channel: 'SIMULATED_API' or 'EMAIL'")
    custom_notes: Optional[str] = Field(None, description="Custom note or municipal dispatch instructions")
    recipient_email: Optional[str] = Field(None, description="Optional override for authority email")


class PotholeReportResponse(BaseModel):
    """Audit record for a generated and dispatched pothole report."""
    id: int
    ticket_id: str
    pothole_id: int
    authority_name: str
    authority_code: str
    channel: str
    status: str
    report_data: Dict[str, Any]
    dispatch_log: Dict[str, Any]
    dispatched_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CivicAuthorityResponse(BaseModel):
    """Metadata describing a municipal or regional authority."""
    code: str
    name: str
    region: str
    contact_email: str
    api_endpoint: str
    description: str
    bounds: Optional[List[float]] = None


class BatchReportResponse(BaseModel):
    """Response returned when auto-reporting multiple potholes."""
    message: str
    reported_count: int
    tickets: List[str]
    reports: List[PotholeReportResponse]

