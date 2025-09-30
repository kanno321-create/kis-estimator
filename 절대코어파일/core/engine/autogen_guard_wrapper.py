# -*- coding: utf-8 -*-
# ================================================================
# autogen_guard_wrapper.py - 한국산업 자동견적프로그램 Guard 시스템
# Windows CP949 완전 대응 및 설정값 직접 지정 버전
# ================================================================

import subprocess
import sys
import time
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Windows UTF-8 완전 강제 설정
if sys.platform == "win32":
    import codecs
    import locale
    
    # 환경변수 강제 설정
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    
    # stdout/stderr UTF-8 강제
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except:
        pass

# .env 파일 로드 함수 (혹시 모를 다른 스크립트 호환성을 위해 유지)
def load_env():
    env_path = Path('.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# 스크립트 시작 시 .env 파일 로드
load_env()

# 설정값
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True, parents=True)

# 환경변수에서 설정값 읽기 (Direct API 사용으로 인한 조정)
MAX_TURNS = 2000  # Direct API로 실제 AI 작업 수행하므로 더 많은 턴 허용
NO_PROGRESS_N = 8   # 실제 AI 응답이므로 더 많은 시도 허용
DEADLINE_SEC = 1800  # 30분 제한으로 확장 (실제 AI 작업 시간 고려)
RESPAWN_DELAY = 3   # 3초 대기

# 로그 파일 생성 주기 (분 단위)
LOG_INTERVAL_MINUTES = 10  # 10분에 1개 로그 파일
last_log_time = 0  # 마지막 로그 시간

# 콘솔 출력 주기 (초 단위)
CONSOLE_LOG_INTERVAL_SEC = 60  # 1분에 1번 콘솔 상태 출력
last_console_log_time = 0  # 마지막 콘솔 로그 시간

class GuardState:
    """Guard 상태 관리"""
    def __init__(self):
        self.turn = 0
        self.start = time.time()
        self.last_hash: Optional[str] = None
        self.no_progress_count = 0
        self.recent_lines: List[str] = []

    def elapsed(self) -> float:
        return time.time() - self.start

    def feed(self, text: str):
        # 안전한 텍스트 처리
        try:
            safe_text = str(text or "").encode('utf-8', errors='replace').decode('utf-8')
        except:
            safe_text = str(text or "")
            
        # MD5 해시로 동일 출력 감지
        h = hashlib.md5(safe_text.encode("utf-8", errors='replace')).hexdigest()
        if h == self.last_hash:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0
        self.last_hash = h
        self.turn += 1

        self.recent_lines.append(safe_text)
        if len(self.recent_lines) > 50:
            self.recent_lines = self.recent_lines[-50:]

    def should_stop(self) -> Optional[str]:
        """중단해야 하는지 확인"""
        if self.turn >= MAX_TURNS:
            return "max_turns"
        if self.elapsed() > DEADLINE_SEC:
            return "deadline"
        if self.no_progress_count >= NO_PROGRESS_N:
            return "no_progress"
        return None

def safe_print(msg: str):
    """안전한 출력 함수"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # 유니코드 문제시 ASCII로 대체
        safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
        print(safe_msg)
    except:
        print("[OUTPUT_ERROR]")

def terminate_process(proc: subprocess.Popen):
    """프로세스 안전 종료"""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
            return
        except:
            pass
        proc.kill()
    except:
        pass

def run_once() -> str:
    """autogen_team.py를 한 번 실행하고 결과 반환"""
    py = sys.executable or "python"
    target = str(ROOT / "autogen_team.py")

    # UTF-8 환경변수 설정
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        proc = subprocess.Popen(
            [py, "-X", "utf8", target],  # UTF-8 강제 옵션 추가
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',  # 인코딩 오류시 대체
            env=env
        )
    except Exception as e:
        safe_print(f"[ERROR] 실행 실패: {e}")
        return "child_spawn_error"

    state = GuardState()
    reason: Optional[str] = None

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                text = line.rstrip("\n")
                
                # 콘솔 출력 주기 제한 (1분마다만 출력)
                global last_console_log_time
                current_time = time.time()
                should_print = (current_time - last_console_log_time) >= CONSOLE_LOG_INTERVAL_SEC
                
                if should_print:
                    safe_print(text)
                    last_console_log_time = current_time
                
                state.feed(text)

                reason = state.should_stop()
                if reason:
                    safe_print(f"\n[STOP] 중단 사유: {reason}")
                    break
            except Exception as e:
                if should_print:
                    safe_print(f"[LINE_ERROR] {e}")
                continue

        # 자식 프로세스 상태 확인
        ret = proc.poll()
        if ret not in (None, 0) and reason is None:
            reason = "child_exit_nonzero"

    except KeyboardInterrupt:
        reason = "user_break"
        safe_print("\n[STOP] 사용자 중단")
    except Exception as e:
        reason = "child_exit_nonzero"
        safe_print(f"\n[ERROR] 실행 중 오류: {e}")
    finally:
        terminate_process(proc)

    # 로그 저장 (5분 간격으로만)
    global last_log_time
    current_time = time.time()
    
    # Phase 완료나 종료시에만 로그 저장 (10분 간격으로 제한)
    should_log = (
        reason in ["user_break", "normal_exit", "deadline", "max_turns"] or
        (current_time - last_log_time) >= (LOG_INTERVAL_MINUTES * 60)
    )
    
    if should_log:
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_data = f"""실행 결과: {reason or 'normal_exit'}
턴 수: {state.turn}
경과 시간: {state.elapsed():.2f}초
타임스탬프: {timestamp}
최근 출력: {len(state.recent_lines)}줄
"""
            
            log_file = OUT / f"guard_log_{timestamp}.txt"
            log_file.write_text(log_data, encoding='utf-8', errors='replace')
            last_log_time = current_time
        except Exception as e:
            safe_print(f"[LOG_ERROR] {e}")

    return reason or "normal_exit"

def main():
    """메인 실행 루프"""
    safe_print("[GUARD] 한국산업 Guard 시스템 시작")
    safe_print(f"   최대 턴: {MAX_TURNS}")
    safe_print(f"   무응답 제한: {NO_PROGRESS_N}")
    safe_print(f"   시간 제한: {DEADLINE_SEC}초")
    safe_print(f"   재시작 대기: {RESPAWN_DELAY}초")
    safe_print("=" * 50)

    run_count = 0
    # continuous_mode 와 상관없이 Guard는 항상 재시작 대기
    while True:
        run_count += 1
        start_time = time.time()
        
        current_time = datetime.now().strftime('%H:%M:%S')
        safe_print(f"\n[RUN] 실행 #{run_count} 시작 - {current_time}")
        
        reason = run_once()
        elapsed = round(time.time() - start_time, 1)
        
        safe_print(f"\n[RESULT] 실행 완료: {reason} (경과: {elapsed}초)")
        
        if reason == "user_break":
            safe_print("[EXIT] 사용자 요청으로 종료")
            break

        # .env 파일에서 연속 실행 여부 확인
        continuous_mode = os.getenv("CONTINUOUS_PHASES", "false").lower() == "true"
        if not continuous_mode:
            safe_print("[EXIT] 단일 Phase 모드 완료. 연속 실행이 비활성화되어 종료합니다.")
            break
        
        safe_print(f"[WAIT] {RESPAWN_DELAY}초 후 다음 Phase 재시작...")
        time.sleep(RESPAWN_DELAY)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print("\n[EXIT] Guard 시스템 종료")
    except Exception as e:
        safe_print(f"\n[ERROR] Guard 시스템 오류: {e}")