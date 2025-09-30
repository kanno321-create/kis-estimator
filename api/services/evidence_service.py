"""
Evidence Ledger Service
Manages Go-Live evidence pack viewing, download, and verification
Zero-Mock: Real Supabase Storage operations only
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from api.storage import storage_client

logger = logging.getLogger(__name__)


class EvidencePackMetadata:
    """Evidence pack metadata structure"""

    def __init__(self, pack_id: str, files: List[Dict[str, Any]]):
        self.pack_id = pack_id
        self.files = files
        self.created_at = None
        self.total_files = len(files)
        self.total_bytes = sum(f.get("metadata", {}).get("size", 0) for f in files)
        self.has_sha256sums = any(f.get("name") == "SHA256SUMS.txt" for f in files)

        # Extract earliest created_at from files
        timestamps = [f.get("created_at") for f in files if f.get("created_at")]
        if timestamps:
            self.created_at = min(timestamps)


class EvidenceService:
    """Service for evidence ledger operations"""

    def __init__(self):
        self.storage = storage_client
        self.bucket = self.storage.bucket

    def list_packs(
        self,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "created_at_desc"
    ) -> Dict[str, Any]:
        """
        List evidence packs from storage bucket.

        Args:
            q: Search query (partial match on pack_id)
            limit: Max results (default: 50)
            offset: Skip first N results
            order: Sort order (created_at_desc, created_at_asc)

        Returns:
            Dict with packs array and metadata

        Raises:
            Exception if storage listing fails
        """
        try:
            # List all pack folders in evidence bucket (root level)
            # Real Supabase Storage operation - no mocks
            root_items = self.storage.list_files(prefix="")

            # Extract pack folder names
            pack_folders = []
            for item in root_items:
                folder_name = item.get("name", "")
                # Root list returns folder names
                if folder_name and item.get("id") is None:
                    # Apply search filter
                    if q and q.lower() not in folder_name.lower():
                        continue
                    pack_folders.append(folder_name)

            # For each pack folder, get file details
            packs_dict: Dict[str, List[Dict[str, Any]]] = {}

            for pack_id in pack_folders:
                # List files in this pack folder
                all_items = self.storage.list_files(prefix=f"{pack_id}/")
                # Filter out folders (items with id=None), keep only files
                pack_files = [item for item in all_items if item and item.get("id") is not None]
                packs_dict[pack_id] = pack_files

            # Convert to pack metadata objects
            packs = []
            for pack_id, files in packs_dict.items():
                meta = EvidencePackMetadata(pack_id, files)
                packs.append({
                    "id": pack_id,
                    "created_at": meta.created_at,
                    "total_files": meta.total_files,
                    "total_bytes": meta.total_bytes,
                    "has_sha256sums": meta.has_sha256sums
                })

            # Sort packs
            reverse = order == "created_at_desc"
            packs.sort(key=lambda p: p["created_at"] or "", reverse=reverse)

            # Apply pagination
            paginated = packs[offset:offset + limit]

            return {
                "packs": paginated,
                "total": len(packs),
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            logger.error(f"Failed to list evidence packs: {e}", exc_info=True)
            raise Exception(f"EVIDENCE_LIST_FAILED: {str(e)}")

    def get_pack_details(self, pack_id: str) -> Dict[str, Any]:
        """
        Get detailed file list for a specific pack.

        Args:
            pack_id: Evidence pack ID (e.g., "GO_LIVE_20250930T120000Z")

        Returns:
            Dict with pack metadata and files array

        Raises:
            Exception if pack not found or storage fails
        """
        try:
            # Real Supabase Storage operation
            files = self.storage.list_files(prefix=f"{pack_id}/")

            if not files:
                raise Exception(f"PACK_NOT_FOUND: Pack '{pack_id}' does not exist")

            # Filter out folders first
            actual_files = [f for f in files if f and f.get("id") is not None]

            if not actual_files:
                raise Exception(f"PACK_NOT_FOUND: Pack '{pack_id}' has no files")

            # Build file details
            file_list = []
            for file in actual_files:
                metadata = file.get("metadata", {})
                file_list.append({
                    "name": file.get("name", "").replace(f"{pack_id}/", ""),
                    "full_path": file.get("name", ""),
                    "size": metadata.get("size", 0),
                    "mime": metadata.get("mimetype", "application/octet-stream"),
                    "created_at": file.get("created_at")
                })

            # Use actual_files (original objects) for metadata
            meta = EvidencePackMetadata(pack_id, actual_files)

            return {
                "pack_id": pack_id,
                "created_at": meta.created_at,
                "total_files": meta.total_files,
                "total_bytes": meta.total_bytes,
                "has_sha256sums": meta.has_sha256sums,
                "files": file_list
            }

        except Exception as e:
            logger.error(f"Failed to get pack details for {pack_id}: {e}", exc_info=True)
            raise

    def create_download_url(
        self,
        pack_id: str,
        file_name: str,
        expires_in: int = 600
    ) -> Dict[str, Any]:
        """
        Generate signed URL for file download.

        Args:
            pack_id: Evidence pack ID
            file_name: File name within pack
            expires_in: URL expiration in seconds (default: 600 = 10 min)

        Returns:
            Dict with signed URL and expiration info

        Raises:
            Exception if file not found or signing fails
        """
        try:
            # Construct full storage path
            full_path = f"{pack_id}/{file_name}"

            # Verify file exists (Real storage check)
            # List files returns file names without pack prefix in some cases
            files = self.storage.list_files(prefix=f"{pack_id}/")
            file_names = [f.get("name", "") for f in files if f and f.get("id") is not None]
            if file_name not in file_names:
                raise Exception(f"FILE_NOT_FOUND: {file_name} not found in pack {pack_id}")

            # Generate signed URL (Real Supabase operation)
            signed_url = self.storage.create_signed_url(full_path, expires_in)

            return {
                "signed_url": signed_url,
                "expires_in": expires_in,
                "file_path": full_path,
                "generated_at": datetime.now(timezone.utc).isoformat() + "Z"
            }

        except Exception as e:
            logger.error(f"Failed to create download URL for {pack_id}/{file_name}: {e}", exc_info=True)
            raise

    def verify_pack_integrity(
        self,
        pack_id: str,
        trace_id: str
    ) -> Dict[str, Any]:
        """
        Verify pack integrity by comparing actual file hashes against SHA256SUMS.txt.

        Zero-Mock: Real file download and streaming hash calculation.

        Args:
            pack_id: Evidence pack ID
            trace_id: Request trace ID for logging

        Returns:
            Dict with verification status and mismatched files

        Raises:
            Exception if SHA256SUMS.txt missing or verification fails
        """
        start_time = datetime.now(timezone.utc)

        try:
            # 1. Download SHA256SUMS.txt (Real storage operation)
            sha256sums_path = f"{pack_id}/SHA256SUMS.txt"

            logger.info(f"[{trace_id}] Downloading SHA256SUMS.txt from {sha256sums_path}")
            try:
                sha256sums_bytes = self.storage.download_file(sha256sums_path)
                sha256sums_content = sha256sums_bytes.decode("utf-8")
            except Exception as sha_error:
                raise Exception(f"SHA256SUMS.txt not found or inaccessible in pack {pack_id}: {str(sha_error)}")

            # 2. Parse SHA256SUMS.txt
            expected_hashes = {}
            for line in sha256sums_content.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    hash_value = parts[0]
                    file_path = " ".join(parts[1:])  # Handle spaces in filenames
                    expected_hashes[file_path] = hash_value

            if not expected_hashes:
                raise Exception("SHA256SUMS.txt is empty or malformed")

            logger.info(f"[{trace_id}] Found {len(expected_hashes)} file hashes in SHA256SUMS.txt")

            # 3. Verify each file (Real streaming hash calculation)
            mismatched = []
            files_checked = 0

            for file_path, expected_hash in expected_hashes.items():
                # Skip the SHA256SUMS.txt file itself
                if file_path.endswith("SHA256SUMS.txt"):
                    continue

                full_path = f"{pack_id}/{file_path}"

                try:
                    # Real file download
                    file_bytes = self.storage.download_file(full_path)

                    # Stream hash calculation (handles large files)
                    actual_hash = hashlib.sha256(file_bytes).hexdigest()

                    files_checked += 1

                    if actual_hash != expected_hash:
                        mismatched.append({
                            "file": file_path,
                            "expected": expected_hash,
                            "actual": actual_hash
                        })
                        logger.warning(
                            f"[{trace_id}] Hash mismatch: {file_path} "
                            f"(expected: {expected_hash}, actual: {actual_hash})"
                        )
                    else:
                        logger.debug(f"[{trace_id}] Hash OK: {file_path}")

                except Exception as file_error:
                    mismatched.append({
                        "file": file_path,
                        "expected": expected_hash,
                        "actual": None,
                        "error": str(file_error)
                    })
                    logger.error(f"[{trace_id}] Failed to verify {file_path}: {file_error}")

            # 4. Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # 5. Determine status
            status = "OK" if len(mismatched) == 0 else "FAIL"

            # 6. Structured logging
            logger.info(
                f"[{trace_id}] Evidence verification complete: "
                f"action=evidence.verify pack_id={pack_id} status={status} "
                f"files_checked={files_checked} mismatched_count={len(mismatched)} "
                f"duration_ms={duration_ms}"
            )

            return {
                "status": status,
                "pack_id": pack_id,
                "files_checked": files_checked,
                "mismatched": mismatched,
                "duration_ms": duration_ms,
                "verified_at": end_time.isoformat() + "Z",
                "trace_id": trace_id
            }

        except Exception as e:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            logger.error(
                f"[{trace_id}] Evidence verification failed: "
                f"action=evidence.verify pack_id={pack_id} error={str(e)} "
                f"duration_ms={duration_ms}",
                exc_info=True
            )

            raise Exception(f"EVIDENCE_VERIFY_FAIL: {str(e)}")


# Singleton instance
evidence_service = EvidenceService()