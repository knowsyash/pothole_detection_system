"""Rough severity calculation engine based on bounding box metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from okdriver.models import BoundingBox, SeverityLevel


@dataclass
class SeverityConfig:
    """Configurable thresholds for bounding-box based severity calculation.

    Thresholds represent the ratio of bounding box area to total frame area (0.0 to 1.0).
    Default thresholds:
      - LOW: area < 1% of frame
      - MEDIUM: 1% <= area < 4% of frame
      - HIGH: 4% <= area < 8% of frame
      - CRITICAL: area >= 8% of frame
    """
    low_max_ratio: float = 0.010       # Up to 1.0% of frame
    medium_max_ratio: float = 0.040    # 1.0% to 4.0% of frame
    high_max_ratio: float = 0.080      # 4.0% to 8.0% of frame
    min_score: float = 1.0             # Baseline score for any confirmed pothole
    max_score: float = 10.0            # Upper bound for severity score

    def __post_init__(self) -> None:
        if not (0 < self.low_max_ratio < self.medium_max_ratio < self.high_max_ratio <= 1.0):
            raise ValueError(
                "Thresholds must satisfy: 0 < low_max_ratio < medium_max_ratio < high_max_ratio <= 1.0"
            )
        if self.min_score < 0 or self.max_score <= self.min_score:
            raise ValueError("Scores must satisfy: 0 <= min_score < max_score")


class SeverityCalculator:
    """Calculates categorical and numeric pothole severity from bounding box dimensions."""

    def __init__(self, config: Optional[SeverityConfig] = None) -> None:
        self.config = config or SeverityConfig()

    def calculate(self, bbox: BoundingBox) -> Tuple[SeverityLevel, float]:
        """Compute severity level and continuous score (0.0 - 10.0) from a bounding box.

        Args:
            bbox: BoundingBox object with pixel dimensions and frame context.

        Returns:
            Tuple of (SeverityLevel, severity_score as float).
        """
        # Relative area of the pothole relative to the frame (0.0 - 1.0)
        rel_area = bbox.relative_area

        # Fallback if image dimensions were not supplied: estimate using pixel area assuming standard 1080p
        if rel_area == 0.0 and bbox.area > 0:
            reference_frame_area = 1920.0 * 1080.0
            rel_area = min(1.0, bbox.area / reference_frame_area)

        # 1. Categorical severity classification
        if rel_area < self.config.low_max_ratio:
            level = SeverityLevel.LOW
        elif rel_area < self.config.medium_max_ratio:
            level = SeverityLevel.MEDIUM
        elif rel_area < self.config.high_max_ratio:
            level = SeverityLevel.HIGH
        else:
            level = SeverityLevel.CRITICAL

        # 2. Continuous severity score (scaled smoothly from min_score to max_score)
        # We scale relative to high_max_ratio where high_max_ratio corresponds to ~8.5/10
        ratio_norm = min(1.5, rel_area / self.config.high_max_ratio)
        score_range = self.config.max_score - self.config.min_score
        raw_score = self.config.min_score + (ratio_norm / 1.5) * score_range
        score = round(max(self.config.min_score, min(self.config.max_score, raw_score)), 2)

        return level, score


# Default module-level singleton helper
_default_calculator = SeverityCalculator()


def calculate_severity(
    bbox: BoundingBox,
    config: Optional[SeverityConfig] = None
) -> Tuple[SeverityLevel, float]:
    """Convenience function to calculate severity using default or custom config."""
    if config is not None:
        return SeverityCalculator(config).calculate(bbox)
    return _default_calculator.calculate(bbox)
