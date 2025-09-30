# 🚨 긴급: GitHub에 바로 업로드하기

## 방법 1: GitHub 웹사이트에서 직접 (5분 소요)

1. **GitHub.com 접속** → 로그인
2. 우측 상단 **'+'** 클릭 → **'New repository'**
3. 설정:
   - Repository name: `kis-estimator`
   - **🔒 Private 선택** (필수!)
   - ❌ "Initialize this repository" 체크 해제
   - **Create repository** 클릭

4. 생성 후 나오는 화면에서 **"...or push an existing repository"** 섹션의 명령어 복사

5. 터미널에서 실행:
```bash
# GitHub에서 복사한 명령어 (예시)
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/kis-estimator.git
git branch -M main
git push -u origin main
```

## 방법 2: Personal Access Token으로 바로 푸시 (이미 토큰이 있다면)

```bash
# 1. Remote 설정 (YOUR_USERNAME을 실제 GitHub 사용자명으로 변경)
git remote set-url origin https://github.com/YOUR_USERNAME/kis-estimator.git

# 2. 푸시 (Username과 Password 입력)
git push -u origin main
# Username: YOUR_GITHUB_USERNAME
# Password: YOUR_PERSONAL_ACCESS_TOKEN (비밀번호 아님!)
```

## 🔑 Personal Access Token 빠르게 만들기

1. GitHub.com → Settings (프로필 클릭)
2. 맨 아래 **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token** → **Generate new token (classic)**
5. 설정:
   - Note: `kis-estimator-upload`
   - Expiration: 30 days
   - ✅ **repo** 체크 (전체)
6. **Generate token** → 토큰 복사 (한 번만 보임!)

## 📥 집에서 다운받기

푸시 완료 후 집에서:
```bash
# Private 저장소 clone
git clone https://github.com/YOUR_USERNAME/kis-estimator.git
cd kis-estimator

# 의존성 설치
npm install
pip install -r requirements.txt

# 개발 서버 실행
npm run dev
```

## ⚠️ 현재 커밋 상태
```
aa0194c docs: GitHub private repository setup guide
b9c3d4f feat: Include all project files for complete deployment
0ad24c2 feat: Initial KIS Estimator project with Supabase integration
```

3개 커밋 모두 준비 완료! GitHub 저장소만 만들면 바로 푸시 가능!