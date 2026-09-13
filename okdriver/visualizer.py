"""Visualization utilities to annotate frames with bounding boxes, severity badges, and GPS metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from okdriver.models import PotholeDetectionResult, SeverityLevel
from okdriver.utils import normalize_frame

# Color palette for severity levels (BGR format for OpenCV)
SEVERITY_COLORS = {
    SeverityLevel.LOW: (46, 204, 113),       # Green
    SeverityLevel.MEDIUM: (15, 196, 241),    # Yellow-Gold
    SeverityLevel.HIGH: (34, 126, 230),      # Orange
    SeverityLevel.CRITICAL: (60, 76, 231),   # Red / Crimson
}


def annotate_frame(
    frame_input: Union[str, Path, np.ndarray, Image.Image, bytes],
    result: PotholeDetectionResult,
    show_telemetry_banner: bool = True,
    box_thickness: int = 2,
    font_scale: float = 0.55,
    is_bgr: bool = False,
) -> np.ndarray:
    """Draw bounding boxes, severity badges, and telemetry overlays onto a frame.

    Args:
        frame_input: Original frame (file path, numpy array, PIL Image, or bytes).
        result: PotholeDetectionResult containing detections, GPS, and timestamp.
        show_telemetry_banner: If True, draws top telemetry banner with GPS & timestamp.
        box_thickness: Line thickness for bounding boxes.
        font_scale: Font scale for labels.
        is_bgr: If True and frame_input is a NumPy array, it is already BGR (e.g. from OpenCV).

    Returns:
        Annotated frame as a NumPy array (BGR format for OpenCV/saving).
    """
    if isinstance(frame_input, np.ndarray) and is_bgr and frame_input.ndim == 3 and frame_input.shape[2] == 3:
        canvas = frame_input.copy()
        height, width = canvas.shape[:2]
    else:
        frame, width, height = normalize_frame(frame_input, is_bgr=is_bgr)
        if frame.ndim == 2:
            canvas = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            canvas = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            canvas = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    canvas = np.ascontiguousarray(canvas, dtype=np.uint8)

    # 1. Draw detections
    for det in result.detections:
        color = SEVERITY_COLORS.get(det.severity, (255, 255, 255))
        x1, y1 = int(round(det.bbox.x1)), int(round(det.bbox.y1))
        x2, y2 = int(round(det.bbox.x2)), int(round(det.bbox.y2))

        # Clamp to frame boundary
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width - 1, x2), min(height - 1, y2)

        # Draw box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, box_thickness)

        # Prepare label
        label = f"#{det.id} Pothole {det.confidence:.0%} | {det.severity.value} ({det.severity_score:.1f})"

        # Label background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y1 = max(0, y1 - text_h - baseline - 6)
        label_y2 = label_y1 + text_h + baseline + 6
        label_x2 = min(width, x1 + text_w + 10)

        cv2.rectangle(canvas, (x1, label_y1), (label_x2, label_y2), color, -1)
        cv2.putText(
            canvas,
            label,
            (x1 + 5, label_y2 - baseline - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

    # 2. Draw telemetry banner
    if show_telemetry_banner:
        banner_height = 42
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (width, banner_height), (20, 20, 20), -1)
        # Blend banner with 75% opacity
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        # Compose telemetry text
        gps_str = "GPS: N/A"
        if result.gps:
            gps_str = f"GPS: {result.gps.latitude:.5f}, {result.gps.longitude:.5f}"
            if result.gps.speed_kmh is not None:
                gps_str += f" | {result.gps.speed_kmh:.0f} km/h"

        status_str = f"Potholes: {result.total_potholes}"
        if result.max_severity:
            status_str += f" | Max: {result.max_severity.value}"

        telemetry_text = f"UTC: {result.timestamp}   |   {gps_str}   |   {status_str}"

        cv2.putText(
            canvas,
            telemetry_text,
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return canvas


def save_annotated_frame(
    frame_input: Union[str, Path, np.ndarray, Image.Image, bytes],
    result: PotholeDetectionResult,
    output_path: Union[str, Path],
    **kwargs,
) -> str:
    """Annotate a frame and save the result image to disk."""
    annotated = annotate_frame(frame_input, result, **kwargs)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), annotated)
    return str(path.resolve())
