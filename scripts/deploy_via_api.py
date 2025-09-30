#!/usr/bin/env python3
"""
Supabase Schema Deployment via REST API
Uses Supabase service role key to execute SQL through API
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone

# Supabase configuration
SUPABASE_URL = "https://cgqukhmqnndwdbmkmjrn.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNncXVraG1xbm5kd2RibWttanJuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTIwNTkyMSwiZXhwIjoyMDc0NzgxOTIxfQ.-olqMJ5sx_LofEGqlePOMK0MnFJT-LLg3_ll0IR3yj4"

def log(msg: str):
    """Log with timestamp"""
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] {msg}")

def execute_sql(sql: str, description: str):
    """Execute SQL via Supabase REST API"""
    log(f"Executing: {description}")
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/query"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": sql
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code in [200, 201, 204]:
            log(f"✅ {description} - SUCCESS")
            return True
        else:
            log(f"❌ {description} - FAILED")
            log(f"   Status: {response.status_code}")
            log(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        log(f"❌ {description} - ERROR: {e}")
        return False

def check_table_exists(table_name: str, schema: str = "public"):
    """Check if table exists via API"""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?limit=0"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

def main():
    """Main deployment function"""
    log("="*60)
    log("KIS Estimator API-Based Deployment")
    log("="*60)
    log(f"Target: {SUPABASE_URL}")
    
    # Read SQL files
    try:
        with open("/workspace/db/schema.sql", "r") as f:
            schema_sql = f.read()
        with open("/workspace/db/functions.sql", "r") as f:
            functions_sql = f.read()
        with open("/workspace/db/policies.sql", "r") as f:
            policies_sql = f.read()
            
        log("✅ SQL files loaded successfully")
        
    except Exception as e:
        log(f"❌ Failed to read SQL files: {e}")
        return 1
    
    # Execute deployments
    log("\n" + "="*60)
    log("DEPLOYMENT STEPS")
    log("="*60)
    
    # Step 1: Schema
    if not execute_sql(schema_sql, "Database Schema"):
        log("⚠️  Schema deployment failed, continuing...")
    
    # Step 2: Functions
    if not execute_sql(functions_sql, "Database Functions"):
        log("⚠️  Functions deployment failed, continuing...")
    
    # Step 3: Policies
    if not execute_sql(policies_sql, "Security Policies"):
        log("⚠️  Policies deployment failed, continuing...")
    
    # Verification
    log("\n" + "="*60)
    log("VERIFICATION")
    log("="*60)
    
    # Check if quotes table exists
    if check_table_exists("quotes"):
        log("✅ quotes table exists")
    else:
        log("❌ quotes table not found")
    
    log("\n" + "="*60)
    log("DEPLOYMENT COMPLETED")
    log("="*60)
    log("\nNote: Some operations may have failed due to API limitations.")
    log("For complete deployment, use psql or Supabase CLI.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
