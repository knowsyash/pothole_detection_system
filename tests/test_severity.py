"""Unit tests for severity calculation engine."""

import unittest

from okdriver.models import BoundingBox, SeverityLevel
from okdriver.severity import SeverityCalculator, SeverityConfig, calculate_severity


class TestSeverityCalculation(unittest.TestCase):
    def setUp(self):
        self.width = 1000
        self.height = 1000
        # Total frame area = 1,000,000 pixels

    def test_low_severity(self):
        # 0.5% area = 5,000 pixels -> 50x100
        bbox = BoundingBox(x1=0, y1=0, x2=50, y2=100, image_width=self.width, image_height=self.height)
        level, score = calculate_severity(bbox)
        self.assertEqual(level, SeverityLevel.LOW)
        self.assertGreaterEqual(score, 1.0)
        self.assertLess(score, 4.0)

    def test_medium_severity(self):
        # 2.0% area = 20,000 pixels -> 100x200
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=200, image_width=self.width, image_height=self.height)
        level, score = calculate_severity(bbox)
        self.assertEqual(level, SeverityLevel.MEDIUM)
        self.assertGreater(score, 2.0)
        self.assertLess(score, 7.0)

    def test_high_severity(self):
        # 6.0% area = 60,000 pixels -> 200x300
        bbox = BoundingBox(x1=0, y1=0, x2=200, y2=300, image_width=self.width, image_height=self.height)
        level, score = calculate_severity(bbox)
        self.assertEqual(level, SeverityLevel.HIGH)
        self.assertGreater(score, 5.0)
        self.assertLess(score, 10.0)

    def test_critical_severity(self):
        # 10.0% area = 100,000 pixels -> 316x316 approx
        bbox = BoundingBox(x1=0, y1=0, x2=350, y2=300, image_width=self.width, image_height=self.height)
        level, score = calculate_severity(bbox)
        self.assertEqual(level, SeverityLevel.CRITICAL)
        self.assertGreaterEqual(score, 8.0)
        self.assertLessEqual(score, 10.0)

    def test_custom_severity_config(self):
        custom_config = SeverityConfig(
            low_max_ratio=0.005,
            medium_max_ratio=0.020,
            high_max_ratio=0.050,
            min_score=0.5,
            max_score=5.0,
        )
        calculator = SeverityCalculator(custom_config)
        # 1.5% area was MEDIUM under default, should be MEDIUM here as well
        bbox = BoundingBox(x1=0, y1=0, x2=150, y2=100, image_width=self.width, image_height=self.height)
        level, score = calculator.calculate(bbox)
        self.assertEqual(level, SeverityLevel.MEDIUM)
        self.assertLessEqual(score, 5.0)

    def test_invalid_severity_config(self):
        with self.assertRaises(ValueError):
            SeverityConfig(low_max_ratio=0.05, medium_max_ratio=0.02)  # Low > medium


if __name__ == "__main__":
    unittest.main()
