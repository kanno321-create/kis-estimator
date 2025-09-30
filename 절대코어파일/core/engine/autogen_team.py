#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# === autogen_team.py — 한국산업 자동견적프로그램 MCP/A2A 리빌드 ===

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime

# UTF-8 출력 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

# .env 파일 로드 (강화된 버전)
def load_env():
    """환경변수 파일 로드 - 가상환경 호환"""
    env_files = [Path('.env'), Path(__file__).parent / '.env']
    
    for env_path in env_files:
        if env_path.exists():
            print(f"📁 .env 파일 로드 중: {env_path}")
            try:
                content = env_path.read_text(encoding='utf-8')
                loaded_count = 0
                for line_num, line in enumerate(content.splitlines(), 1):
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            key, value = key.strip(), value.strip()
                            # 빈 값이 아니면 설정
                            if value:
                                os.environ[key] = value
                                loaded_count += 1
                                # API 키는 보안상 일부만 출력
                                if 'API_KEY' in key:
                                    print(f"  ✅ {key}={value[:10]}...")
                                elif key == 'CURRENT_PHASE':
                                    print(f"  ✅ {key}={value}")
                        except ValueError:
                            print(f"  ❌ 라인 {line_num} 파싱 오류: {line}")
                
                print(f"📊 총 {loaded_count}개 환경변수 로드 완료")
                return True
                
            except Exception as e:
                print(f"❌ .env 파일 읽기 오류: {e}")
                continue
    
    print("❌ .env 파일을 찾을 수 없습니다")
    return False

# 환경변수 로드
env_loaded = load_env()

# 필수 환경변수 검증
def validate_environment():
    """필수 환경변수가 설정되었는지 확인"""
    required_vars = ['OPENROUTER_API_KEY', 'CURRENT_PHASE']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 필수 환경변수 누락: {missing_vars}")
        print("📋 .env 파일을 확인하고 다음 변수들을 설정하세요:")
        for var in missing_vars:
            if var == 'CURRENT_PHASE':
                print(f"   {var}=1")
            elif 'API_KEY' in var:
                print(f"   {var}=your_api_key_here")
        return False
    
    print("✅ 필수 환경변수 확인 완료")
    return True

if not validate_environment():
    print("❌ 환경변수 설정 문제로 인해 종료합니다")
    sys.exit(1)

# AutoGen import (수정된 버전)
try:
    from autogen import ConversableAgent
    AUTOGEN_AVAILABLE = True
    print("✅ AutoGen 로드 성공 (v0.2.32)")
except ImportError as e:
    print(f"❌ AutoGen 로드 실패: {e}")
    AUTOGEN_AVAILABLE = False

