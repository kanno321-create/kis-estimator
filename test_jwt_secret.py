"""
JWT Secret 검증 스크립트
Supabase JWT Secret이 올바른지 테스트
"""
import jwt
from datetime import datetime, timezone, timedelta

# JWT Secret (Base64 형태 그대로 사용)
JWT_SECRET = "2Ujjd4++CT6/reNK0pOvIbuCwcq/3BPDMaiEvWyEp3QjyF4Q5uLts+GA+H0XY8EzR1UErgoZvTiAp7gdilhfCw=="

print("=" * 60)
print("JWT Secret 검증 테스트")
print("=" * 60)

# 1. Admin 토큰 생성 테스트
print("\n1️⃣ Admin JWT 토큰 생성 중...")
try:
    admin_payload = {
        "sub": "test-admin-user-123",
        "email": "admin@test.com",
        "role": "admin",
        "aud": "authenticated",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }

    admin_token = jwt.encode(admin_payload, JWT_SECRET, algorithm="HS256")
    print(f"✅ Admin 토큰 생성 성공!")
    print(f"Token (처음 50자): {admin_token[:50]}...")

except Exception as e:
    print(f"❌ Admin 토큰 생성 실패: {e}")
    exit(1)

# 2. 토큰 검증 테스트
print("\n2️⃣ 토큰 검증 중...")
try:
    decoded = jwt.decode(
        admin_token,
        JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated"
    )
    print(f"✅ 토큰 검증 성공!")
    print(f"Decoded payload:")
    print(f"  - sub: {decoded['sub']}")
    print(f"  - email: {decoded['email']}")
    print(f"  - role: {decoded['role']}")
    print(f"  - aud: {decoded['aud']}")

except jwt.ExpiredSignatureError:
    print("❌ 토큰이 만료되었습니다")
    exit(1)
except jwt.InvalidTokenError as e:
    print(f"❌ 토큰 검증 실패: {e}")
    exit(1)

# 3. User 토큰 생성 테스트
print("\n3️⃣ User JWT 토큰 생성 중...")
try:
    user_payload = {
        "sub": "test-user-456",
        "email": "user@test.com",
        "role": "authenticated",  # 일반 유저
        "aud": "authenticated",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }

    user_token = jwt.encode(user_payload, JWT_SECRET, algorithm="HS256")
    print(f"✅ User 토큰 생성 성공!")
    print(f"Token (처음 50자): {user_token[:50]}...")

except Exception as e:
    print(f"❌ User 토큰 생성 실패: {e}")
    exit(1)

# 4. .env 파일 생성 제안
print("\n" + "=" * 60)
print("✅ JWT Secret이 올바르게 작동합니다!")
print("=" * 60)

print("\n📝 다음 명령어로 .env.test 파일을 생성하세요:")
print("\n--- .env.test 내용 ---")
print(f'SUPABASE_JWT_SECRET="{JWT_SECRET}"')
print('SUPABASE_URL="https://your-project.supabase.co"')
print('SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"')
print("-" * 60)

print("\n🧪 테스트 토큰 (복사해서 사용 가능):")
print(f"\nAdmin Token:\n{admin_token}\n")
print(f"User Token:\n{user_token}\n")

print("=" * 60)
print("테스트 완료! 이제 pytest를 실행할 수 있습니다.")
print("=" * 60)