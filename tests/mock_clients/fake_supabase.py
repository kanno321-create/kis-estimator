"""Fake Supabase Client for Testing"""
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import jwt

class FakeSupabaseStorage:
    """Mock Supabase Storage Service"""
    def __init__(self):
        self.buckets = {}
        self.files = {}

    def create_bucket(self, name: str) -> Dict[str, Any]:
        self.buckets[name] = {"name": name, "created_at": datetime.utcnow().isoformat()}
        return {"data": self.buckets[name]}

    def upload(self, bucket: str, path: str, file_data: bytes) -> Dict[str, Any]:
        key = f"{bucket}/{path}"
        self.files[key] = {
            "data": file_data,
            "size": len(file_data),
            "hash": hashlib.sha256(file_data).hexdigest(),
            "created_at": datetime.utcnow().isoformat()
        }
        return {"data": {"path": path, "size": len(file_data)}}

    def download(self, bucket: str, path: str) -> bytes:
        key = f"{bucket}/{path}"
        return self.files.get(key, {}).get("data", b"")

class FakeSupabaseDB:
    """Mock Supabase Database Service"""
    def __init__(self):
        self.tables = {
            "quotes": [],
            "quote_items": [],
            "panels": [],
            "evidence_blobs": []
        }
        self.query_count = 0

    def from_table(self, table_name: str):
        self.current_table = table_name
        self.query_count += 1
        return self

    def select(self, *columns):
        return self

    def insert(self, data: Dict[str, Any]):
        if self.current_table in self.tables:
            data["id"] = len(self.tables[self.current_table]) + 1
            data["created_at"] = datetime.utcnow().isoformat()
            self.tables[self.current_table].append(data)
        return {"data": data}

    def eq(self, column: str, value: Any):
        result = [
            row for row in self.tables.get(self.current_table, [])
            if row.get(column) == value
        ]
        return {"data": result}

    def execute(self):
        return {"data": self.tables.get(self.current_table, [])}

    def reset_query_count(self):
        count = self.query_count
        self.query_count = 0
        return count

class FakeSupabaseAuth:
    """Mock Supabase Auth Service"""
    def __init__(self, secret: str):
        self.secret = secret
        self.users = {}

    def create_user(self, email: str, password: str) -> Dict[str, Any]:
        user_id = hashlib.md5(email.encode()).hexdigest()
        self.users[user_id] = {
            "id": user_id,
            "email": email,
            "created_at": datetime.utcnow().isoformat()
        }
        return {"data": {"user": self.users[user_id]}}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        user_id = hashlib.md5(email.encode()).hexdigest()
        if user_id in self.users:
            token = self.generate_token(user_id)
            return {
                "data": {
                    "user": self.users[user_id],
                    "session": {
                        "access_token": token,
                        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
                    }
                }
            }
        return {"error": "Invalid credentials"}

    def generate_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "role": "authenticated"
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"], audience="authenticated")
            return payload
        except jwt.InvalidTokenError:
            return None

class FakeSupabase:
    """Complete Fake Supabase Client"""
    def __init__(self, url: str, key: str, secret: str):
        self.url = url
        self.key = key
        self.storage = FakeSupabaseStorage()
        self.db = FakeSupabaseDB()
        self.auth = FakeSupabaseAuth(secret)

    def from_table(self, table: str):
        return self.db.from_table(table)

    def storage_upload(self, bucket: str, path: str, data: bytes):
        return self.storage.upload(bucket, path, data)

    def storage_download(self, bucket: str, path: str):
        return self.storage.download(bucket, path)

    def auth_sign_in(self, email: str, password: str):
        return self.auth.sign_in(email, password)

    def auth_verify(self, token: str):
        return self.auth.verify_token(token)