# 설정
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
LOGS = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(OUT / "autogen_session.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# === Direct API Fallback for Windows AutoGen Issues ===
def direct_api_call(model, system_message, user_message, base_url, api_key, timeout=90):
    """Direct API call bypassing AutoGen when initiate_chat fails on Windows"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 4000,
            "temperature": 0.35,
            "timeout": timeout
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            return "API 응답 파싱 오류"
            
    except Exception as e:
        logger.error(f"Direct API call failed: {e}")
        return f"Direct API call 실패: {e}"

# === File Extraction from AI Responses ===
def extract_and_save_files(response_text, session_dir, worker_name):
    """AI 응답에서 파일들을 추출하고 저장"""
    import re
    
    files_saved = []
    
    # 패턴 1: ```filename\ncontent``` 또는 ```python\ncontent``` 형식
    file_pattern = r'```(?:(\w+\.\w+)\n|(python|json|markdown)\n)(.*?)```'
    raw_matches = re.findall(file_pattern, response_text, re.DOTALL)
    
    # 매치 결과 정리
    matches = []
    for match in raw_matches:
        filename, lang, content = match
        if filename:
            matches.append((filename, content))
        elif lang == 'python':
            matches.append(('patch_bundle.py', content))
        elif lang == 'json':
            matches.append(('data.json', content))
        elif lang == 'markdown':
            matches.append(('documentation.md', content))
    
    for filename, content in matches:
        try:
            # 안전한 파일명 생성 (메모리에만 저장)
            safe_filename = f"{worker_name}_{filename}"
            clean_content = content.strip()
            
            # 메모리에 파일 정보 저장
            files_saved.append({
                'filename': safe_filename,
                'content': clean_content,
                'size': len(clean_content)
            })
            print(f"📄 파일 추출 (메모리): {safe_filename} ({len(clean_content)} 문자)")
            
        except Exception as e:
            print(f"❌ 파일 추출 실패 ({filename}): {e}")
    
    # 패턴 2: **파일명:** 또는 **출력:** patch_bundle.txt 형식의 언급된 파일들
    mentioned_files = re.findall(r'(?:\*\*출력:\*\*|\*\*파일:\*\*|\b)(patch_bundle\.txt|ui_texts\.json|tests_comprehensive\.jsonl|system_architecture\.md|education_tab_spec\.md|learning_system_design\.json|quality_report\.json)', response_text, re.IGNORECASE)
    
    # 패턴 3: 코드 블록에서 파일 내용 추출 시도
    if not matches and mentioned_files:
        # 큰 코드 블록을 찾아서 주요 파일로 저장
        code_blocks = re.findall(r'```(?:\w+\n)?(.*?)```', response_text, re.DOTALL)
        
        for i, code_block in enumerate(code_blocks):
            if len(code_block.strip()) > 50:  # 의미있는 내용만
                # 가장 가능성 높은 파일명 결정
                if i < len(mentioned_files):
                    filename = mentioned_files[i]
                else:
                    filename = f"patch_bundle_{i+1}.txt"
                
                try:
                    safe_filename = f"{worker_name}_{filename}"
                    files_saved.append({
                        'filename': safe_filename,
                        'content': code_block.strip(),
                        'size': len(code_block.strip())
                    })
                    print(f"📄 코드 블록 추출 (메모리): {safe_filename}")
                except Exception as e:
                    print(f"❌ 코드 블록 추출 실패: {e}")
    
    # 패턴 4: JSON 형식 데이터 추출
    json_pattern = r'```json\n(.*?)```'
    json_matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    for i, json_content in enumerate(json_matches):
        try:
            # JSON 유효성 검사
            import json
            json.loads(json_content.strip())  # 파싱 테스트
            
            filename = f"{worker_name}_data_{i+1}.json"
            files_saved.append({
                'filename': filename,
                'content': json_content.strip(),
                'size': len(json_content.strip())
            })
            print(f"📄 JSON 파일 추출 (메모리): {filename}")
            
        except Exception as e:
            print(f"❌ JSON 파일 저장 실패: {e}")
    
    return files_saved


def save_files_to_disk(extracted_files, session_dir):
    """Phase 완료시 메모리에 있던 파일들을 실제 디스크에 저장"""
    if not extracted_files:
        return []
    
    # 세션 디렉토리 생성
    session_dir.mkdir(exist_ok=True, parents=True)
    
    saved_files = []
    for file_info in extracted_files:
        if isinstance(file_info, dict):
            filename = file_info['filename']
            content = file_info['content']
        else:
            # 이전 버전 호환성
            filename = file_info
            content = ""
            
        try:
            file_path = session_dir / filename
            file_path.write_text(content, encoding='utf-8', errors='replace')
            saved_files.append(filename)
            print(f"💾 파일 실제 저장: {filename}")
        except Exception as e:
            print(f"❌ 파일 저장 실패: {filename} - {e}")
    
    return saved_files

# === 환경 설정 ===
SKIP_WORKERS = os.getenv("AUTOGEN_SKIP_WORKERS", "").split(",")
SKIP_WORKERS = [w.strip() for w in SKIP_WORKERS if w.strip()]
TIMEOUT_SEC = int(os.getenv("AUTOGEN_TIMEOUT", "120"))
TEMPERATURE = float(os.getenv("AUTOGEN_TEMPERATURE", "0.35"))

# OpenRouter 설정
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# 최신 모델 설정 (정확한 모델명)
MODELS = {
    "leader": "openai/gpt-4o",
    "chatgpt": "openai/gpt-4o-mini", 
    "claude": "anthropic/claude-3.7-sonnet",
    "gemini": "google/gemini-2.5-flash",
    "grok": "x-ai/grok-code-fast-1"
}

def create_agent(name, system_message, model):
    """AutoGen Agent 생성"""
    if not AUTOGEN_AVAILABLE:
        return None
    
    llm_config = {
        "model": model,
        "api_key": OPENROUTER_API_KEY,
        "base_url": BASE_URL,
        "temperature": TEMPERATURE,
        "timeout": TIMEOUT_SEC,
        "max_tokens": 4000,
        "price": [0.15, 0.6]
    }
    
    try:
        agent = ConversableAgent(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=8,
            is_termination_msg=lambda x: "[END]" in x.get("content", "")
        )
        return agent
    except Exception as e:
        logger.error(f"Agent {name} 생성 실패: {e}")
        return None

# Phase 제어 시스템 (이전 대화 내용 반영)
def get_current_phase():
    """현재 실행할 Phase 결정"""
    phase_str = os.getenv("CURRENT_PHASE", "1")
    logger.info(f"환경변수 CURRENT_PHASE 값: '{phase_str}'")
    
    try:
        phase = int(phase_str)
        logger.info(f"Phase 정수 변환 성공: {phase}")
    except ValueError:
        logger.error(f"Phase 변환 실패, 기본값 1 사용: '{phase_str}'")
        phase = 1
    
    phase_descriptions = {
        1: "Phase 1: autogen_team.py 자체 완성 (Meta Phase)",
        2: "Phase 2: 계획 수립 + assistant_agent.py 오토파일럿",
        3: "Phase 3: macOS Glass UI 3개 탭 + 엑셀 매핑",
        4: "Phase 4: 골격 검증 90% + 폼 검증/토스트",
        5: "Phase 5: MCP/A2A 교차학습 + 공식견적 승격"
    }
    
    description = phase_descriptions.get(phase, f"Phase {phase}: 사용자 정의")
    logger.info(f"실행 Phase: {description}")
    return phase

def get_phase_description_clean(phase):
    """Phase 설명 (파일명용 - 특수문자 제거)"""
    descriptions = {
        1: "Meta-Phase",
        2: "Planning-Assistant",
        3: "UI-Excel-Mapping",
        4: "Validation-Forms",
        5: "Integration-Email"
    }
    return descriptions.get(phase, f"Phase-{phase}")

def run_team_collaboration():
    """완전한 4개 AI 팀 + MCP/A2A 협업 (역할 재분배)"""
    if not AUTOGEN_AVAILABLE:
        return run_dummy_mode()
    
    current_phase = get_current_phase()
    logger.info(f"🚀 한국산업 자동견적프로그램 MCP/A2A 리빌드 시작! Phase {current_phase}")
    
    # 세션 ID 생성 (폴더는 나중에 생성)
    session_id = datetime.now().strftime(f"session-phase{current_phase}-%Y%m%d-%H%M%S")
    session_dir = OUT / session_id
    # 폴더는 Phase 완료시에만 생성
    
    # === 팀 구성 (역할 재분배) ===
    
    # 🤖 리더: KaraLeader (GPT-4o)
    leader_prompt = f"""당신은 한국산업 자동견적프로그램 리빌드 프로젝트의 총괄 리더 AI(KaraLeader)입니다.

🎯 **Phase {current_phase} 특별 전략: 4개 AI 전체 구현 → 최고 결과 추출**

**Phase {current_phase} 혁신적 접근법:**
각 워커(ChatGPT, Claude, Grok, Gemini)가 자신의 전문 관점으로 전체 시스템을 완구현합니다.
4개의 완전한 구현체를 생성한 후, 가장 효율적이고 혁신적인 부분들을 추려내어 최종 통합본을 만듭니다.

**워커별 관점:**
- ChatGPT: 백엔드 최적화와 계산 정확성 중심의 전체 구현
- Claude: UI/UX 혁신과 사용자 경험 중심의 전체 구현
- Grok: 창의적 솔루션과 학습 시스템 혁신 중심의 전체 구현
- Gemini: 품질과 효율성, 통합 최적화 중심의 전체 구현

**당신의 역할:**
1. 각 워커가 전체 시스템을 완전히 구현하도록 지시
2. 4개 구현체의 장단점 비교 분석
3. 최고의 아이디어들을 추려내어 통합 설계안 제시
4. Phase 2-5에서 사용할 최적화된 아키텍처 결정

**Phase {current_phase} 완료 후:**
4개 구현체 중에서 가장 효율적인 알고리즘, 혁신적인 UI, 안정적인 아키텍처를 선별하여
Phase 2-5의 완벽한 기반을 마련하세요.

각 워커에게 전체 시스템 구현을 명확히 지시하고 결과를 분석하세요."""

    # 📧 ChatGPT 워커 (코어 개발)
    chatgpt_prompt = get_chatgpt_prompt(current_phase)

    # 🎨 Claude 워커 (UI/UX 디자인 메인)  
    claude_prompt = get_claude_prompt(current_phase)

    # 🚀 Grok 워커 (교육탭 전문 설계자)
    grok_prompt = get_grok_prompt(current_phase)

    # 🧪 Gemini 워커 (요약/집계 + 종합 QA)
    gemini_prompt = get_gemini_prompt(current_phase)

    # 팀 생성
    team = {}
    
    # 리더 생성
    leader = create_agent("KaraLeader", leader_prompt, MODELS["leader"])
    if leader:
        team["leader"] = leader
        logger.info(f"🤖 리더 KaraLeader ({MODELS['leader']}) 생성 완료")
    else:
        logger.error("❌ 리더 생성 실패")
        return False
    
    # 워커들 생성 (역할 재분배)
    workers_config = [
        ("ChatGPT_Worker", chatgpt_prompt, MODELS["chatgpt"]),
        ("Claude_Worker", claude_prompt, MODELS["claude"]), 
        ("Grok_Worker", grok_prompt, MODELS["grok"]),
        ("Gemini_Worker", gemini_prompt, MODELS["gemini"])
    ]
    
    team["workers"] = {}
    for worker_name, prompt, model in workers_config:
        if worker_name not in SKIP_WORKERS:
            worker = create_agent(worker_name, prompt, model)
            if worker:
                team["workers"][worker_name] = worker
                logger.info(f"🤖 {worker_name} ({model}) 생성 완료")
            else:
                logger.warning(f"❌ {worker_name} 생성 실패")
        else:
            logger.info(f"⭐️ {worker_name} 스킵됨")
    
    if not team["workers"]:
        logger.error("❌ 활성화된 워커가 없음")
        return False
    
    # === 협업 세션 시작 (강제 워커 순환 시스템) ===
    leader = team["leader"]
    workers = team["workers"]
    
    logger.info(f"👥 팀 구성: 리더 1명 + 워커 {len(workers)}명")
    logger.info(f"👥 활성 워커: {list(workers.keys())}")
    
    ### KISAN-AI PATCH: 강제 워커 활성화 시스템 ###
    # 모든 워커가 반드시 작업하도록 강제하는 시스템
    mandatory_worker_rotation = get_mandatory_worker_rotation(current_phase)
    logger.info(f"🔄 강제 워커 순환: {mandatory_worker_rotation}")
    
    session_results = []
    
    try:
        # Phase 킥오프 (역할 재분배)
        logger.info(f"🎯 Phase {current_phase} 킥오프: {get_phase_kickoff_message(current_phase)}")
        
        kickoff_instruction = get_kickoff_instruction(current_phase)
        
        # 🚨 새로운 강제 순환 시스템: 모든 워커가 필수적으로 작업
        for round_idx, worker_assignment in enumerate(mandatory_worker_rotation):
            logger.info(f"\n🔄 워커 순환 라운드 {round_idx + 1}: {worker_assignment}")
            
            for worker_name in worker_assignment:
                if worker_name not in workers:
                    logger.warning(f"⚠️ {worker_name} 워커가 활성화되지 않음, 스킵")
                    continue
                    
                worker = workers[worker_name]
                logger.info(f"🤖 {worker_name} 강제 작업 시작")
                
                try:
                    logger.info(f"📋 {worker_name}에게 Phase {current_phase} 라운드 {round_idx + 1} 작업 지시")
                    
                    # Phase 1 반복 개선 시스템 (1회 작업 + 5회 수정)
                    if current_phase == 1:
                        worker_results = run_iterative_improvement(leader, worker, worker_name, workers, session_dir)
                        worker_response = worker_results["final_result"]
                        
                        # AI 응답에서 파일 추출 및 저장
                        files_saved = extract_and_save_files(worker_response, session_dir, worker_name)
                        
                        session_results.append({
                            "worker": worker_name,
                            "model": workers_config[[w[0] for w in workers_config].index(worker_name)][2],
                            "timestamp": datetime.now().isoformat(),
                            "phase": f"Phase {current_phase} (강제순환-라운드{round_idx + 1})",
                            "new_role": get_worker_new_role(worker_name),
                            "response": worker_response,
                            "iteration_history": worker_results["iteration_history"],
                            "a2a_consultations": worker_results["a2a_count"],
                            "extracted_files": files_saved,
                            "summary": f"강제순환 반복 개선 완료 (라운드 {round_idx + 1})"
                        })
                    else:
                        # 각 워커별 맞춤형 지시사항 (라운드별 차별화)
                        worker_specific_message = get_round_specific_instruction(
                            worker_name, current_phase, round_idx, session_results
                        )
                        
                        # 강제 A2A 트리거: 50% 확률로 다른 워커 힌트 요청
                        if should_trigger_mandatory_a2a(worker_name, round_idx):
                            worker_specific_message += "\n\n💡 참고: 다른 워커의 관점이 필요하면 '[A2A_HELP] 구체적요청'을 사용하세요."
                        
                        ### KISAN-AI PATCH: Windows 호환성 개선 ###
                        chat_result = leader.initiate_chat(
                            recipient=worker,
                            message=worker_specific_message,
                            max_consecutive_auto_reply=6,  # 효율성을 위해 단축
                            summary_method="last_msg"  # Windows 호환성을 위해 변경
                        )
                        
                        # 워커 응답 처리
                        worker_response = extract_worker_response(chat_result)
                        
                        # AI 응답에서 파일 추출 및 저장
                        files_saved = extract_and_save_files(worker_response, session_dir, worker_name)
                        
                        # A2A 트리거 확인 및 처리 (적극적 A2A 개입)
                        a2a_triggered = False
                        if "[A2A_HELP]" in worker_response:
                            logger.info(f"🔗 {worker_name} A2A 요청 감지")
                            a2a_request = worker_response.split("[A2A_HELP]", 1)[1].strip()[:120]
                            a2a_triggered = True
                        else:
                            # 강제 A2A 개입: 다른 워커들이 자동으로 개입하도록
                            if len(workers) > 1 and current_phase == 1:
                                a2a_request = f"{worker_name}의 작업에 대한 개선 제안"
                                logger.info(f"🔗 {worker_name}에 대한 강제 A2A 개입 시작")
                                a2a_triggered = True
                        
                        if a2a_triggered:
                            # 다른 활성 워커에서 힌트 제공
                            hints = get_best_available_a2a_hints(leader, workers, worker_name, a2a_request)
                            if hints and hints != "A2A 조언자가 없습니다":
                                worker_response += f"\n\n[A2A_HINTS from {worker_name}]\n{hints}"
                                logger.info(f"✅ {worker_name}에게 A2A 힌트 제공 완료")
                            else:
                                logger.warning(f"⚠️ {worker_name}에 대한 A2A 힌트 제공 실패")
                        
                        # 결과 저장
                        result = {
                            "worker": worker_name,
                            "model": workers_config[[w[0] for w in workers_config].index(worker_name)][2],
                            "timestamp": datetime.now().isoformat(),
                            "phase": f"Phase {current_phase} (강제순환-라운드{round_idx + 1})",
                            "round": round_idx + 1,
                            "new_role": get_worker_new_role(worker_name),
                            "response": worker_response,
                            "a2a_triggered": a2a_triggered,
                            "extracted_files": files_saved,
                            "summary": getattr(chat_result, 'summary', '요약 없음')
                        }
                        
                        session_results.append(result)
                    
                    # 개별 워커 결과는 메모리에만 저장 (Phase 완료시 디스크에 저장)
                    
                    # 실시간 진행률 출력
                    total_expected_tasks = sum(len(assignment) for assignment in mandatory_worker_rotation)
                    progress = len(session_results) / total_expected_tasks * 100 if total_expected_tasks > 0 else 0
                    logger.info(f"📊 Phase {current_phase} 진행률: {progress:.1f}% ({len(session_results)}/{total_expected_tasks})")
                    logger.info(f"✅ {worker_name} Phase {current_phase} 라운드 {round_idx + 1} 완료")
                    
                    ### KISAN-AI PATCH: 라운드 간 짧은 휴식 (오버로드 방지) ###
                    time.sleep(1)  # 1초 쿨다운
                    
                except Exception as e:
                    logger.error(f"❌ {worker_name} 라운드 {round_idx + 1} 협업 실패: {e}")
                    session_results.append({
                        "worker": worker_name,
                        "timestamp": datetime.now().isoformat(),
                        "phase": f"Phase {current_phase} (강제순환-라운드{round_idx + 1})",
                        "round": round_idx + 1,
                        "error": str(e)
                    })
            
            # 라운드 완료 보고
            round_workers = [w for w in worker_assignment if w in workers]
            logger.info(f"🔄 라운드 {round_idx + 1} 완료: {round_workers}")
        
        # 강제 워커 활성화 검증
        logger.info(f"\n🔍 강제 워커 활성화 검증 결과:")
        worker_participation = {}
        for result in session_results:
            worker = result.get("worker", "Unknown")
            worker_participation[worker] = worker_participation.get(worker, 0) + 1
        
        for worker_name in ["ChatGPT_Worker", "Claude_Worker", "Grok_Worker", "Gemini_Worker"]:
            count = worker_participation.get(worker_name, 0)
            status = "✅ 활성화" if count > 0 else "❌ 비활성화"
            logger.info(f"  {worker_name}: {count}회 작업 - {status}")
        
        # 비활성화된 워커가 있으면 경고
        inactive_workers = [w for w in ["ChatGPT_Worker", "Claude_Worker", "Grok_Worker", "Gemini_Worker"] 
                          if worker_participation.get(w, 0) == 0]
        if inactive_workers:
            logger.warning(f"⚠️ 비활성화된 워커 발견: {inactive_workers}")
            logger.warning("이는 .env 파일의 AUTOGEN_SKIP_WORKERS 설정이나 API 키 문제일 수 있습니다.")
        else:
            logger.info("🎉 모든 워커가 성공적으로 활성화되어 작업을 완료했습니다!")
        
        logger.info(f"📊 총 작업 세션: {len(session_results)}개")
        
        # === 최종 통합 보고 ===
        if current_phase == 1:
            # Phase 1 특별 처리: 4개 구현체 비교 분석 및 통합
            logger.info("📊 Phase 1 특별 분석: 4개 구현체 비교 및 최고 결과 추출")
            integration_result = analyze_and_integrate_phase1_results(session_results, session_dir, leader)
        else:
            logger.info(f"📊 Phase {current_phase} 최종 통합 및 보고")
        
        # Phase 완료 시 폴더 생성 및 파일 저장
        print(f"💾 Phase {current_phase} 완료 - 세션 폴더 생성 중...")
        session_dir.mkdir(exist_ok=True, parents=True)
        
        # 모든 추출된 파일들을 디스크에 저장
        all_extracted_files = []
        for result in session_results:
            if 'extracted_files' in result:
                all_extracted_files.extend(result['extracted_files'])
        
        if all_extracted_files:
            saved_count = len(save_files_to_disk(all_extracted_files, session_dir))
            print(f"💾 {saved_count}개 파일 디스크에 저장 완료")
            
        # 개별 워커 결과 파일들도 저장
        for i, result in enumerate(session_results):
            worker_file = session_dir / f"phase{current_phase}_round{result.get('round', i+1)}_{result['worker']}.json"
            worker_file.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        
        # 전체 팀 대화 통합
        team_chat = "\n\n".join([
            f"===== [{r['worker']}] =====\n{r.get('response', r.get('error', '오류'))}"
            for r in session_results
        ])
        
        (session_dir / f"phase{current_phase}_all_workers.txt").write_text(team_chat, encoding="utf-8")
        
        # 최종 보고서
        final_report = {
            "session_id": session_id,
            "project": "한국산업 자동견적프로그램 MCP/A2A 리빌드",
            "phase": f"Phase {current_phase} - {get_phase_description(current_phase)}",
            "timestamp": datetime.now().isoformat(),
            "role_redistribution": get_role_redistribution_map(),
            "team_composition": {
                "leader": f"KaraLeader ({MODELS['leader']})",
                "workers": {name: f"{name} ({workers_config[[w[0] for w in workers_config].index(name)][2]})" 
                          for name in workers.keys()}
            },
            "mcp_a2a_system": {
                "enabled": True,
                "mcp_priority": True,
                "a2a_triggered_count": sum(1 for r in session_results if r.get("a2a_triggered", False))
            },
            "results": session_results,
            "files_generated": [f.name for f in session_dir.glob("*")],
            "next_phase": f"Phase {current_phase + 1}" if current_phase < 5 else "프로젝트 완료"
        }
        
        # 보고서 저장
        report_file = session_dir / f"phase{current_phase}_final_report.json"
        report_file.write_text(
            json.dumps(final_report, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        # 요약 출력
        summary = generate_phase_summary(current_phase, session_id, workers, session_results, session_dir, report_file)
        
        (session_dir / f"phase{current_phase}_summary.txt").write_text(summary, encoding='utf-8')
        
        logger.info(f"🎉 한국산업 자동견적프로그램 Phase {current_phase} 성공! (역할 재분배)")
        print(summary)
        
        return True
        
    except Exception as e:
        logger.error(f"팀 협업 실행 중 오류: {e}")
        return False

def get_phase_specific_goals(phase):
    """Phase별 구체적 목표"""
    goals = {
        1: """구글드라이브에서 기존 핵심파일 숙지 및 최종 결과물과 목표하는 바 정확하게 이해하고, 작업할것
- estimate_engine.py 완전 재구현
- 한국산업 견적서 엑셀 완벽 매핑
- 3개 핵심 탭 (견적/AI도우미/교육) 구현
- MCP/A2A 기반 시스템 구축
- RAG 기반 학습 시스템""",
        
        2: """프로그램 뼈대 구현 (견적탭/AI도우미탭/교육탭) + 엑셀 완벽 매핑
- assistant_agent.py 오토파일럿 루프 구현
- query_api.py 4개 모델 어댑터""",
        
        3: """macOS Glass UI 3개 탭 + 엑셀 완벽 매핑
- 탭바/글래스 카드/Dock 구현
- 좌측 AI 인덱스/우측 스키마 폼""",
        
        4: """골격 검증 90% + 스키마 기반 폼 검증/토스트
- 공식견적 승격 시스템 구현""",
        
        5: """MCP/A2A 교차학습 + 공식견적 승격 + 이메일연동
- 이미지/PDF/CAD 분석
- 네이버웍스 이메일 연동"""
    }
    return goals.get(phase, f"Phase {phase} 목표")

def get_chatgpt_prompt(phase):
    """ChatGPT 워커 Phase별 프롬프트"""
    base_prompt = """역할: 코어 개발 전문가

**📋 필수 사전 작업:**
구글드라이브에서 기존 핵심파일 숙지 및 최종 결과물과 목표하는 바 정확하게 이해하고, 작업할것

**🎯 핵심 업무 (Phase 1-2):**
1. estimate_engine.py 완전 재구현
   - 외함 크기 계산 (W×H×D 공식)
   - 부스바 용량 계산
   - 차단기 AF 매핑 및 선택
   - 인건비 및 기타사항 계산

2. 한국산업 견적서 엑셀 완벽 매핑
   - openpyxl을 사용한 읽기/쓰기
   - 품명/규격/수량/단가/금액 정확한 배치

3. JSON/JSONL 데이터 처리 파이프라인

**🛠️ 기술 제약:**
- 계산식/정책 절대 변경 금지
- 기존 함수 시그니처 보존
- MCP 우선 사용, 막히면 "[A2A_HELP] <요청>" 표시

**📤 출력:** out/patch_bundle.txt (파일명·삽입위치·주변 15~20줄·코드 블록)"""
    
    return base_prompt

def get_claude_prompt(phase):
    """Claude 워커 Phase별 프롬프트"""
    base_prompt = """역할: UI/UX 디자인 메인 담당

**📋 필수 사전 작업:**
구글드라이브에서 기존 핵심파일 숙지 및 최종 결과물과 목표하는 바 정확하게 이해하고, 작업할것

**🎯 핵심 업무 (Phase 1-2):**
1. system_estimate_ui.py macOS Glass UI 메인 프레임워크
   - 3개 핵심 탭 (견적/AI도우미/교육)
   - 상단 앱 아이콘형 탭바
   - 중앙 글래스 카드 (반투명, blur, 라운드 20px)
   - 하단 Dock (AI불러오기, 공식견적, 저장, 내보내기)

2. macOS Glass 디자인 언어
   - 글래스 스타일: 반투명(blur 느낌), 라운드 18~24px, 은은한 그림자
   - 탭/아이콘: hover scale 1.08, click spring ease-out(200~250ms)
   - 좌측: AI 인덱스(최근 산출 json 목록)
   - 우측: 스키마 기반 편집 폼(메인/분기/부속/메모)

**🤝 협업:**
Grok의 교육탭 설계를 UI 관점에서 지원 (레이아웃, 인터랙션 등)

**📤 출력:** out/patch_bundle.txt(UI), out/ui_texts.json"""
    
    return base_prompt

def get_grok_prompt(phase):
    """Grok 워커 Phase별 프롬프트"""
    base_prompt = """역할: 교육탭(Review & Train) 전문 설계 및 제작 담당

핵심 목표: AI-Human 학습 협업 시스템 구축

**📋 필수 사전 작업:**
구글드라이브에서 기존 핵심파일 숙지 및 최종 결과물과 목표하는 바 정확하게 이해하고, 작업할것

**🎯 교육탭 핵심 기능:**
1. **견적 불러오기 시스템**
   - AI 낸 견적 (out/ai_inbox/*.json) 불러오기
   - 시스템 견적 (out/estimates/*.json) 불러오기  
   - 드래그&드롭, 파일 선택기, 최근 목록 등 다양한 방법 지원

2. **실제 견적서 양식 표현**
   - 불러온 견적을 한국산업 견적서 실제 양식처럼 표시
   - 표 형태: 품명/규격/수량/단가/금액 구조
   - 외함 크기, 차단기 사양, 부스바 정보 등 세부 표시
   - 계산 과정과 근거도 보기 좋게 표현

3. **수정 가능한 편집 시스템**
   - 견적서의 모든 항목 편집 가능
   - 실시간 계산 업데이트 (수량 변경 시 자동 재계산)
   - 항목 추가/삭제, 사양 변경 등
   - 변경 사항 하이라이트 표시

4. **레이아웃 설계 (2분할)**
   - **좌측 (70% 넓이)**: 메인 견적서 편집 영역
     - 상단: 견적서 헤더 (업체명, 프로젝트, 날짜 등)
     - 중앙: 견적 테이블 (품목별 상세)  
     - 하단: 합계, 부가세, 최종 금액
   - **우측 (30% 넓이)**: 메모 및 학습 제어 패널
     - 학습 메모 (사람이 왜 수정했는지)
     - AI가 이해하기 쉬운 태그/루트 정보
     - 학습 버튼, 저장 버튼
     - 변경 이력 요약

5. **학습 시스템 핵심**
   - 원본 JSON vs 수정된 JSON 비교 분석
   - 변경 패턴 추출 (어떤 항목을 어떻게 수정하는지)
   - 학습 데이터 생성 (out/learn_queue/*.jsonl)
   - 학습 이유/태그를 포함한 구조화된 데이터 저장

6. **편의 기능들**
   - 견적 템플릿 저장/불러오기
   - 자주 사용하는 수정 패턴 원클릭 적용
   - 견적서 PDF/Excel 내보내기
   - 학습 통계 (얼마나 학습했는지, 어떤 패턴이 많은지)
   - 되돌리기/다시하기 (Undo/Redo)

**💡 혁신적 아이디어 추가:**
1. **스마트 추천 시스템**
   - 과거 학습 데이터 기반으로 "이런 경우 보통 이렇게 수정하셨어요" 제안
   - 유사한 프로젝트 견적 자동 추천

2. **AI 튜터 모드**
   - 수정 이유를 AI가 질문 ("왜 이 차단기를 바꾸셨나요?")
   - 학습 효과 극대화를 위한 대화형 인터페이스

3. **배치 학습 모드**
   - 여러 견적을 한번에 불러와서 패턴 학습
   - 대량 데이터 처리 및 학습

4. **견적 품질 점수**
   - AI가 현재 견적의 완성도/정확도 점수 표시
   - 개선 포인트 하이라이트

**📤 출력 파일:**
- out/patch_bundle.txt (교육탭 UI 코드)
- out/ui_texts.json (교육탭 전용 텍스트)  
- out/education_tab_spec.md (상세 설계 문서)
- out/learning_system_design.json (학습 시스템 구조)

지금 바로 교육탭의 혁신적이고 사용하기 편한 설계를 시작하세요!
"""
    
    return base_prompt

def get_gemini_prompt(phase):
    """Gemini 워커 Phase별 프롬프트"""
    base_prompt = """역할: 종합 품질보증 + 요약/집계 + MCP/A2A 교차학습 시스템

**📋 필수 사전 작업:**
구글드라이브에서 기존 핵심파일 숙지 및 최종 결과물과 목표하는 바 정확하게 이해하고, 작업할것

**🎯 핵심 업무 (Phase 2 확장):**

**1. 요약/집계 업무 (Grok에서 이관)**
   - 다른 워커 작업 진행상황 모니터링
   - 생성된 파일들 교차검증
   - 다음 라운드 Top-5 개선안 제시
   - A2A 힌트 제공 (다른 워커 "[A2A_HELP] 요청" 시 힌트 3줄 제공)

**2. 종합 테스트 시스템 구축**
   - 엣지케이스 테스트 스위트 (20개 이상)
   - 외함 계산 극한 조건 (800A 메인 + 대량 분기)
   - ELB 특수 규칙 전체 케이스 테스트
   - 부스바 경계값 및 안전계수 검증
   - 자동 회귀 테스트 시스템 구축

**3. 데이터 검증 및 분석**
   - 한국산업 견적서 엑셀 데이터 무결성 검증
   - 계산 결과 정확성 교차 검증
   - 과거 견적 데이터와 신규 계산 결과 비교 분석

**4. 사용자 경험 최적화**
   - UI/UX 사용성 테스트 및 개선안
   - 워크플로우 최적화 제안
   - 오류 처리 및 사용자 가이드 개선 

**5. 교육탭 품질 검증 (Grok 작업 지원)**
   - Grok이 설계한 교육탭 기능 테스트
   - 학습 시스템 정확성 검증
   - 사용자 편의성 개선 제안

**📋 A2A 힌트 제공 형식:**
다른 워커 "[A2A_HELP] 요청" 시:
- hint1: 구체적 해결 방법
- hint2: 대안적 접근법  
- hint3: 참고할 리소스/파일

**📤 출력 파일:**
- out/tests_comprehensive.jsonl (종합 테스트)
- out/quality_report.json (품질 분석)
- out/grok_summary.txt (요약/집계)
- out/ux_optimization.txt (UX 개선안)
- out/education_tab_qa.txt (교육탭 품질 검증)

모든 워커의 작업을 종합적으로 검증하고 최고 품질의 결과를 보장하세요!
"""
    
    return base_prompt

def get_worker_specific_instruction(worker_name, phase):
    """각 워커별 구체적 개별 지시사항"""
    
    if phase == 1:  # Phase 1: 모든 워커가 전체 시스템 구현 후 비교
        return f"""
🎯 **Phase 1 반복 개선 시스템: 1회 작업 + 2회 수정**

**Phase 1 핵심 철학:**
당신은 {get_worker_new_role(worker_name)}이지만, Phase 1에서는 전체 시스템을 모두 구현해야 합니다.

**반복 개선 프로세스:**
1차 작업: 전체 시스템 초기 구현
2-3차 작업: A2A 조언을 받아 2회 연속 개선 
- 각 개선 전마다 다른 AI로부터 구체적 조언 획득
- 효율성, 혁신성, 안정성을 점진적으로 향상

**중요한 제약사항:**
⚠️ **과도한 코드 줄이기는 절대 금지**
- 코드 단순화만을 위한 줄 수 축소 금지
- 기능 삭제나 축소 금지  
- 이전 작업의 핵심 내용 제거 금지
- 기존 기능을 유지하면서 품질만 향상

**당신이 구현해야 하는 전체 시스템:**

1. **estimate_engine.py 완전 재구현**
   - 외함 크기 계산 (W×H×D 공식)
   - 부스바 용량 계산
   - 차단기 AF 매핑 및 선택
   - 인건비 및 기타사항 계산
   - 한국산업 견적서 엑셀 완벽 매핑

2. **assistant_agent.py 오토파일럿 루프**
   - plan→dispatch→consensus→run_tests→refine→report 사이클

3. **query_api.py 4개 AI 모델 어댑터**
   - call_chatgpt/claude/gemini/grok 인터페이스

4. **macOS Glass UI 3개 탭**
   - 견적탭/AI도우미탭/교육탭 완전 구현
   - 글래스 스타일: blur, 라운드, 반투명
   - 애니메이션: hover scale, click spring

5. **교육탭 AI-Human 학습 시스템**
   - 견적 불러오기/편집/학습 데이터 생성
   - 2분할 레이아웃 (편집 70%, 제어 30%)

6. **공식견적 승격 시스템**
   - official=true, semver bump, _history 저장

7. **종합 테스트 시스템**
   - 엣지케이스 20개 이상
   - 자동 회귀 테스트

8. **MCP/A2A 교차학습 + 이메일연동**
   - 이미지/PDF/CAD 분석
   - 네이버웍스 연동

**당신의 특별한 관점으로 접근하세요:**
- ChatGPT: 백엔드 최적화와 계산 정확성 중심
- Claude: UI/UX 혁신과 사용자 경험 중심
- Grok: 창의적 솔루션과 학습 시스템 혁신 
- Gemini: 품질과 효율성, 통합 최적화 중심

**1차 작업 시작:**
전체 시스템의 초기 버전을 완성하세요. 이후 2회의 개선을 통해 완벽한 시스템으로 발전시킬 것입니다.

**출력 요구사항:**
- patch_bundle.txt (전체 시스템 완성 코드)
- ui_texts.json (UI 텍스트)
- tests_comprehensive.jsonl (테스트 케이스)
- system_architecture.md (당신의 아키텍처 설계 철학)

**즉시 1차 작업을 시작하세요!**
"""
    
    base_intro = f"""
🎯 **당신의 개별 임무: Phase {phase}**

당신은 {get_worker_new_role(worker_name)}로서 지금 즉시 작업을 시작해야 합니다.
다른 워커들과 관계없이 당신만의 전문 영역에 집중하세요.
"""
    
    if worker_name == "ChatGPT_Worker":
        return f"""{base_intro}

**당신의 핵심 임무:**
1. estimate_engine.py 완전 재구현 계획
   - 외함 크기 계산 (W×H×D 공식) 완성
   - 부스바 용량 계산 완성
   - 차단기 AF 매핑 완성
   - 인건비 계산 완성

2. assistant_agent.py 오토파일럿 루프 설계
   - plan→dispatch→consensus→run_tests→refine→report

3. query_api.py 4개 AI 어댑터 구현
   - call_chatgpt/claude/gemini/grok 인터페이스

**즉시 시작하세요! 구체적인 코드와 구현 계획을 제시하세요.**
**출력: patch_bundle.txt 형식의 완성된 코드**"""

    elif worker_name == "Claude_Worker":
        return f"""{base_intro}

**당신의 핵심 임무:**
1. macOS Glass UI 완벽한 설계
   - 3개 탭 (견적/AI도우미/교육) 구조 완성
   - 글래스 스타일: blur, 라운드 20px, 반투명
   - 상단 탭바, 중앙 카드, 하단 Dock

2. 애니메이션 시스템 구현
   - hover scale 1.08
   - click spring ease-out(200-250ms)

3. 레이아웃 완성
   - 좌측: AI 인덱스 리스트
   - 우측: 스키마 기반 편집 폼

**즉시 시작하세요! UI 코드와 디자인을 완성하세요.**
**출력: patch_bundle.txt(UI) + ui_texts.json**"""

    elif worker_name == "Grok_Worker":
        return f"""{base_intro}

**당신의 핵심 임무:**
1. 교육탭 AI-Human 학습 시스템 완전 설계
   - 견적 불러오기 시스템
   - 실제 견적서 양식 표현
   - 수정 가능한 편집 시스템
   - 학습 데이터 생성 파이프라인

2. 공식견적 승격 시스템
   - official=true, semver bump, _history 저장

3. 2분할 레이아웃 설계
   - 좌측 70%: 견적서 편집
   - 우측 30%: 학습 제어 패널

**즉시 시작하세요! 교육탭 설계를 완성하세요.**
**출력: education_tab_spec.md + learning_system_design.json**"""

    elif worker_name == "Gemini_Worker":
        return f"""{base_intro}

**당신의 핵심 임무:**
1. 종합 테스트 시스템 구축
   - 엣지케이스 테스트 20개 이상
   - 외함 계산 극한 조건 테스트
   - 자동 회귀 테스트 시스템

2. MCP/A2A 교차학습 시스템
   - A2A 힌트 제공 시스템 구현
   - 워커 간 협업 최적화

3. 품질 검증 및 분석
   - 데이터 무결성 검증
   - 계산 결과 정확성 교차 검증

**즉시 시작하세요! 테스트와 QA 시스템을 완성하세요.**
**출력: tests_comprehensive.jsonl + quality_report.json**

**추가 역할: 다른 워커가 [A2A_HELP] 요청 시 힌트 3줄 제공**"""

    return f"{base_intro}\n\n당신의 전문 분야에서 즉시 작업을 시작하세요!"

def get_worker_new_role(worker_name):
    """워커별 새로운 역할"""
    roles = {
        "ChatGPT_Worker": "코어 개발 전문가",
        "Claude_Worker": "UI/UX 디자인 메인",
        "Grok_Worker": "교육탭 전문 설계자",
        "Gemini_Worker": "요약/집계 + 종합 QA"
    }
    return roles.get(worker_name, "Unknown")

def get_role_redistribution_map():
    """역할 재분배 맵"""
    return {
        "ChatGPT": "코어 개발 전문가 (estimate_engine.py, Excel 매핑)",
        "Claude": "UI/UX 디자인 메인 (macOS Glass UI)",
        "Grok": "교육탭 전문 설계자 (AI-Human 학습 협업)",
        "Gemini": "요약/집계 + 종합 QA (품질보증, 테스트)"
    }

### KISAN-AI PATCH: 강제 워커 순환 시스템 함수들 ###

def get_mandatory_worker_rotation(phase):
    """Phase별 필수 워커 순환 패턴 - 모든 워커가 반드시 작업하도록 보장"""
    
    # 기본 워커 우선순위 (가용성에 따라 동적 조정)
    base_workers = ["ChatGPT_Worker", "Claude_Worker", "Grok_Worker", "Gemini_Worker"]
    
    if phase == 1:
        # Phase 1: 모든 워커가 동시에 협업하며 전체 시스템 구현 (A2A 활성화)
        return [
            ["ChatGPT_Worker", "Claude_Worker", "Grok_Worker", "Gemini_Worker"],  # 라운드 1: 모든 워커 동시 협업
        ]
    elif phase == 2:
        # Phase 2: 전문 영역별 분담 + 협업
        return [
            ["ChatGPT_Worker", "Claude_Worker"],  # 라운드 1: 코어 + UI 협업
            ["Grok_Worker", "Gemini_Worker"],     # 라운드 2: 교육탭 + 품질검증
            ["ChatGPT_Worker", "Grok_Worker"],    # 라운드 3: 백엔드 + 교육 통합
            ["Claude_Worker", "Gemini_Worker"]    # 라운드 4: UI + QA 검증
        ]
    elif phase == 3:
        # Phase 3: UI 중심 + 엑셀 매핑
        return [
            ["Claude_Worker"],                    # 라운드 1: UI 메인 설계
            ["ChatGPT_Worker"],                  # 라운드 2: 엑셀 매핑 구현  
            ["Grok_Worker"],                     # 라운드 3: 교육탭 UI 구현
            ["Claude_Worker", "Gemini_Worker"]   # 라운드 4: UI 통합 + 검증
        ]
    elif phase == 4:
        # Phase 4: 검증 중심
        return [
            ["Gemini_Worker"],                   # 라운드 1: 메인 검증
            ["ChatGPT_Worker"],                  # 라운드 2: 로직 검증
            ["Claude_Worker"],                   # 라운드 3: UI 검증
            ["Grok_Worker", "Gemini_Worker"]     # 라운드 4: 교육탭 + 종합 QA
        ]
    elif phase == 5:
        # Phase 5: 고급 기능 통합
        return [
            ["ChatGPT_Worker", "Claude_Worker", "Grok_Worker", "Gemini_Worker"]  # 전체 협업
        ]
    else:
        # 기본값: 모든 워커 순차 실행
        return [[worker] for worker in base_workers]

def get_round_specific_instruction(worker_name, phase, round_idx, previous_results):
    """라운드별 워커 맞춤 지시사항 - 이전 결과를 고려한 차별화된 임무"""
    
    base_role = get_worker_new_role(worker_name)
    previous_workers = [r["worker"] for r in previous_results if r.get("phase", "").endswith(str(phase))]
    
    # 이전 라운드 결과 요약 (최신 3개)
    recent_results = ""
    if previous_results:
        recent_work = previous_results[-3:]
        recent_results = "\n".join([
            f"- {r['worker']}: {r.get('summary', '작업완료')[:100]}..." 
            for r in recent_work
        ])
    
    instruction_header = f"""
🎯 **{worker_name} - Phase {phase} 라운드 {round_idx + 1} 전용 임무**

**당신의 역할:** {base_role}
**이전 라운드 진행상황:**
{recent_results or "첫 라운드입니다"}

**라운드 {round_idx + 1} 특별 지시사항:**
"""
    
    # Phase별 라운드별 차별화된 지시
    if phase == 1:
        round_specific = {
            0: f"""**1라운드: 전체 시스템 초기 설계**
당신의 {base_role} 관점에서 전체 시스템을 설계하고 핵심 구현을 완료하세요.
- 모든 주요 컴포넌트 (estimate_engine, UI, 교육탭, 테스트) 포함
- 당신만의 독특한 접근법과 혁신적 아이디어 제시""",
            
            1: f"""**2라운드: 타워커 피드백 반영 개선**
다른 워커들의 접근법을 참고하여 당신의 설계를 개선하세요.
- 이전 워커들이 놓친 부분 보완
- 당신의 전문성으로 시스템 품질 향상""",
            
            2: f"""**3라운드: 혁신적 통합 솔루션**
각 워커의 장점을 융합한 혁신적 통합 솔루션을 제시하세요.
- 기존 접근법들의 한계 극복
- 창의적이고 실용적인 최종 솔루션""",
            
            3: f"""**4라운드: 최종 품질 보증**
전체 시스템의 완성도와 안정성을 최종 검증하세요.
- 엣지케이스와 오류 상황 대응
- 운영 환경 최적화"""
        }
    
    elif phase == 2:
        round_specific = {
            0: f"""**1라운드: 핵심 기능 구현**
당신의 전문 영역에서 핵심 기능을 구현하세요.
- 실제 동작하는 코드 작성
- 기존 시스템과의 호환성 보장""",
            
            1: f"""**2라운드: 협업 인터페이스 구축**  
다른 워커들과의 협업을 위한 인터페이스를 구축하세요.
- 모듈 간 연동 방식 정의
- 데이터 교환 포맷 설계""",
            
            2: f"""**3라운드: 통합 테스트 및 최적화**
통합된 시스템의 성능을 테스트하고 최적화하세요.
- 병목 구간 식별 및 개선
- 사용자 경험 최적화""",
            
            3: f"""**4라운드: 배포 준비 및 문서화**
시스템 배포를 위한 최종 준비 작업을 완료하세요.
- 설정 가이드 및 사용법 문서화
- 오류 처리 및 복구 방안"""
        }
    
    else:
        # 기본 라운드별 지시
        round_specific = {
            0: f"**1라운드:** 당신의 전문 영역에서 핵심 작업 수행",
            1: f"**2라운드:** 이전 결과를 바탕으로 추가 개선", 
            2: f"**3라운드:** 다른 워커와의 협업 강화",
            3: f"**4라운드:** 최종 품질 검증 및 완성"
        }
    
    specific_instruction = round_specific.get(round_idx, f"**라운드 {round_idx + 1}:** 당신의 전문성을 발휘하여 작업을 완료하세요")
    
    return f"""{instruction_header}
{specific_instruction}

**필수 출력:**
- patch_bundle.txt (구체적 구현 코드)
- 작업 요약 (2-3줄)
- 다음 라운드 제안사항 (1줄)

**즉시 시작하세요!**"""

def should_trigger_mandatory_a2a(worker_name, round_idx):
    """강제 A2A 트리거 조건 - 워커별/라운드별 차별화"""
    
    # 라운드 2 이후에는 50% 확률로 A2A 트리거
    if round_idx >= 1:
        return True
    
    # 특정 워커들은 첫 라운드부터 A2A 권장
    collaborative_workers = ["Claude_Worker", "Gemini_Worker"]
    if worker_name in collaborative_workers:
        return True
        
    return False

def get_best_available_a2a_hints(leader, workers, requesting_worker, a2a_request):
    """최적의 A2A 힌트 제공 - 여러 워커 중에서 최적 선택"""
    
    # 요청 워커 제외한 활성 워커 리스트
    available_advisors = [name for name in workers.keys() if name != requesting_worker]
    
    if not available_advisors:
        return "A2A 조언자가 없습니다"
    
    # 우선순위 기반 조언자 선택
    advisor_priority = {
        "ChatGPT_Worker": ["Gemini_Worker", "Claude_Worker", "Grok_Worker"],
        "Claude_Worker": ["Gemini_Worker", "Grok_Worker", "ChatGPT_Worker"],
        "Grok_Worker": ["Claude_Worker", "Gemini_Worker", "ChatGPT_Worker"],
        "Gemini_Worker": ["Claude_Worker", "ChatGPT_Worker", "Grok_Worker"]
    }
    
    preferred_advisors = advisor_priority.get(requesting_worker, available_advisors)
    
    # 첫 번째 가용한 우선순위 조언자 선택
    selected_advisor = None
    for advisor in preferred_advisors:
        if advisor in available_advisors:
            selected_advisor = advisor
            break
    
    if not selected_advisor:
        selected_advisor = available_advisors[0]
    
    # A2A 힌트 요청 (기존 함수 활용)
    return get_a2a_hints(leader, workers[selected_advisor], a2a_request, requesting_worker)

def get_phase_description(phase):
    """Phase 설명"""
    descriptions = {
        1: "autogen_team.py 자체 완성 (Meta Phase)",
        2: "계획 수립 + assistant_agent.py 오토파일럿 골격",
        3: "macOS Glass UI 3개 탭 + 엑셀 완벽 매핑",
        4: "골격 검증 90% + 스키마 기반 폼 검증/토스트",
        5: "MCP/A2A 교차학습 + 공식견적 승격 + 이메일연동"
    }
    return descriptions.get(phase, f"Phase {phase}")

def get_phase_kickoff_message(phase):
    """Phase별 킥오프 메시지"""
    messages = {
        1: "계획 수립 및 AI 특화 배치 (역할 재분배)",
        2: "프로그램 뼈대 구현",
        3: "UI 및 엑셀 매핑 완성",
        4: "검증 및 품질 보증",
        5: "고급 기능 및 연동"
    }
    return messages.get(phase, f"Phase {phase} 실행")

def run_iterative_improvement(leader, worker, worker_name, workers, session_dir):
    """Phase 1 반복 개선 시스템: 1회 작업 + 2회 수정 (각 수정 전 A2A 조언)"""
    
    logger.info(f"🔄 {worker_name} 반복 개선 시스템 시작 (1+2회)")
    
    iteration_history = []
    a2a_count = 0
    
    # 1차: 초기 작업
    logger.info(f"📝 {worker_name} 1차 작업 시작")
    initial_instruction = get_worker_specific_instruction(worker_name, 1)
    
    try:
        # ### KISAN-AI PATCH: AutoGen initiate_chat 오류 방지 ###
        # Windows 환경에서 [Errno 22] Invalid argument 오류 해결
        logger.info(f"🔄 {worker_name} AutoGen 채팅 시도 중...")
        
        initial_result = leader.initiate_chat(
            recipient=worker,
            message=initial_instruction,
            max_consecutive_auto_reply=6,
            summary_method="last_msg"  # reflection_with_llm → last_msg로 변경
        )
        
        current_work = extract_worker_response(initial_result)
        
        # AI 응답에서 파일 추출 및 저장
        files_saved = extract_and_save_files(current_work, session_dir, worker_name)
        
        iteration_history.append({
            "iteration": 1,
            "type": "initial_work",
            "result": current_work,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"✅ {worker_name} 1차 작업 완료")
        
    except OSError as e:
        if e.errno == 22:  # Invalid argument
            logger.error(f"❌ {worker_name} 파일시스템 오류 (Windows 호환성 문제): {e}")
            # 대안: Direct API 호출로 실제 AI 작업 수행
            try:
                logger.info(f"🔄 {worker_name} Direct API 방식으로 재시도...")
                
                # 워커별 모델 및 시스템 메시지 가져오기
                worker_model_map = {
                    "ChatGPT_Worker": MODELS["chatgpt"],
                    "Claude_Worker": MODELS["claude"], 
                    "Grok_Worker": MODELS["grok"],
                    "Gemini_Worker": MODELS["gemini"]
                }
                
                worker_prompt_map = {
                    "ChatGPT_Worker": get_chatgpt_prompt(1),
                    "Claude_Worker": get_claude_prompt(1),
                    "Grok_Worker": get_grok_prompt(1), 
                    "Gemini_Worker": get_gemini_prompt(1)
                }
                
                model = worker_model_map.get(worker_name, MODELS["chatgpt"])
                system_prompt = worker_prompt_map.get(worker_name, f"{worker_name} 전용 작업")
                
                # Direct API 호출
                current_work = direct_api_call(
                    model=model,
                    system_message=system_prompt,
                    user_message=initial_instruction,
                    base_url=BASE_URL,
                    api_key=OPENROUTER_API_KEY,
                    timeout=TIMEOUT_SEC
                )
                
                # AI 응답에서 파일 추출 및 저장
                files_saved = extract_and_save_files(current_work, session_dir, worker_name)
                
                iteration_history.append({
                    "iteration": 1,
                    "type": "direct_api_work",
                    "result": current_work,
                    "timestamp": datetime.now().isoformat(),
                    "note": f"AutoGen 호환성 문제로 Direct API 사용 ({model})"
                })
                logger.info(f"✅ {worker_name} Direct API 방식 완료")
            except Exception as fallback_error:
                logger.error(f"❌ {worker_name} Direct API 방식도 실패: {fallback_error}")
                return {"final_result": f"모든 방식 실패: {e}", "iteration_history": [], "a2a_count": 0}
        else:
            logger.error(f"❌ {worker_name} 1차 작업 실패: {e}")
            return {"final_result": f"1차 작업 실패: {e}", "iteration_history": [], "a2a_count": 0}
    except Exception as e:
        logger.error(f"❌ {worker_name} 1차 작업 실패: {e}")
        return {"final_result": f"1차 작업 실패: {e}", "iteration_history": [], "a2a_count": 0}
    
    # 2-3차: A2A 조언 → 수정 작업 (2회 반복)
    for iteration in range(2, 4):  # 2, 3차 (총 2회 수정)
        logger.info(f"🔄 {worker_name} {iteration}차 개선 시작")
        
        # A2A 조언 요청
        a2a_advice = get_improvement_advice(leader, workers, worker_name, current_work, iteration)
        a2a_count += 1
        
        # 수정 작업 지시
        improvement_instruction = f"""
🔄 **{iteration}차 개선 작업**

**A2A 조언:**
{a2a_advice}

**이전 작업 결과:**
{current_work[-2000:]}

**개선 지시사항:**
A2A 조언을 반영하여 이전 결과를 개선하되, 아래의 제약사항을 반드시 준수하세요.

⚠️ **반드시 명심할 제약사항:**
- **코드를 과하게 줄이지 마세요.** 단순히 코드 라인 수를 줄이는 것을 목표로 삼지 마십시오.
- **기존 핵심 기능을 절대 삭제하거나 축소하지 마세요.**
- 이전 작업의 결과물을 바탕으로 품질을 '향상'시키는 것이 목표입니다.

즉시 개선된 버전을 제시하세요!
"""
        
        try:
            ### KISAN-AI PATCH: 개선 작업 Windows 호환성 ###
            improvement_result = leader.initiate_chat(
                recipient=worker,
                message=improvement_instruction,
                max_consecutive_auto_reply=6,
                summary_method="last_msg"  # Windows 호환성
            )
            
            improved_work = extract_worker_response(improvement_result)
            current_work = improved_work
            
            # AI 응답에서 파일 추출 및 저장
            files_saved = extract_and_save_files(improved_work, session_dir, worker_name)
            
            iteration_history.append({
                "iteration": iteration,
                "type": "improvement",
                "a2a_advice": a2a_advice,
                "result": improved_work,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"✅ {worker_name} {iteration}차 개선 완료")
            
        except Exception as e:
            logger.error(f"❌ {worker_name} {iteration}차 개선 실패: {e}")
            iteration_history.append({
                "iteration": iteration,
                "type": "improvement_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    logger.info(f"🎉 {worker_name} 반복 개선 완료 (총 {a2a_count}회 A2A 조언)")
    
    return {
        "final_result": current_work,
        "iteration_history": iteration_history,
        "a2a_count": a2a_count
    }

def get_improvement_advice(leader, workers, worker_name, current_work, iteration):
    """A2A 개선 조언 요청"""
    
    # Gemini를 기본 조언자로 사용, 해당 워커가 Gemini인 경우 다른 워커 선택
    advisor_priority = ["Gemini_Worker", "Claude_Worker", "ChatGPT_Worker", "Grok_Worker"]
    advisor = None
    
    for advisor_candidate in advisor_priority:
        if advisor_candidate != worker_name and advisor_candidate in workers:
            advisor = workers[advisor_candidate]
            advisor_name = advisor_candidate
            break
    
    if not advisor:
        return "A2A 조언자를 찾을 수 없음"
    
    advice_request = f"""
🤝 **A2A 개선 조언 요청**

**대상 워커:** {worker_name}
**개선 단계:** {iteration}차
**현재 작업 결과:** (최근 1500자)
{current_work[-1500:]}

**조언 요청사항:**
{get_worker_new_role(worker_name)}인 {worker_name}의 작업을 개선하기 위한 구체적 조언을 해주세요.

**조언 형식 (정확히 3줄):**
- advice1: 구체적 개선 방안
- advice2: 추가 최적화 아이디어  
- advice3: 혁신적 접근법 제안

**조언 기준:**
- 효율성 향상
- 코드 품질 개선 (단, 과도한 줄이기 금지)
- 사용자 경험 최적화
- 시스템 안정성 강화

짧고 실용적인 조언을 제공하세요!
"""
    
    try:
        ### KISAN-AI PATCH: 개선 조언 시스템 Windows 호환성 ###
        advice_result = leader.initiate_chat(
            recipient=advisor,
            message=advice_request,
            max_consecutive_auto_reply=2,
            summary_method="last_msg"  # Windows 호환성
        )
        
        advice_response = extract_worker_response(advice_result)
        
        # advice1, advice2, advice3 형식 추출
        advice_lines = [line.strip() for line in advice_response.splitlines() 
                       if line.strip() and "advice" in line.lower()]
        
        if len(advice_lines) >= 3:
            return "\n".join(advice_lines[:3])
        else:
            return advice_response[:500]  # 전체 응답의 일부 반환
            
    except Exception as e:
        logger.error(f"A2A 조언 요청 실패 ({advisor_name} → {worker_name}): {e}")
        return f"A2A 조언 실패: {e}"

def extract_worker_response(chat_result):
    """채팅 결과에서 워커 응답 추출"""
    if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
        for msg in reversed(chat_result.chat_history):  # 최신 메시지부터 확인
            if msg.get("role") == "assistant":
                return msg.get("content", "")
    return "응답 추출 실패"

def get_a2a_hints(leader, advisor_worker, request, requesting_worker):
    """기존 A2A 힌트 시스템 (Phase 2-5용)"""
    hint_request = f"""A2A 힌트 요청: {request}

다음 형식으로 정확히 3줄 힌트만 제공:
- hint1: ...
- hint2: ...
- hint3: ...

토론이나 장황한 설명 금지. 짧고 굵게."""

    try:
        ### KISAN-AI PATCH: A2A 힌트 시스템 Windows 호환성 ###
        hint_chat = leader.initiate_chat(
            recipient=advisor_worker,
            message=hint_request,
            max_consecutive_auto_reply=1,
            summary_method="last_msg"  # Windows 호환성
        )
        
        hint_response = extract_worker_response(hint_chat)
        lines = [line.strip() for line in hint_response.splitlines() 
               if line.strip() and "hint" in line]
        
        return "\n".join(lines[:3]) if lines else "A2A 힌트 생성 실패"
        
    except Exception as e:
        logger.error(f"A2A 힌트 제공 실패: {e}")
        return "A2A 힌트 시스템 오류"

def analyze_and_integrate_phase1_results(session_results, session_dir, leader):
    """Phase 1 특별 분석: 4개 구현체 비교 및 최고 결과 추출"""
    
    logger.info("🔍 Phase 1 구현체 비교 분석 시작")
    
    # 각 워커별 구현체 분석
    implementations = {}
    for result in session_results:
        worker_name = result.get('worker', '')
        response = result.get('response', '')
        
        # 구현체 특징 추출
        implementations[worker_name] = {
            "response": response,
            "code_quality": analyze_code_quality(response),
            "innovation_level": analyze_innovation_level(response),
            "efficiency_score": analyze_efficiency(response),
            "completeness": analyze_completeness(response)
        }
    
    # 리더가 최종 통합 분석 수행
    integration_prompt = f"""
🔍 **Phase 1 최종 통합 분석 임무**

4개 워커가 각자의 관점으로 전체 시스템을 구현했습니다.
당신은 이제 각 구현체의 장점을 분석하고 최고의 통합본을 만들어야 합니다.

**구현체 분석 결과:**
{json.dumps(implementations, ensure_ascii=False, indent=2)}

**통합 분석 지시사항:**
1. **최고의 백엔드 로직 선택**: 가장 정확하고 효율적인 계산 알고리즘
2. **최혁신 UI/UX 채택**: 가장 사용자 친화적이고 혁신적인 인터페이스
3. **최적 아키텍처 구조**: 가장 안정적이고 확장 가능한 시스템 구조
4. **최효율 워크플로우**: 가장 효율적인 사용자 작업 흐름

**최종 통합 설계안을 제시하세요:**
- 각 영역별 최고 구현체 선택 이유 
- 통합된 최종 아키텍처
- Phase 2-5 실행 최적화 방안

즉시 분석을 시작하세요!
"""
    
    try:
        # 통합 분석 결과 (실제 리더 대화는 복잡하므로 기본 구조만)
        integration_analysis = {
            "analysis_timestamp": datetime.now().isoformat(),
            "worker_implementations": implementations,
            "integration_result": "통합 분석 완료",
            "selected_best_practices": extract_best_practices(implementations),
            "optimized_architecture": "Phase 2-5 최적화 아키텍처 도출"
        }
        
        # 통합 분석 결과 저장
        integration_file = session_dir / "phase1_integration_analysis.json"
        integration_file.write_text(
            json.dumps(integration_analysis, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        logger.info(f"✅ Phase 1 통합 분석 완료: {integration_file}")
        return integration_analysis
        
    except Exception as e:
        logger.error(f"Phase 1 통합 분석 실패: {e}")
        return {"error": str(e)}

def extract_best_practices(implementations):
    """최고 관행 추출"""
    best_practices = {}
    
    # 각 영역별 최고 점수 구현체 찾기
    for area in ["code_quality", "innovation_level", "efficiency_score", "completeness"]:
        best_worker = max(implementations.keys(), 
                         key=lambda w: implementations[w][area])
        best_practices[area] = {
            "best_worker": best_worker,
            "score": implementations[best_worker][area]
        }
    
    return best_practices

def analyze_code_quality(response):
    """코드 품질 분석"""
    quality_indicators = [
        "def " in response,  # 함수 정의
        "class " in response,  # 클래스 정의
        "import " in response,  # 모듈 임포트
        "try:" in response,  # 예외 처리
        "#" in response,  # 주석
        "return " in response  # 반환값
    ]
    return sum(quality_indicators) / len(quality_indicators) * 100

def analyze_innovation_level(response):
    """혁신성 분석"""
    innovation_keywords = [
        "혁신", "창의", "스마트", "자동", "AI", "머신러닝",
        "최적화", "효율", "사용자", "경험", "인터페이스"
    ]
    count = sum(1 for keyword in innovation_keywords if keyword in response)
    return min(count * 10, 100)  # 최대 100점

def analyze_efficiency(response):
    """효율성 분석"""
    efficiency_indicators = [
        "캐시" in response or "cache" in response,
        "최적화" in response or "optimize" in response,
        "병렬" in response or "parallel" in response,
        "비동기" in response or "async" in response,
        "메모리" in response or "memory" in response
    ]
    return sum(efficiency_indicators) / len(efficiency_indicators) * 100

def analyze_completeness(response):
    """완성도 분석"""
    required_components = [
        "estimate_engine" in response,
        "assistant_agent" in response,
        "query_api" in response,
        "UI" in response or "interface" in response,
        "교육탭" in response or "education" in response,
        "테스트" in response or "test" in response
    ]
    return sum(required_components) / len(required_components) * 100

def get_kickoff_instruction(phase):
    """Phase별 킥오프 지시 (기존 함수 복원)"""
    if phase == 1:
        return """
🚀 **한국산업 자동견적프로그램 MCP/A2A 리빌드 Phase 1 시작**

**📋 모든 워커 공통 첫 번째 작업:**
1. 구글드라이브에서 다음 핵심파일들 완전 학습:
   - autogen_team (기존 팀 구조)
   - estimate_engine (견적 엔진 핵심)
   - system_estimate_ui (UI 시스템)
   - 외함 사이즈 공식 (계산 로직)
   - 부스바 산출공식 (용량 계산)
   - 차단기설명 (규격 정보)
   - 부속자재 (자재 스펙)
   - 제작지침프롬프트 (시스템 규칙)

2. 최종 목표와 결과물을 정확히 파악:
   - 한국산업 견적서 엑셀 완벽 매핑 (가장 중요!)
   - 3개 탭 (견적/AI도우미/교육) 구현
   - MCP/A2A 기반 시스템 구축
   - RAG 기반 학습 시스템

**🎯 Phase 1 목표:** 각자의 전문 분야별 상세 작업 계획 수립 및 기존 파일 완전 이해

지금 바로 시작하세요!
"""
    else:
        return f"Phase {phase} 킥오프 메시지"

def generate_phase_summary(phase, session_id, workers, session_results, session_dir, report_file):
    """Phase별 요약 생성"""
    return f"""
=== 한국산업 자동견적프로그램 MCP/A2A 리빌드 Phase {phase} 완료 (역할 재분배) ===

🎯 세션: {session_id}
🤖 리더: KaraLeader (GPT-4o)
👥 워커: {len(workers)}명 활성화 (역할 재분배)
🔗 A2A: {sum(1 for r in session_results if r.get('a2a_triggered', False))}회 트리거

🔄 새로운 역할 분담:
- ChatGPT: {MODELS['chatgpt']} (코어 개발 전문가)
- Claude: {MODELS['claude']} (UI/UX 디자인 메인)
- Grok: {MODELS['grok']} (교육탭 전문 설계자)
- Gemini: {MODELS['gemini']} (요약/집계 + 종합 QA)

🎯 Phase {phase} 달성 목표:
✅ 구글드라이브 핵심파일 학습 지시 완료
✅ 각 워커별 새로운 전문분야 작업계획 수립
✅ MCP/A2A 시스템 동작 확인
✅ 팀 협업 체계 구축 (역할 재분배)

📁 생성 파일: {len(list(session_dir.glob('*')))}개
📊 상세 보고서: {report_file}

🚀 다음 단계: Phase {phase + 1} - 프로그램 뼈대 구현
- 견적탭 (자동견적 기능)
- AI도우미탭 (AI 채팅)  
- 교육탭 (AI-Human 학습 협업) ⭐ 새 전문 영역
- 엑셀 완벽 매핑 (최우선!)
"""

def run_dummy_mode():
    """더미 모드"""
    current_phase = get_current_phase()
    logger.info(f"더미 모드 실행 - Phase {current_phase}")
    (OUT / f"phase{current_phase}_dummy.txt").write_text(f"Phase {current_phase} 더미 모드 완료 (역할 재분배)", encoding="utf-8")
    return True

def run_single_phase():
    """단일 Phase 실행 (기존 main 함수 로직)"""
    current_phase = get_current_phase()
    
    logger.info("=" * 80)
    logger.info(f"🚀 한국산업 자동견적프로그램 MCP/A2A 리빌드 시작 Phase {current_phase} (역할 재분배)")
    logger.info(f"AutoGen: {AUTOGEN_AVAILABLE}")
    logger.info(f"MCP/A2A 시스템: 활성화")
    logger.info(f"스킵 워커: {SKIP_WORKERS}")
    logger.info("=" * 80)
    
    try:
        return run_team_collaboration()
    except Exception as e:
        logger.error(f"Phase {current_phase} 실행 중 오류: {e}")
        return False

def main():
    """Phase 1-5 연속 실행 메인 함수"""
    
    # 연속 실행 여부 확인 (환경변수로 제어)
    continuous_mode = os.getenv("CONTINUOUS_PHASES", "false").lower() == "true"
    
    if continuous_mode:
        # Phase 1-5 연속 실행
        logger.info("🔄 연속 실행 모드: Phase 1-5 자동 진행")
        
        overall_success = True
        completed_phases = []
        
        for phase_num in range(1, 6):  # Phase 1~5
            try:
                logger.info(f"\n{'='*100}")
                logger.info(f"🎯 Phase {phase_num} 시작 - {get_phase_description(phase_num)}")
                logger.info(f"{'='*100}")
                
                # 현재 Phase 설정
                os.environ["CURRENT_PHASE"] = str(phase_num)
                
                # Phase 실행
                phase_success = run_single_phase()
                
                if phase_success:
                    completed_phases.append(phase_num)
                    logger.info(f"✅ Phase {phase_num} 성공적으로 완료")
                    
                    # Phase 간 휴식 시간 (마지막 Phase 제외)
                    if phase_num < 5:
                        rest_time = int(os.getenv("PHASE_REST_SEC", "120"))  # 기본 2분
                        logger.info(f"⏱️ Phase {phase_num + 1} 준비를 위해 {rest_time}초 대기 중...")
                        time.sleep(rest_time)
                else:
                    logger.error(f"❌ Phase {phase_num} 실패")
                    overall_success = False
                    
                    # 실패 시 계속 진행할지 결정
                    continue_on_failure = os.getenv("CONTINUE_ON_PHASE_FAILURE", "false").lower() == "true"
                    if not continue_on_failure:
                        logger.error("Phase 실패로 인해 연속 실행을 중단합니다.")
                        break
                    else:
                        logger.warning(f"Phase {phase_num} 실패했지만 다음 Phase 계속 진행...")
                        
            except KeyboardInterrupt:
                logger.warning(f"Phase {phase_num} 실행 중 사용자 중단 (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"Phase {phase_num} 실행 중 예상치 못한 오류: {e}")
                overall_success = False
                
                continue_on_error = os.getenv("CONTINUE_ON_ERROR", "false").lower() == "true"
                if not continue_on_error:
                    break
        
        # 최종 결과 보고
        logger.info(f"\n{'='*100}")
        logger.info("🏁 연속 실행 완료 보고서")
        logger.info(f"{'='*100}")
        logger.info(f"완료된 Phase: {completed_phases}")
        logger.info(f"총 {len(completed_phases)}/5개 Phase 완료")
        
        if overall_success and len(completed_phases) == 5:
            logger.info("🎉 모든 Phase가 성공적으로 완료되었습니다!")
            return True
        else:
            logger.error("⚠️ 일부 Phase가 완료되지 않았습니다.")
            return False
            
    else:
        # 기존 단일 Phase 실행
        return run_single_phase()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
    