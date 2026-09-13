"""Utility functions for frame loading, EXIF GPS extraction, and weight caching."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import numpy as np
from PIL import ExifTags, Image

from okdriver.models import GPSCoordinate

# Default open-source pothole model URL on Hugging Face (YOLOv8s, ~22.5 MB)
DEFAULT_MODEL_URL = "https://huggingface.co/peterhdd/pothole-detection-yolov8/resolve/main/best.pt"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "okdriver" / "weights"


def normalize_frame(
    frame_input: Union[str, Path, np.ndarray, Image.Image, bytes],
    is_bgr: bool = False,
) -> Tuple[np.ndarray, int, int]:
    """Convert various frame input types into a standardized NumPy array (RGB compatible).

    Args:
        frame_input: File path, Path object, NumPy array, PIL Image, or raw image bytes.
        is_bgr: If True and frame_input is a NumPy array, indicates it is in BGR format (e.g., from cv2.imread or cv2.VideoCapture).
                It will be converted to RGB.

    Returns:
        Tuple of (frame_array as np.ndarray in RGB, width as int, height as int).
    """
    if isinstance(frame_input, (str, Path)):
        path = Path(frame_input)
        if not path.exists():
            raise FileNotFoundError(f"Frame image file not found: {path}")
        with Image.open(path) as img:
            img = img.convert("RGB")
            arr = np.array(img)
            height, width = arr.shape[:2]
            return arr, width, height

    elif isinstance(frame_input, Image.Image):
        img = frame_input.convert("RGB")
        arr = np.array(img)
        height, width = arr.shape[:2]
        return arr, width, height

    elif isinstance(frame_input, bytes):
        with Image.open(io.BytesIO(frame_input)) as img:
            img = img.convert("RGB")
            arr = np.array(img)
            height, width = arr.shape[:2]
            return arr, width, height

    elif isinstance(frame_input, np.ndarray):
        if frame_input.ndim not in (2, 3):
            raise ValueError(f"Invalid frame array dimensions: {frame_input.ndim} (expected 2 or 3)")
        height, width = frame_input.shape[:2]
        if is_bgr and frame_input.ndim == 3 and frame_input.shape[2] == 3:
            import cv2
            arr = cv2.cvtColor(frame_input, cv2.COLOR_BGR2RGB)
            return arr, width, height
        return frame_input, width, height

    else:
        raise TypeError(
            f"Unsupported frame input type: {type(frame_input)}. "
            "Supported: str, Path, np.ndarray, PIL.Image, or bytes."
        )


def _dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    """Convert degrees, minutes, seconds tuple/ratio to decimal degrees."""
    try:
        if isinstance(dms, (list, tuple)) and len(dms) >= 3:
            deg = float(dms[0])
            min_val = float(dms[1])
            sec = float(dms[2])
            decimal = deg + (min_val / 60.0) + (sec / 3600.0)
            if ref in ("S", "W"):
                decimal = -decimal
            return decimal
    except Exception:
        return None
    return None


def extract_exif_gps(
    image_input: Union[str, Path, Image.Image, bytes]
) -> Optional[GPSCoordinate]:
    """Attempt to extract GPS coordinates from image EXIF metadata.

    Args:
        image_input: File path, Path object, PIL Image, or bytes.

    Returns:
        GPSCoordinate if valid EXIF GPS data is found, else None.
    """
    try:
        pil_img: Optional[Image.Image] = None
        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.exists():
                return None
            pil_img = Image.open(path)
        elif isinstance(image_input, bytes):
            pil_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            pil_img = image_input

        if pil_img is None:
            return None

        exif_raw = pil_img.getexif()
        if not exif_raw:
            return None

        # Look for GPSInfo tag (0x8825)
        gps_info = None
        for tag_id, value in exif_raw.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                gps_info = value
                break

        # In modern Pillow, get_ifd(ExifTags.IFD.GPSInfo) is preferred
        if not gps_info:
            try:
                gps_info = exif_raw.get_ifd(ExifTags.IFD.GPSInfo)
            except Exception:
                gps_info = None

        if not gps_info:
            return None

        # GPS tag indices
        # 1: GPSLatitudeRef, 2: GPSLatitude, 3: GPSLongitudeRef, 4: GPSLongitude, 6: GPSAltitude
        lat_ref = gps_info.get(1) or gps_info.get("GPSLatitudeRef")
        lat_val = gps_info.get(2) or gps_info.get("GPSLatitude")
        lon_ref = gps_info.get(3) or gps_info.get("GPSLongitudeRef")
        lon_val = gps_info.get(4) or gps_info.get("GPSLongitude")
        alt_val = gps_info.get(6) or gps_info.get("GPSAltitude")

        if lat_val and lat_ref and lon_val and lon_ref:
            latitude = _dms_to_decimal(lat_val, str(lat_ref).upper())
            longitude = _dms_to_decimal(lon_val, str(lon_ref).upper())
            if latitude is not None and longitude is not None:
                altitude = float(alt_val) if alt_val is not None else None
                return GPSCoordinate(
                    latitude=latitude,
                    longitude=longitude,
                    altitude=altitude,
                )
    except Exception:
        return None
    return None


def ensure_model_weights(
    model_path: Optional[str] = None,
    cache_dir: Optional[Union[str, Path]] = None,
    timeout: int = 60,
) -> str:
    """Ensure YOLO pothole weights are available locally, downloading if necessary.

    Args:
        model_path: Path to local .pt file, or HTTP/HTTPS URL. If None, uses DEFAULT_MODEL_URL.
        cache_dir: Directory to store downloaded weights.
        timeout: HTTP download timeout in seconds.

    Returns:
        Absolute string path to verified local model weights file.
    """
    import urllib.request

    if model_path and os.path.exists(model_path):
        return str(Path(model_path).resolve())

    target_url = model_path if (model_path and model_path.startswith(("http://", "https://"))) else DEFAULT_MODEL_URL

    destination_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)

    # Derive filename from URL
    filename = target_url.rstrip("/").split("/")[-1]
    if not filename.endswith(".pt"):
        filename = "pothole_yolov8s.pt"
    local_file = destination_dir / filename

    if local_file.exists() and local_file.stat().st_size > 1_000_000:
        return str(local_file.resolve())

    # Download file with streaming
    temp_file = local_file.with_suffix(".tmp")
    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "okdriver-pothole-detector/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response, open(temp_file, "wb") as out_f:
            chunk_size = 1024 * 64  # 64 KB
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)

        # Rename temp file to destination upon successful completion
        temp_file.replace(local_file)
        return str(local_file.resolve())
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise RuntimeError(
            f"Failed to download pothole model weights from '{target_url}': {e}"
        ) from e
