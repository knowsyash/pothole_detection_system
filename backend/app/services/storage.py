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
        self.auto_upload_r2 = getattr(settings, "ENABLE_R2_STORAGE", True)

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
        else:
            logger.info("Cloudflare R2 client not initialized (credentials missing or incomplete).")

    def _generate_filename(self, prefix: str = "pothole", extension: str = ".jpg") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_token = uuid.uuid4().hex[:8]
        if not extension.startswith("."):
            extension = f".{extension}"
        return f"{prefix}_{timestamp}_{unique_token}{extension}"

    def get_presigned_url(self, filename: str, expires_in: int = 604800) -> Optional[str]:
        """
        Generate a presigned GET URL for an object in Cloudflare R2.
        Default expiration is 7 days (604,800 seconds), the maximum permitted by AWS S3 SigV4.
        """
        if not self.s3_client:
            return None
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": filename},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            logger.error(f"Failed to generate presigned URL for {filename}: {exc}")
            return None

    def get_public_or_presigned_url(self, filename: str, expires_in: int = 604800) -> Optional[str]:
        """
        Return a direct public CDN URL if R2_PUBLIC_URL_PREFIX is set,
        otherwise generate a presigned Cloudflare R2 URL for instant access.
        """
        if self.public_url_prefix:
            return f"{self.public_url_prefix.rstrip('/')}/{filename}"
        return self.get_presigned_url(filename, expires_in=expires_in)

    def _upload_to_r2(self, data: bytes, filename: str, content_type: str = "image/jpeg") -> Optional[str]:
        """Upload binary data to Cloudflare R2 bucket and return a viewable URL."""
        if not self.s3_client:
            return None
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Successfully uploaded {filename} ({len(data)} bytes) to Cloudflare R2 bucket '{self.bucket_name}'.")
            return self.get_public_or_presigned_url(filename)
        except Exception as exc:
            logger.error(f"Failed to upload {filename} to Cloudflare R2: {exc}")
            return None

    def ensure_r2_url(self, evidence_path_or_url: Optional[str]) -> Optional[str]:
        """
        Ensure that an evidence asset (local file path or relative URL) is stored on Cloudflare R2
        and return a direct public/presigned URL that can be clicked directly from an email or phone.
        """
        if not evidence_path_or_url:
            return None

        clean_val = str(evidence_path_or_url).strip()
        if not clean_val or clean_val.lower() in ("none", "n/a", "null"):
            return None

        # Already an external public URL (e.g. https://...r2.cloudflarestorage.com or custom domain)
        if clean_val.startswith("http://") or clean_val.startswith("https://"):
            return clean_val

        filename = Path(clean_val).name
        local_path = self.upload_dir / filename

        if self.s3_client:
            if local_path.exists():
                try:
                    with open(local_path, "rb") as f:
                        data = f.read()
                    ext = local_path.suffix.lower()
                    content_type = "video/mp4" if ext in (".mp4", ".mov") else "image/jpeg"
                    url = self._upload_to_r2(data, filename, content_type=content_type)
                    if url:
                        return url
                except Exception as exc:
                    logger.warning(f"Error ensuring R2 upload for {filename}: {exc}")

            # If local file is missing from this machine (e.g. uploaded previously or on another host),
            # try generating the presigned URL directly for the filename in R2
            url = self.get_public_or_presigned_url(filename)
            if url:
                return url

        # Fallback to local static URL if R2 is unconfigured
        if clean_val.startswith("/"):
            return clean_val
        return f"{self.url_prefix}/{filename}"

    async def save_upload_file(self, upload_file: UploadFile, prefix: str = "evidence") -> str:
        """Save a FastAPI UploadFile to local disk and Cloudflare R2."""
        ext = os.path.splitext(upload_file.filename or "")[1] or ".jpg"
        filename = self._generate_filename(prefix=prefix, extension=ext)
        dest_path = self.upload_dir / filename

        contents = await upload_file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)

        content_type = upload_file.content_type or ("video/mp4" if ext in (".mp4", ".mov") else "image/jpeg")
        r2_url = None
        if self.auto_upload_r2:
            r2_url = self._upload_to_r2(contents, filename, content_type=content_type)
        return r2_url or f"{self.url_prefix}/{filename}"

    def save_bytes(self, data: bytes, prefix: str = "annotated", extension: str = ".jpg") -> str:
        """Save raw bytes to disk and Cloudflare R2."""
        filename = self._generate_filename(prefix=prefix, extension=extension)
        dest_path = self.upload_dir / filename

        with open(dest_path, "wb") as f:
            f.write(data)

        content_type = "video/mp4" if extension in (".mp4", ".mov") else "image/jpeg"
        r2_url = None
        if self.auto_upload_r2:
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
        r2_url = None
        if self.auto_upload_r2:
            r2_url = self._upload_to_r2(data, filename, content_type=content_type)
        return r2_url or f"{self.url_prefix}/{filename}"


storage_service = StorageService()
