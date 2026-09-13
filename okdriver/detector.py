"""Core PotholeDetector class running YOLO inference, GPS/timestamp binding, and severity analysis."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Union

import numpy as np
from PIL import Image

from okdriver.models import (
    BoundingBox,
    GPSCoordinate,
    PotholeDetection,
    PotholeDetectionResult,
    SeverityLevel,
)
from okdriver.severity import SeverityCalculator, SeverityConfig
from okdriver.utils import ensure_model_weights, extract_exif_gps, normalize_frame


class PotholeDetector:
    """Detects potholes in image and video frames using an open-source YOLO model.

    Features:
      - YOLOv8 inference with customizable confidence thresholds
      - Automatic open-source model download and local caching
      - Frame-level GPS coordinate and ISO timestamp attachment
      - EXIF GPS metadata auto-extraction for photo inputs
      - Severity classification and continuous scoring from bounding-box size
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.25,
        device: Optional[str] = None,
        severity_config: Optional[SeverityConfig] = None,
        auto_download: bool = True,
        offline_mode: bool = False,
    ) -> None:
        """Initialize PotholeDetector.

        Args:
            model_path: Path to local .pt weight file or model URL. If None, uses default open-source weights.
            conf_threshold: Minimum confidence threshold for detection (0.0 to 1.0).
            device: Computing device ('cpu', 'cuda', '0', etc.). None selects best available.
            severity_config: Custom configuration for severity thresholds and score scaling.
            auto_download: If True, automatically downloads default weights if not present.
            offline_mode: If True, operates without loading YOLO weights (useful for testing or pipeline mocks).
        """
        self.conf_threshold = conf_threshold
        self.device = device
        self.offline_mode = offline_mode
        self.severity_calculator = SeverityCalculator(severity_config)
        self.model: Any = None
        self.weights_path: Optional[str] = None

        if not self.offline_mode:
            self._init_model(model_path, auto_download)

    def _init_model(self, model_path: Optional[str], auto_download: bool) -> None:
        """Load YOLO model from local weights or download them."""
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "Ultralytics package is required for PotholeDetector. "
                "Install it via `pip install ultralytics` or run in offline_mode=True."
            ) from exc

        if auto_download or (model_path and Path(model_path).exists()):
            self.weights_path = ensure_model_weights(model_path)
            self.model = YOLO(self.weights_path)
        elif model_path:
            self.weights_path = model_path
            self.model = YOLO(model_path)
        else:
            raise ValueError(
                "Model path not specified and auto_download is disabled. "
                "Provide a local weight file path or enable auto_download."
            )

    def detect(
        self,
        frame: Union[str, Path, np.ndarray, Image.Image, bytes],
        gps: Optional[GPSCoordinate] = None,
        timestamp: Optional[Union[str, datetime]] = None,
        frame_id: Optional[str] = None,
        auto_extract_gps: bool = True,
        is_bgr: bool = False,
    ) -> PotholeDetectionResult:
        """Run pothole detection on a single image or video frame.

        Args:
            frame: Input frame as a file path, Path object, NumPy array, PIL Image, or bytes.
            gps: Explicit GPS coordinate to attach. If None and auto_extract_gps=True, extracts from EXIF.
            timestamp: Explicit timestamp (datetime or ISO string). Defaults to current UTC time.
            frame_id: Custom frame/sequence identifier. Defaults to generated UUID4.
            auto_extract_gps: If True and gps is None, attempts to extract GPS tags from image EXIF.
            is_bgr: If True and frame is a NumPy array, indicates BGR format (e.g. from OpenCV video streams).

        Returns:
            PotholeDetectionResult with detections, bounding boxes, severity ratings, GPS, and timestamp.
        """
        # 1. Normalize frame input
        frame_arr, width, height = normalize_frame(frame, is_bgr=is_bgr)

        # 2. Resolve metadata (ID, Timestamp, GPS)
        resolved_frame_id = frame_id or uuid.uuid4().hex[:12]

        if timestamp is None:
            resolved_timestamp = datetime.now(timezone.utc).isoformat()
        elif isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            resolved_timestamp = timestamp.isoformat()
        else:
            resolved_timestamp = str(timestamp)

        resolved_gps = gps
        if resolved_gps is None and auto_extract_gps:
            resolved_gps = extract_exif_gps(frame)

        # 3. Execute inference
        t_start = time.perf_counter()
        detections: List[PotholeDetection] = []

        if not self.offline_mode and self.model is not None:
            results = self.model.predict(
                source=frame_arr,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )

            if results and len(results) > 0:
                result_item = results[0]
                boxes = result_item.boxes
                if boxes is not None and len(boxes) > 0:
                    for i, box in enumerate(boxes, start=1):
                        xyxy = box.xyxy[0].tolist()
                        conf = float(box.conf[0])

                        bbox = BoundingBox(
                            x1=float(xyxy[0]),
                            y1=float(xyxy[1]),
                            x2=float(xyxy[2]),
                            y2=float(xyxy[3]),
                            image_width=width,
                            image_height=height,
                        )

                        severity_level, severity_score = self.severity_calculator.calculate(bbox)

                        detections.append(
                            PotholeDetection(
                                id=i,
                                confidence=conf,
                                bbox=bbox,
                                severity=severity_level,
                                severity_score=severity_score,
                                class_name="pothole",
                            )
                        )

        processing_time_ms = (time.perf_counter() - t_start) * 1000.0

        return PotholeDetectionResult(
            frame_id=resolved_frame_id,
            timestamp=resolved_timestamp,
            image_width=width,
            image_height=height,
            detections=detections,
            gps=resolved_gps,
            processing_time_ms=processing_time_ms,
        )

    def detect_batch(
        self,
        frames: List[Union[str, Path, np.ndarray, Image.Image, bytes]],
        gps_list: Optional[List[Optional[GPSCoordinate]]] = None,
        timestamps: Optional[List[Optional[Union[str, datetime]]]] = None,
    ) -> List[PotholeDetectionResult]:
        """Run pothole detection over a list of frames.

        Args:
            frames: List of frames to process.
            gps_list: Optional list of GPS coordinates matching the length of frames.
            timestamps: Optional list of timestamps matching the length of frames.

        Returns:
            List of PotholeDetectionResult objects.
        """
        results: List[PotholeDetectionResult] = []
        for i, frame in enumerate(frames):
            gps = gps_list[i] if (gps_list and i < len(gps_list)) else None
            ts = timestamps[i] if (timestamps and i < len(timestamps)) else None
            results.append(self.detect(frame=frame, gps=gps, timestamp=ts))
        return results
