"""Unit tests for okdriver data models."""

import json
import unittest

from okdriver.models import (
    BoundingBox,
    GPSCoordinate,
    PotholeDetection,
    PotholeDetectionResult,
    SeverityLevel,
)


class TestDataModels(unittest.TestCase):
    def test_gps_coordinate_valid(self):
        gps = GPSCoordinate(
            latitude=37.7749,
            longitude=-122.4194,
            altitude=15.3,
            speed_kmh=45.2,
            heading_deg=180.0,
        )
        d = gps.to_dict()
        self.assertEqual(d["latitude"], 37.7749)
        self.assertEqual(d["longitude"], -122.4194)
        self.assertEqual(d["altitude"], 15.3)
        self.assertEqual(d["speed_kmh"], 45.2)
        self.assertEqual(d["heading_deg"], 180.0)

    def test_gps_coordinate_validation(self):
        with self.assertRaises(ValueError):
            GPSCoordinate(latitude=95.0, longitude=0.0)
        with self.assertRaises(ValueError):
            GPSCoordinate(latitude=0.0, longitude=-200.0)
        with self.assertRaises(ValueError):
            GPSCoordinate(latitude=0.0, longitude=0.0, speed_kmh=-5.0)
        with self.assertRaises(ValueError):
            GPSCoordinate(latitude=0.0, longitude=0.0, heading_deg=400.0)

    def test_bounding_box_metrics(self):
        bbox = BoundingBox(
            x1=100.0,
            y1=200.0,
            x2=300.0,
            y2=350.0,
            image_width=1000,
            image_height=500,
        )
        self.assertEqual(bbox.width, 200.0)
        self.assertEqual(bbox.height, 150.0)
        self.assertEqual(bbox.area, 30000.0)

        # Frame area is 1000 * 500 = 500,000
        # Relative area = 30000 / 500000 = 0.06
        self.assertAlmostEqual(bbox.relative_area, 0.06, places=4)

        norm = bbox.normalized_xyxy
        self.assertIsNotNone(norm)
        self.assertAlmostEqual(norm[0], 0.1)
        self.assertAlmostEqual(norm[1], 0.4)
        self.assertAlmostEqual(norm[2], 0.3)
        self.assertAlmostEqual(norm[3], 0.7)

    def test_bounding_box_auto_ordering(self):
        # Inverted coords should be fixed automatically
        bbox = BoundingBox(x1=300.0, y1=400.0, x2=100.0, y2=200.0)
        self.assertEqual(bbox.x1, 100.0)
        self.assertEqual(bbox.x2, 300.0)
        self.assertEqual(bbox.y1, 200.0)
        self.assertEqual(bbox.y2, 400.0)

    def test_pothole_detection_result_aggregation(self):
        bbox1 = BoundingBox(x1=10, y1=10, x2=50, y2=50, image_width=1000, image_height=1000)
        bbox2 = BoundingBox(x1=200, y1=200, x2=600, y2=600, image_width=1000, image_height=1000)

        det1 = PotholeDetection(
            id=1,
            confidence=0.85,
            bbox=bbox1,
            severity=SeverityLevel.LOW,
            severity_score=1.5,
        )
        det2 = PotholeDetection(
            id=2,
            confidence=0.92,
            bbox=bbox2,
            severity=SeverityLevel.CRITICAL,
            severity_score=9.2,
        )

        gps = GPSCoordinate(latitude=40.7128, longitude=-74.0060)
        result = PotholeDetectionResult(
            frame_id="frame_001",
            timestamp="2026-09-11T21:30:00Z",
            image_width=1000,
            image_height=1000,
            detections=[det1, det2],
            gps=gps,
            processing_time_ms=18.5,
        )

        self.assertEqual(result.total_potholes, 2)
        self.assertTrue(result.has_potholes)
        self.assertEqual(result.max_severity, SeverityLevel.CRITICAL)
        self.assertEqual(result.max_severity_score, 9.2)

        # JSON serialization
        json_str = result.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["frame_id"], "frame_001")
        self.assertEqual(parsed["total_potholes"], 2)
        self.assertEqual(parsed["max_severity"], "CRITICAL")
        self.assertEqual(parsed["gps"]["latitude"], 40.7128)
        self.assertEqual(len(parsed["detections"]), 2)

    def test_empty_detection_result(self):
        result = PotholeDetectionResult(
            frame_id="empty_frame",
            timestamp="2026-09-11T21:30:00Z",
            image_width=1920,
            image_height=1080,
            detections=[],
        )
        self.assertEqual(result.total_potholes, 0)
        self.assertFalse(result.has_potholes)
        self.assertIsNone(result.max_severity)
        self.assertEqual(result.max_severity_score, 0.0)


if __name__ == "__main__":
    unittest.main()
