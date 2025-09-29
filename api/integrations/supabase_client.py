"""
Supabase Client Integration
Direct integration with Supabase for KIS Estimator
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from supabase import create_client, Client
import asyncpg

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Client for Supabase database operations"""

    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_ANON_KEY")
        self.service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.db_url = os.environ.get("SUPABASE_DB_URL")

        # Initialize Supabase client
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            logger.warning("Supabase credentials not found in environment")
            self.client = None

        self.db_conn = None

    async def connect(self):
        """Initialize database connection"""
        if self.db_url:
            try:
                self.db_conn = await asyncpg.connect(self.db_url)
                logger.info("Connected to Supabase database")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")

    async def disconnect(self):
        """Close database connection"""
        if self.db_conn:
            await self.db_conn.close()
            logger.info("Disconnected from Supabase database")

    # ==========================================
    # Catalog Operations
    # ==========================================

    async def get_catalog_items(
        self,
        kind: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch catalog items from database"""
        query = self.client.table("catalog_items").select("*")

        if kind:
            query = query.eq("kind", kind)

        query = query.limit(limit)

        response = query.execute()
        return response.data

    async def get_catalog_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get single catalog item by ID"""
        response = self.client.table("catalog_items").select("*").eq("id", item_id).execute()
        return response.data[0] if response.data else None

    # ==========================================
    # Quote Operations
    # ==========================================

    async def create_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new quote"""
        # Add timestamps
        quote_data["created_at"] = datetime.now(timezone.utc).isoformat()
        quote_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client.table("quotes").insert(quote_data).execute()

        if response.data:
            quote_id = response.data[0]["id"]

            # Log to audit
            await self.create_audit_log(
                actor="system",
                action="create_quote",
                target=f"quote:{quote_id}",
                trace_id=quote_data.get("trace_id")
            )

            return response.data[0]

        raise Exception("Failed to create quote")

    async def get_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
        """Get quote by ID with related data"""
        # Get quote
        quote_response = self.client.table("quotes").select("*").eq("id", quote_id).execute()

        if not quote_response.data:
            return None

        quote = quote_response.data[0]

        # Get related panels
        panels_response = self.client.table("panels").select("*").eq("quote_id", quote_id).execute()
        quote["panels"] = panels_response.data

        # Get breakers for each panel
        for panel in quote["panels"]:
            breakers_response = self.client.table("breakers").select("*").eq("panel_id", panel["id"]).execute()
            panel["breakers"] = breakers_response.data

        # Get quote items
        items_response = self.client.table("quote_items").select("*").eq("quote_id", quote_id).execute()
        quote["items"] = items_response.data

        return quote

    async def update_quote(
        self,
        quote_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing quote"""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client.table("quotes").update(updates).eq("id", quote_id).execute()

        if response.data:
            await self.create_audit_log(
                actor="system",
                action="update_quote",
                target=f"quote:{quote_id}",
                trace_id=updates.get("trace_id")
            )

            return response.data[0]

        raise Exception(f"Failed to update quote {quote_id}")

    async def list_quotes(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List quotes with filters"""
        query = self.client.table("quotes").select("*")

        if customer_id:
            query = query.eq("customer_id", customer_id)

        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        response = query.execute()
        return response.data

    # ==========================================
    # Panel & Breaker Operations
    # ==========================================

    async def create_panel(
        self,
        quote_id: str,
        panel_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a panel for a quote"""
        panel_data["quote_id"] = quote_id
        panel_data["created_at"] = datetime.now(timezone.utc).isoformat()
        panel_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client.table("panels").insert(panel_data).execute()
        return response.data[0] if response.data else None

    async def create_breaker(
        self,
        panel_id: str,
        breaker_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add breaker to a panel"""
        breaker_data["panel_id"] = panel_id
        breaker_data["created_at"] = datetime.now(timezone.utc).isoformat()
        breaker_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client.table("breakers").insert(breaker_data).execute()
        return response.data[0] if response.data else None

    async def bulk_create_breakers(
        self,
        panel_id: str,
        breakers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Bulk create breakers for a panel"""
        timestamp = datetime.now(timezone.utc).isoformat()

        for breaker in breakers:
            breaker["panel_id"] = panel_id
            breaker["created_at"] = timestamp
            breaker["updated_at"] = timestamp

        response = self.client.table("breakers").insert(breakers).execute()
        return response.data

    # ==========================================
    # Document Operations
    # ==========================================

    async def create_document(
        self,
        quote_id: str,
        kind: str,
        path: str,
        sha256: str
    ) -> Dict[str, Any]:
        """Store document reference"""
        doc_data = {
            "quote_id": quote_id,
            "kind": kind,
            "path": path,
            "sha256": sha256,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.table("documents").insert(doc_data).execute()
        return response.data[0] if response.data else None

    async def get_document(
        self,
        quote_id: str,
        kind: str
    ) -> Optional[Dict[str, Any]]:
        """Get document by quote and kind"""
        response = self.client.table("documents").select("*").eq("quote_id", quote_id).eq("kind", kind).execute()
        return response.data[0] if response.data else None

    # ==========================================
    # Evidence Operations
    # ==========================================

    async def create_evidence(
        self,
        quote_id: str,
        stage: str,
        path: str,
        sha256: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store evidence blob"""
        evidence_data = {
            "quote_id": quote_id,
            "stage": stage,
            "path": path,
            "sha256": sha256,
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.table("evidence_blobs").insert(evidence_data).execute()
        return response.data[0] if response.data else None

    async def get_evidence(
        self,
        quote_id: str,
        stage: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get evidence for a quote"""
        query = self.client.table("evidence_blobs").select("*").eq("quote_id", quote_id)

        if stage:
            query = query.eq("stage", stage)

        query = query.order("created_at", desc=True)

        response = query.execute()
        return response.data

    # ==========================================
    # Customer Operations
    # ==========================================

    async def create_customer(
        self,
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new customer"""
        customer_data["created_at"] = datetime.now(timezone.utc).isoformat()
        customer_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client.table("customers").insert(customer_data).execute()
        return response.data[0] if response.data else None

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        response = self.client.table("customers").select("*").eq("id", customer_id).execute()
        return response.data[0] if response.data else None

    # ==========================================
    # Audit Operations
    # ==========================================

    async def create_audit_log(
        self,
        actor: str,
        action: str,
        target: str,
        trace_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create audit log entry"""
        import uuid

        audit_data = {
            "actor": actor,
            "action": action,
            "target": target,
            "trace_id": trace_id or str(uuid.uuid4()),
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.table("audit_logs").insert(audit_data).execute()
        return response.data[0] if response.data else None

    # ==========================================
    # View Operations
    # ==========================================

    async def get_quote_summary(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get quote summary from view"""
        response = self.client.from_("quote_summary").select("*").limit(limit).execute()
        return response.data

    async def get_phase_balance(
        self,
        panel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get phase balance analysis for a panel"""
        response = self.client.from_("phase_balance").select("*").eq("panel_id", panel_id).execute()
        return response.data[0] if response.data else None

    # ==========================================
    # Transaction Operations (using direct connection)
    # ==========================================

    async def execute_transaction(
        self,
        queries: List[tuple]
    ) -> List[Any]:
        """Execute multiple queries in a transaction"""
        if not self.db_conn:
            raise Exception("Database connection not initialized")

        async with self.db_conn.transaction():
            results = []
            for query, params in queries:
                result = await self.db_conn.fetch(query, *params)
                results.append(result)

            return results

    # ==========================================
    # Real-time Subscriptions
    # ==========================================

    def subscribe_to_quotes(self, callback):
        """Subscribe to real-time quote updates"""
        if self.client:
            channel = self.client.channel("quotes-changes")
            channel.on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": "quotes"
                },
                callback
            ).subscribe()

            return channel

        logger.warning("Cannot subscribe - Supabase client not initialized")
        return None

# Singleton instance
supabase_client = SupabaseClient()