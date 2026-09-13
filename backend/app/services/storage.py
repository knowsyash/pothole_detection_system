"""Storage service for saving and managing image evidence across local disk and Cloudflare R2 / AWS S3."""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import aiofiles
from fastapi import UploadFile
from app.config import settings

logger = logging.getLogger("okdriver.storage")


class StorageService:
    """Handles storage of pothole evidence images and annotated frames."""

    def __init__(self, upload_dir: Optional[Path] = None, url_prefix: Optional[str] = None):
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        self.url_prefix = url_prefix or settings.STATIC_URL_PREFIX
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.s3_client = None
        self.bucket_name = getattr(settings, "R2_BUCKET_NAME", "potholeimage")
        self.public_url_prefix = getattr(settings, "R2_PUBLIC_URL_PREFIX", None)

        # Initialize boto3 S3/R2 client if credentials are configured
        r2_endpoint = getattr(settings, "R2_ENDPOINT_URL", None)
        r2_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
        r2_secret = getattr(settings, "R2_SECRET_ACCESS_KEY", None)

        if r2_endpoint and r2_key and r2_secret:
            try:
                import boto3
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=r2_endpoint,
                    aws_access_key_id=r2_key,
                    aws_secret_access_key=r2_secret,
                    region_name="auto",
                )
                logger.info(f"Cloudflare R2 storage initialized for bucket '{self.bucket_name}'.")
            except Exception as e:
                logger.warning(f"Failed to initialize Cloudflare R2 client: {e}")

    def _generate_filename(self, prefix: str = "pothole", extension: str = ".jpg") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_token = uuid.uuid4().hex[:8]
        if not extension.startswith("."):
            extension = f".{extension}"
        return f"{prefix}_{timestamp}_{unique_token}{extension}"

    def _upload_to_r2(self, data: bytes, filename: str, content_type: str = "image/jpeg") -> Optional[str]:
        """Upload binary data to Cloudflare R2 bucket."""
        if not self.s3_client:
            return None
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Successfully uploaded {filename} to Cloudflare R2 bucket '{self.bucket_name}'.")
            if self.public_url_prefix:
                return f"{self.public_url_prefix.rstrip('/')}/{filename}"
            return None
        except Exception as exc:
            logger.error(f"Failed to upload {filename} to Cloudflare R2: {exc}")
            return None

    async def save_upload_file(self, upload_file: UploadFile, prefix: str = "evidence") -> str:
        """Save a FastAPI UploadFile to local disk and Cloudflare R2."""
        ext = os.path.splitext(upload_file.filename or "")[1] or ".jpg"
        filename = self._generate_filename(prefix=prefix, extension=ext)
        dest_path = self.upload_dir / filename

        contents = await upload_file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)

        content_type = upload_file.content_type or ("video/mp4" if ext in (".mp4", ".mov") else "image/jpeg")
        r2_url = self._upload_to_r2(contents, filename, content_type=content_type)
        return r2_url or f"{self.url_prefix}/{filename}"

    def save_bytes(self, data: bytes, prefix: str = "annotated", extension: str = ".jpg") -> str:
        """Save raw bytes to disk and Cloudflare R2."""
        filename = self._generate_filename(prefix=prefix, extension=extension)
        dest_path = self.upload_dir / filename

        with open(dest_path, "wb") as f:
            f.write(data)

        content_type = "video/mp4" if extension in (".mp4", ".mov") else "image/jpeg"
        r2_url = self._upload_to_r2(data, filename, content_type=content_type)
        return r2_url or f"{self.url_prefix}/{filename}"

    def save_local_file_copy(self, source_path: Union[str, Path], prefix: str = "frame") -> str:
        """Copy an existing local image into evidence store and Cloudflare R2."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file {source} does not exist")

        ext = source.suffix or ".jpg"
        filename = self._generate_filename(prefix=prefix, extension=ext)
        dest_path = self.upload_dir / filename

        with open(source, "rb") as sf:
            data = sf.read()

        with open(dest_path, "wb") as df:
            df.write(data)

        content_type = "video/mp4" if ext in (".mp4", ".mov") else "image/jpeg"
        r2_url = self._upload_to_r2(data, filename, content_type=content_type)
        return r2_url or f"{self.url_prefix}/{filename}"


storage_service = StorageService()
