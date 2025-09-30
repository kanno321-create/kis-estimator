"""
Document Service with Async I/O Optimizations
Implements non-blocking file and HTTP operations
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

import aiofiles
import httpx
from fastapi import HTTPException, status

class DocumentService:
    """Service for document generation with async I/O"""

    def __init__(self):
        self.template_dir = Path(os.getenv("EXCEL_TEMPLATE_DIR", "./templates/excel"))
        self.output_dir = Path(os.getenv("EXCEL_OUTPUT_DIR", "./output/excel"))
        self.http_timeout = httpx.Timeout(10.0, connect=5.0)

    async def initialize(self):
        """Initialize service (placeholder for compatibility)"""
        pass

    async def cleanup(self):
        """Cleanup service resources (placeholder for compatibility)"""
        pass

    async def load_template(self, template_name: str) -> str:
        """
        Load template file asynchronously

        Performance: Non-blocking file I/O prevents event loop blocking

        Args:
            template_name: Name of template file

        Returns:
            Template content as string

        Raises:
            HTTPException: If template not found
        """
        template_path = self.template_dir / template_name

        if not template_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": f"Template {template_name} not found",
                    "hint": "Check template directory configuration"
                }
            )

        # Async file read - doesn't block event loop
        async with aiofiles.open(template_path, "r", encoding="utf-8") as f:
            content = await f.read()

        return content

    async def save_document(
        self,
        document_id: str,
        content: bytes,
        extension: str = "xlsx"
    ) -> Dict[str, Any]:
        """
        Save document asynchronously

        Performance: Non-blocking write operation

        Args:
            document_id: Unique document identifier
            content: Document content as bytes
            extension: File extension

        Returns:
            Document metadata
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        file_path = self.output_dir / f"{document_id}.{extension}"

        # Async file write
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Generate SHA256 hash for evidence
        content_hash = hashlib.sha256(content).hexdigest()

        return {
            "document_id": document_id,
            "file_path": str(file_path),
            "size": len(content),
            "hash": content_hash,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z"
        }

    async def fetch_metadata(self, url: str) -> Dict[str, Any]:
        """
        Fetch metadata from external service asynchronously

        Performance: Non-blocking HTTP request

        Args:
            url: External service URL

        Returns:
            Metadata dictionary

        Raises:
            HTTPException: If fetch fails
        """
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "METADATA_FETCH_FAILED",
                        "message": "Failed to fetch metadata",
                        "hint": str(e)
                    }
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail={
                        "code": "METADATA_HTTP_ERROR",
                        "message": f"HTTP {e.response.status_code} from metadata service",
                        "hint": e.response.text
                    }
                )

    async def batch_load_templates(
        self,
        template_names: List[str]
    ) -> Dict[str, str]:
        """
        Load multiple templates concurrently

        Performance: Parallel I/O operations

        Args:
            template_names: List of template names

        Returns:
            Dictionary of template name to content
        """
        import asyncio

        # Load all templates concurrently
        tasks = [
            self.load_template(name)
            for name in template_names
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        templates = {}
        for name, result in zip(template_names, results):
            if isinstance(result, Exception):
                # Log error but continue with other templates
                templates[name] = None
            else:
                templates[name] = result

        return templates

    async def generate_evidence_pack(
        self,
        quote_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate evidence pack with all required documents

        Performance: Concurrent generation of multiple documents

        Args:
            quote_id: Quote identifier
            data: Quote data for document generation

        Returns:
            Evidence pack metadata
        """
        import asyncio

        # Define evidence documents to generate
        documents = [
            ("input.json", json.dumps(data["input"], indent=2).encode()),
            ("output.json", json.dumps(data["output"], indent=2).encode()),
            ("metrics.json", json.dumps(data["metrics"], indent=2).encode()),
            ("validation.json", json.dumps(data["validation"], indent=2).encode()),
        ]

        # Save all documents concurrently
        save_tasks = [
            self.save_document(f"{quote_id}_{name}", content, "json")
            for name, content in documents
        ]

        results = await asyncio.gather(*save_tasks)

        # Generate pack metadata
        pack_hash = hashlib.sha256(
            "".join(r["hash"] for r in results).encode()
        ).hexdigest()

        return {
            "quote_id": quote_id,
            "documents": results,
            "pack_hash": pack_hash,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z"
        }

    async def cleanup_old_documents(
        self,
        days_to_keep: int = 30
    ) -> int:
        """
        Clean up old documents asynchronously

        Args:
            days_to_keep: Number of days to keep documents

        Returns:
            Number of files deleted
        """
        import asyncio
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0

        # List all files in output directory
        for file_path in self.output_dir.glob("*"):
            if file_path.is_file():
                # Check file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    # Delete old file asynchronously
                    await asyncio.to_thread(file_path.unlink)
                    deleted_count += 1

        return deleted_count

# Global service instance
document_service = DocumentService()