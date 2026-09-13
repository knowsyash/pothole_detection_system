"""okdriver - Open-source YOLO-based Pothole Detection Module."""

from okdriver.detector import PotholeDetector
from okdriver.models import (
    BoundingBox,
    GPSCoordinate,
    PotholeDetection,
    PotholeDetectionResult,
    SeverityLevel,
)
from okdriver.severity import SeverityCalculator, SeverityConfig, calculate_severity
from okdriver.utils import ensure_model_weights, extract_exif_gps, normalize_frame
from okdriver.visualizer import annotate_frame, save_annotated_frame

__version__ = "0.1.0"

__all__ = [
    "PotholeDetector",
    "PotholeDetectionResult",
    "PotholeDetection",
    "BoundingBox",
    "GPSCoordinate",
    "SeverityLevel",
    "SeverityConfig",
    "SeverityCalculator",
    "calculate_severity",
    "normalize_frame",
    "extract_exif_gps",
    "ensure_model_weights",
    "annotate_frame",
    "save_annotated_frame",
]
