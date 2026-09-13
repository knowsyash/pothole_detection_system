import json
import sys
from pathlib import Path

# Add project root to sys.path for direct script execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import cv2

from okdriver import (
    GPSCoordinate,
    PotholeDetector,
    SeverityConfig,
    annotate_frame,
    save_annotated_frame,
)


def main():
    print("==================================================================")
    print("           okdriver - Pothole Detection Demonstration             ")
    print("==================================================================")

    # 1. Initialize detector with default open-source YOLOv8 pothole weights
    print("\n[1] Initializing PotholeDetector (YOLOv8s pothole model)...")
    detector = PotholeDetector(
        conf_threshold=0.25,
        severity_config=SeverityConfig(
            low_max_ratio=0.01,       # < 1% frame area = LOW
            medium_max_ratio=0.04,    # 1% - 4% frame area = MEDIUM
            high_max_ratio=0.08,      # 4% - 8% frame area = HIGH, >= 8% = CRITICAL
        ),
    )
    print("    Model loaded successfully from:", detector.weights_path)

    # 2. Prepare sample image / video frame
    sample_image_path = Path("sample_pothole.jpg")
    if not sample_image_path.exists():
        print(f"Error: {sample_image_path} not found. Please provide an image.")
        return

    # 3. Define GPS telemetry metadata
    telemetry_gps = GPSCoordinate(
        latitude=37.774929,
        longitude=-122.419416,
        altitude=16.4,
        speed_kmh=42.5,
        heading_deg=85.0,
    )
    print(f"\n[2] Telemetry prepared: GPS=({telemetry_gps.latitude}, {telemetry_gps.longitude}), Speed={telemetry_gps.speed_kmh} km/h")

    # 4. Run detection
    print("\n[3] Running inference on road frame...")
    result = detector.detect(
        frame=str(sample_image_path),
        gps=telemetry_gps,
        frame_id="FRAME-SF-10492",
    )

    # 5. Inspect detection results
    print("\n[4] Detection Summary:")
    print(f"    Frame ID         : {result.frame_id}")
    print(f"    Timestamp (UTC)  : {result.timestamp}")
    print(f"    Dimensions       : {result.image_width}x{result.image_height} px")
    print(f"    Potholes Found   : {result.total_potholes}")
    print(f"    Max Severity     : {result.max_severity.value if result.max_severity else 'None'}")
    print(f"    Max Score (0-10) : {result.max_severity_score:.1f} / 10.0")
    print(f"    Latency          : {result.processing_time_ms:.1f} ms")

    print("\n    Individual Pothole Breakdown:")
    for det in result.detections:
        box = det.bbox
        print(f"    - Pothole #{det.id}:")
        print(f"        Confidence    : {det.confidence:.1%}")
        print(f"        Bounding Box  : [{box.x1:.1f}, {box.y1:.1f}, {box.x2:.1f}, {box.y2:.1f}] (WxH: {box.width:.1f}x{box.height:.1f} px)")
        print(f"        Relative Area : {box.relative_area:.2%} of frame")
        print(f"        Severity      : {det.severity.value} (Score: {det.severity_score:.1f}/10)")

    # 6. JSON Export
    print("\n[5] Serialized JSON Result (first 500 chars):")
    json_output = result.to_json(indent=2)
    print(json_output[:500] + "\n    ... (truncated)")

    # 7. Save annotated visual output
    output_image_path = "demo_annotated_output.jpg"
    saved_path = save_annotated_frame(str(sample_image_path), result, output_image_path)
    print(f"\n[6] Visual annotation saved with telemetry overlay to: {saved_path}")

    # 8. Video Frame Stream Simulation (NumPy BGR array from OpenCV)
    print("\n[7] Simulating Video Stream frame input (OpenCV BGR numpy array)...")
    bgr_frame = cv2.imread(str(sample_image_path))
    stream_result = detector.detect(
        frame=bgr_frame,
        gps=GPSCoordinate(latitude=37.775100, longitude=-122.419000, speed_kmh=45.0),
        is_bgr=True,
    )
    print(f"    Processed video stream frame: {stream_result.total_potholes} potholes detected in {stream_result.processing_time_ms:.1f} ms")

    print("\n==================================================================")
    print("                    Demonstration Complete!                       ")
    print("==================================================================")


if __name__ == "__main__":
    main()
