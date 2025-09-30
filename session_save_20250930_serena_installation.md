# Session Save: Serena MCP 설치 및 통합

**Date**: 2025-09-30
**Session Type**: Infrastructure Setup
**Duration**: ~10 minutes

## 완료된 작업

### 1. uv/uvx 패키지 매니저 설치
- **방법**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **위치**: `~/.local/bin/` (C:/Users/PC/.local/bin/)
- **버전**: uvx 0.8.22
- **목적**: Serena MCP 실행을 위한 Python 패키지 실행 도구

### 2. Serena MCP 서버 설치 및 설정
- **소스**: `git+https://github.com/oraios/serena`
- **설치 명령**: `claude mcp add serena`
- **전체 명령어**:
  ```bash
  C:/Users/PC/.local/bin/uvx.exe --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant --project c:/Users/PC/Desktop/kis-estimator-main
  ```
- **설정 파일**: `C:\Users\PC\.claude.json` (프로젝트 로컬)
- **연결 상태**: ✅ Connected

### 3. 설정 검증
- **확인 명령**: `claude mcp list`
- **결과**:
  - sequential-thinking: ✓ Connected
  - serena: ✓ Connected

## 주요 발견 사항

### Claude Desktop vs Claude Code
- **Claude Desktop**: `claude_desktop_config.json` 사용
- **Claude Code**: `.claude.json` 사용 (프로젝트별)
- **설치 명령**: `claude mcp add [name]` (Claude Code 전용)

### Serena MCP 특성
- **타입**: Python 기반 MCP 서버 (npm 아님)
- **실행 도구**: uvx (uv의 실행 도구)
- **프로젝트 연동**: `--project` 플래그로 프로젝트 경로 지정
- **컨텍스트**: `--context ide-assistant` (IDE 보조 모드)

### 사용 가능한 도구 (예상)
- `activate_project`: 프로젝트 활성화
- `list_memories`: 메모리 목록 조회
- `read_memory/write_memory`: 메모리 읽기/쓰기
- `delete_memory`: 메모리 삭제
- `think_about_*`: 컨텍스트 분석 도구들

## 기술 노트

### 설치 실패 원인 분석
1. **npm 패키지 탐색 실패**: Serena는 npm이 아닌 GitHub 저장소 기반
2. **Claude Desktop 설정 오인식**: Desktop용이 아닌 Code용 설정 필요
3. **경로 문제**: 상대 경로(`uvx`) vs 절대 경로(`C:/Users/PC/.local/bin/uvx.exe`)

### 최종 작동 설정
```json
{
  "serena": {
    "command": "C:/Users/PC/.local/bin/uvx.exe",
    "args": [
      "--from",
      "git+https://github.com/oraios/serena",
      "serena",
      "start-mcp-server",
      "--context",
      "ide-assistant",
      "--project",
      "c:/Users/PC/Desktop/kis-estimator-main"
    ]
  }
}
```

## 프로젝트 상태

### KIS Estimator 현황
- **Branch**: master
- **Latest Commit**: a3e29e1 - Performance optimization
- **Mode**: Contract-First + Evidence-Gated + SPEC KIT
- **Supabase**: 배포 완료
- **Git**: 업로드 완료
- **Critical Rule**: **목업(MOCKUP) 절대 금지**

### MCP 서버 현황
- ✅ sequential-thinking: 복잡한 추론 및 분석
- ✅ serena: 세션 메모리 관리 및 프로젝트 컨텍스트

## 다음 단계

### 즉시 가능
- `/sc:load` 실행 시 Serena MCP 통합된 프로젝트 로딩
- 메모리 기반 세션 관리 및 컨텍스트 보존
- 멀티 에이전트 구성 시 메모리 공유 활용

### 검증 필요
- Serena MCP 도구 실제 사용 가능 여부 확인
- 메모리 읽기/쓰기 기능 테스트
- 프로젝트 활성화 기능 검증

### 멀티 에이전트 구성 고려
- Agent 1: 개발 (현재 Claude + CLAUDE.md)
- Agent 2: 테스트/수정 (백엔드 QA)
- Serena 메모리로 컨텍스트 공유 가능

## 교훈

1. **문서 정확히 읽기**: MCP 서버마다 설치 방법 다름 (npm vs uvx)
2. **도구 구분**: Claude Desktop ≠ Claude Code
3. **경로 명확히**: Windows 환경에서 절대 경로 사용 권장
4. **연결 상태 확인**: `claude mcp list`로 항상 검증

---

*Session saved: 2025-09-30T12:55:00Z*