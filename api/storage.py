"""
KIS Estimator Supabase Storage Module
Storage client for evidence bucket with signed URL generation
"""
from supabase import create_client, Client
import logging
import uuid
from datetime import datetime

from api.config import config

logger = logging.getLogger(__name__)


class StorageClient:
    """Supabase Storage client for evidence bucket operations"""

    def __init__(self):
        """Initialize Supabase client with service role key"""
        self.client: Client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_SERVICE_ROLE_KEY,  # Service role for admin operations
        )
        self.bucket = config.STORAGE_BUCKET

    def upload_file(
        self,
        path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """
        Upload file to evidence bucket.

        Args:
            path: Storage path (e.g., "quote/UUID/stage/hash.ext")
            file_data: File content as bytes
            content_type: MIME type

        Returns:
            dict with path and metadata

        Raises:
            Exception if upload fails
        """
        try:
            self.client.storage.from_(self.bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "false"},
            )

            logger.info(f"File uploaded successfully: {path}")
            return {"path": path, "bucket": self.bucket, "uploaded": True}

        except Exception as e:
            logger.error(f"File upload failed for {path}: {e}")
            raise

    def create_signed_url(self, path: str, expires_in: int = 600) -> str:
        """
        Generate signed URL for private file access.

        Args:
            path: Storage path
            expires_in: TTL in seconds (default: 600 = 10 minutes)

        Returns:
            Signed URL string

        Raises:
            Exception if generation fails
        """
        try:
            result = self.client.storage.from_(self.bucket).create_signed_url(
                path=path, expires_in=expires_in
            )

            if isinstance(result, dict) and "signedURL" in result:
                signed_url = result["signedURL"]
            else:
                signed_url = result

            logger.info(f"Signed URL created for: {path} (expires in {expires_in}s)")
            return signed_url

        except Exception as e:
            logger.error(f"Signed URL creation failed for {path}: {e}")
            raise

    def delete_file(self, path: str) -> dict:
        """
        Delete file from evidence bucket.

        Args:
            path: Storage path

        Returns:
            dict with deletion status

        Raises:
            Exception if deletion fails
        """
        try:
            self.client.storage.from_(self.bucket).remove([path])
            logger.info(f"File deleted: {path}")
            return {"path": path, "deleted": True}

        except Exception as e:
            logger.error(f"File deletion failed for {path}: {e}")
            raise

    def download_file(self, path: str) -> bytes:
        """
        Download file from evidence bucket.

        Args:
            path: Storage path

        Returns:
            File bytes

        Raises:
            Exception if download fails
        """
        try:
            result = self.client.storage.from_(self.bucket).download(path)
            logger.info(f"File downloaded: {path}")
            return result

        except Exception as e:
            logger.error(f"File download failed for {path}: {e}")
            raise

    def list_files(self, prefix: str = "") -> list:
        """
        List files in evidence bucket with optional prefix filter.

        Args:
            prefix: Path prefix filter (e.g., "quote/UUID/")

        Returns:
            List of file objects

        Raises:
            Exception if listing fails
        """
        try:
            result = self.client.storage.from_(self.bucket).list(path=prefix)
            return result

        except Exception as e:
            logger.error(f"File listing failed for prefix {prefix}: {e}")
            raise

    async def check_storage_health(self) -> dict:
        """
        Check storage connectivity by uploading and downloading a test file.

        Returns:
            dict with status, accessible, and optional error
        """
        test_path = f"readyz/{uuid.uuid4()}.txt"
        test_content = f"Health check at {datetime.utcnow().isoformat()}Z".encode(
            "utf-8"
        )

        try:
            # Upload test file
            self.upload_file(test_path, test_content, "text/plain")

            # Generate signed URL (verifies URL generation works)
            self.create_signed_url(test_path, expires_in=60)

            # Clean up test file
            self.delete_file(test_path)

            return {
                "status": "ok",
                "accessible": True,
                "bucket": self.bucket,
            }

        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "error",
                "accessible": False,
                "error": str(e),
            }


# Global storage client instance
storage_client = StorageClient()