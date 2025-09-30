# GitHub Private 저장소 설정 가이드

## 1. GitHub에서 Private 저장소 생성

1. GitHub.com에 로그인
2. 우측 상단 '+' 클릭 → 'New repository' 선택
3. 다음 설정으로 생성:
   - Repository name: `kis-estimator`
   - Description: "KIS Estimator - 전기 패널 견적 시스템"
   - **🔒 Private 선택** (중요!)
   - Initialize repository 체크 해제 (이미 로컬에 코드가 있으므로)
   - 'Create repository' 클릭

## 2. 로컬에서 원격 저장소 연결 및 푸시

GitHub에서 저장소 생성 후 나타나는 URL을 복사하여 아래 명령어 실행:

```bash
# 1. 기존 placeholder remote 제거
git remote remove origin

# 2. 실제 private 저장소 연결 (YOUR_USERNAME을 실제 GitHub 사용자명으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/kis-estimator.git

# 또는 SSH 사용 시:
git remote add origin git@github.com:YOUR_USERNAME/kis-estimator.git

# 3. 모든 파일 푸시
git push -u origin main
```

## 3. GitHub 인증

푸시할 때 인증이 필요합니다:

### HTTPS 방식:
- Username: GitHub 사용자명
- Password: GitHub Personal Access Token (비밀번호 아님!)
  - Settings → Developer settings → Personal access tokens → Generate new token
  - repo 권한 체크 필요

### SSH 방식:
- SSH 키가 GitHub에 등록되어 있어야 함
- Settings → SSH and GPG keys → New SSH key

## 4. 푸시 완료 확인

```bash
# 푸시 상태 확인
git status

# 원격 저장소 확인
git remote -v

# 로그 확인
git log --oneline
```

## 5. 집에서 작업하기

집에서 clone하여 작업 시작:

```bash
# Private 저장소 clone
git clone https://github.com/YOUR_USERNAME/kis-estimator.git
cd kis-estimator

# npm 패키지 설치
npm install

# Python 패키지 설치
pip install -r requirements.txt

# 개발 서버 실행
npm run dev
```

## ⚠️ 보안 주의사항

현재 코드에 민감한 정보가 포함되어 있습니다:
- 데이터베이스 비밀번호: `@dnjsdl2572`
- Supabase 키들

**Private 저장소라도** 보안을 위해 추후 다음 작업 필요:
1. 비밀번호 변경
2. .env 파일 사용
3. 환경 변수로 관리

## 현재 커밋 상태

```
0ad24c2 feat: Initial KIS Estimator project with Supabase integration
b9c3d4f feat: Include all project files for complete deployment
```

두 커밋이 준비되어 있고, private 저장소만 만들면 바로 푸시 가능합니다!