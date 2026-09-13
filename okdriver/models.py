"""Data models for okdriver pothole detection module."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SeverityLevel(str, Enum):
    """Categorical severity levels for detected potholes."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, value: str) -> SeverityLevel:
        """Parse string to SeverityLevel safely."""
        try:
            return cls(value.upper())
        except (ValueError, AttributeError):
            return cls.LOW


@dataclass
class GPSCoordinate:
    """Geographic location coordinates with optional altitude, speed, and heading."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
        if self.speed_kmh is not None and self.speed_kmh < 0:
            raise ValueError(f"Speed cannot be negative, got {self.speed_kmh}")
        if self.heading_deg is not None and not (0.0 <= self.heading_deg <= 360.0):
            raise ValueError(f"Heading must be between 0 and 360 degrees, got {self.heading_deg}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert GPS coordinate to dictionary."""
        return {
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "altitude": round(self.altitude, 2) if self.altitude is not None else None,
            "speed_kmh": round(self.speed_kmh, 2) if self.speed_kmh is not None else None,
            "heading_deg": round(self.heading_deg, 1) if self.heading_deg is not None else None,
        }


@dataclass
class BoundingBox:
    """Bounding box coordinates and area calculations."""
    x1: float
    y1: float
    x2: float
    y2: float
    image_width: Optional[int] = None
    image_height: Optional[int] = None

    def __post_init__(self) -> None:
        # Normalize order if inverted
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    @property
    def width(self) -> float:
        """Pixel width of the bounding box."""
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        """Pixel height of the bounding box."""
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        """Pixel area of the bounding box."""
        return self.width * self.height

    @property
    def normalized_xyxy(self) -> Optional[Tuple[float, float, float, float]]:
        """Normalized bounding box coordinates [rx1, ry1, rx2, ry2] in [0, 1]."""
        if not self.image_width or not self.image_height or self.image_width <= 0 or self.image_height <= 0:
            return None
        return (
            max(0.0, min(1.0, self.x1 / self.image_width)),
            max(0.0, min(1.0, self.y1 / self.image_height)),
            max(0.0, min(1.0, self.x2 / self.image_width)),
            max(0.0, min(1.0, self.y2 / self.image_height)),
        )

    @property
    def relative_area(self) -> float:
        """Area relative to frame area [0.0, 1.0]."""
        if not self.image_width or not self.image_height or self.image_width <= 0 or self.image_height <= 0:
            return 0.0
        frame_area = float(self.image_width * self.image_height)
        return min(1.0, max(0.0, self.area / frame_area))

    def as_xyxy(self) -> Tuple[float, float, float, float]:
        """Return [x1, y1, x2, y2]."""
        return (self.x1, self.y1, self.x2, self.y2)

    def as_xywh(self) -> Tuple[float, float, float, float]:
        """Return [x1, y1, width, height]."""
        return (self.x1, self.y1, self.width, self.height)

    def to_dict(self) -> Dict[str, Any]:
        """Convert bounding box to dictionary."""
        norm = self.normalized_xyxy
        return {
            "x1": round(self.x1, 1),
            "y1": round(self.y1, 1),
            "x2": round(self.x2, 1),
            "y2": round(self.y2, 1),
            "width": round(self.width, 1),
            "height": round(self.height, 1),
            "pixel_area": round(self.area, 1),
            "relative_area": round(self.relative_area, 5),
            "normalized_xyxy": [round(val, 4) for val in norm] if norm else None,
        }


@dataclass
class PotholeDetection:
    """Individual pothole detection within a frame."""
    id: int
    confidence: float
    bbox: BoundingBox
    severity: SeverityLevel
    severity_score: float
    class_name: str = "pothole"

    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary."""
        return {
            "id": self.id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict(),
            "severity": self.severity.value,
            "severity_score": round(self.severity_score, 2),
        }


@dataclass
class PotholeDetectionResult:
    """Aggregated detection result for a single image/video frame."""
    frame_id: str
    timestamp: str
    image_width: int
    image_height: int
    detections: List[PotholeDetection] = field(default_factory=list)
    gps: Optional[GPSCoordinate] = None
    processing_time_ms: float = 0.0

    @property
    def total_potholes(self) -> int:
        """Total count of detected potholes."""
        return len(self.detections)

    @property
    def has_potholes(self) -> bool:
        """True if at least one pothole was detected."""
        return len(self.detections) > 0

    @property
    def max_severity(self) -> Optional[SeverityLevel]:
        """The maximum severity level detected in this frame, or None if no potholes."""
        if not self.detections:
            return None
        # Ranking order: CRITICAL > HIGH > MEDIUM > LOW
        ranking = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        return max(self.detections, key=lambda d: ranking.get(d.severity, 0)).severity

    @property
    def max_severity_score(self) -> float:
        """Maximum continuous severity score (0.0 to 10.0) in this frame."""
        if not self.detections:
            return 0.0
        return max(d.severity_score for d in self.detections)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire detection result to JSON-serializable dictionary."""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "image_dimensions": {
                "width": self.image_width,
                "height": self.image_height,
            },
            "gps": self.gps.to_dict() if self.gps else None,
            "total_potholes": self.total_potholes,
            "has_potholes": self.has_potholes,
            "max_severity": self.max_severity.value if self.max_severity else None,
            "max_severity_score": round(self.max_severity_score, 2),
            "processing_time_ms": round(self.processing_time_ms, 2),
            "detections": [d.to_dict() for d in self.detections],
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
                 