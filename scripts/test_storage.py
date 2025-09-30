#!/usr/bin/env python3
"""
Supabase Storage 테스트 스크립트
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from supabase import create_client

# Supabase 설정
SUPABASE_URL = "https://cgqukhmqnndwdbmkmjrn.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNncXVraG1xbm5kd2RibWttanJuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTIwNTkyMSwiZXhwIjoyMDc0NzgxOTIxfQ.-olqMJ5sx_LofEGqlePOMK0MnFJT-LLg3_ll0IR3yj4"

def log(msg: str):
    """로그 출력"""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")

def main():
    log("="*60)
    log("Supabase Storage 테스트")
    log("="*60)

    # Supabase 클라이언트 생성
    try:
        supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
        log("✅ Supabase 클라이언트 생성 성공")
    except Exception as e:
        log(f"❌ 클라이언트 생성 실패: {e}")
        return 1

    # 1. Bucket 목록 조회
    try:
        log("\n1. Storage Bucket 목록 조회...")
        buckets = supabase.storage.list_buckets()
        log(f"✅ Bucket 개수: {len(buckets)}")

        bucket_names = []
        for bucket in buckets:
            # Handle both dict and object responses
            if hasattr(bucket, 'name'):
                bucket_name = bucket.name
                is_public = getattr(bucket, 'public', False)
            else:
                bucket_name = bucket.get('name', 'unknown')
                is_public = bucket.get('public', False)

            bucket_names.append(bucket_name)
            log(f"   - {bucket_name} (public: {is_public})")

        # evidence 버킷 확인
        evidence_exists = 'evidence' in bucket_names
        if evidence_exists:
            log("✅ 'evidence' 버킷 존재 확인")
        else:
            log("⚠️  'evidence' 버킷이 없습니다. Storage 메뉴에서 생성하세요.")
            log("   Name: evidence")
            log("   Public: OFF")
            return 1

    except Exception as e:
        log(f"❌ Bucket 목록 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 2. 테스트 파일 업로드
    try:
        log("\n2. 테스트 파일 업로드...")

        # 테스트 데이터 생성
        test_data = {
            "stage": "enclosure",
            "quote_id": "test-quote-001",
            "fit_score": 0.95,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        test_content = json.dumps(test_data, indent=2).encode('utf-8')
        test_hash = hashlib.sha256(test_content).hexdigest()

        # 업로드 경로
        test_path = f"test/quote-001/enclosure/{test_hash}.json"

        # 파일 업로드
        result = supabase.storage.from_("evidence").upload(
            path=test_path,
            file=test_content,
            file_options={"content-type": "application/json"}
        )

        log(f"✅ 파일 업로드 성공: {test_path}")
        log(f"   SHA256: {test_hash}")

    except Exception as e:
        log(f"❌ 파일 업로드 실패: {e}")
        log(f"   에러 타입: {type(e).__name__}")
        return 1

    # 3. 파일 목록 조회
    try:
        log("\n3. 업로드된 파일 확인...")

        files = supabase.storage.from_("evidence").list("test/quote-001/enclosure/")
        log(f"✅ 파일 개수: {len(files)}")
        for file in files:
            log(f"   - {file['name']} ({file.get('metadata', {}).get('size', 0)} bytes)")

    except Exception as e:
        log(f"❌ 파일 목록 조회 실패: {e}")
        return 1

    # 4. Signed URL 생성
    try:
        log("\n4. Signed URL 생성 (300초 TTL)...")

        signed_url = supabase.storage.from_("evidence").create_signed_url(
            path=test_path,
            expires_in=300  # 5분
        )

        log(f"✅ Signed URL 생성 성공")
        log(f"   URL: {signed_url['signedURL'][:80]}...")

    except Exception as e:
        log(f"❌ Signed URL 생성 실패: {e}")
        return 1

    # 5. 파일 삭제 (정리)
    try:
        log("\n5. 테스트 파일 삭제...")

        supabase.storage.from_("evidence").remove([test_path])
        log(f"✅ 테스트 파일 삭제 완료")

    except Exception as e:
        log(f"⚠️  파일 삭제 실패 (무시 가능): {e}")

    # 최종 결과
    log("\n" + "="*60)
    log("✅ Storage 테스트 완료")
    log("="*60)
    log("\n다음 단계:")
    log("1. API 서버 시작: uvicorn api.main:app --reload")
    log("2. Health check: curl http://localhost:8000/healthz")
    log("3. Readiness check: curl http://localhost:8000/readyz")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())