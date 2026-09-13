"""Unit and integration tests for PotholeDetector and Visualizer."""

import unittest
from datetime import datetime, timezone
import numpy as np
from PIL import Image

from okdriver.detector import PotholeDetector
from okdriver.models import (
    BoundingBox,
    GPSCoordinate,
    PotholeDetection,
    PotholeDetectionResult,
    SeverityLevel,
)
from okdriver.visualizer import annotate_frame


class TestPotholeDetector(unittest.TestCase):
    def setUp(self):
        # Use offline_mode for fast unit testing without loading neural weights
        self.detector = PotholeDetector(offline_mode=True)
        # Synthetic 640x480 RGB frame
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_detect_with_explicit_gps_and_timestamp(self):
        gps = GPSCoordinate(
            latitude=12.9716,
            longitude=77.5946,
            altitude=920.0,
            speed_kmh=35.0,
            heading_deg=90.0,
        )
        custom_ts = "2026-09-11T12:00:00Z"
        result = self.detector.detect(
            frame=self.dummy_frame,
            gps=gps,
            timestamp=custom_ts,
            frame_id="custom_frame_42",
        )

        self.assertIsInstance(result, PotholeDetectionResult)
        self.assertEqual(result.frame_id, "custom_frame_42")
        self.assertEqual(result.timestamp, custom_ts)
        self.assertIsNotNone(result.gps)
        self.assertEqual(result.gps.latitude, 12.9716)
        self.assertEqual(result.gps.longitude, 77.5946)
        self.assertEqual(result.image_width, 640)
        self.assertEqual(result.image_height, 480)
        self.assertGreaterEqual(result.processing_time_ms, 0.0)

    def test_detect_with_pil_image(self):
        pil_img = Image.new("RGB", (800, 600), color=(128, 128, 128))
        result = self.detector.detect(frame=pil_img)
        self.assertEqual(result.image_width, 800)
        self.assertEqual(result.image_height, 600)
        self.assertIsNotNone(result.timestamp)

    def test_detect_batch(self):
        frames = [
            np.zeros((100, 100, 3), dtype=np.uint8),
            np.zeros((200, 200, 3), dtype=np.uint8),
        ]
        results = self.detector.detect_batch(frames)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].image_width, 100)
        self.assertEqual(results[1].image_width, 200)

    def test_visualizer_annotation(self):
        # Create a synthetic result with 2 potholes
        bbox1 = BoundingBox(x1=50, y1=50, x2=120, y2=100, image_width=640, image_height=480)
        bbox2 = BoundingBox(x1=200, y1=250, x2=450, y2=400, image_width=640, image_height=480)

        det1 = PotholeDetection(1, 0.88, bbox1, SeverityLevel.LOW, 2.1)
        det2 = PotholeDetection(2, 0.94, bbox2, SeverityLevel.HIGH, 7.4)

        result = PotholeDetectionResult(
            frame_id="test_viz",
            timestamp="2026-09-11T21:30:00Z",
            image_width=640,
            image_height=480,
            detections=[det1, det2],
            gps=GPSCoordinate(latitude=37.7749, longitude=-122.4194),
        )

        annotated = annotate_frame(self.dummy_frame, result)
        self.assertEqual(annotated.shape, (480, 640, 3))
        # Verify canvas is not blank (drawn boxes modified pixel values)
        self.assertGreater(np.sum(annotated), 0)


if __name__ == "__main__":
    unittest.main()
