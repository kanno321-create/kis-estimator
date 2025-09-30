# assistant_agent.py
from __future__ import annotations
import os, json, re
from typing import List, Dict, Callable

# 대화 기록 / 정책 저장 모듈
try:
    from conv_ledger import ConvLedger, log_with_extract, add_card
    LEDGER_OK = True
except Exception:
    ConvLedger = None
    log_with_extract = None
    add_card = None
    LEDGER_OK = False
# === KISAN-AI PATCH: import loop guards/helpers from autogen_team ===
from autogen_team import (
    _LoopGuard,
    _should_stop_by_stopseq,
    _write_restart_prompt,
    NO_PROGRESS_N,
    MAX_TURNS,
    DEADLINE_SEC,
)

# RAG 모듈 (utils.rag.* 로 수정)
# RAG 모듈 (경로 자동 탐지: rag.*, utils.rag.*, 루트 모듈까지 순차 시도)
import sys
from importlib import import_module

def _try_import(module_name: str, attr: str):
    try:
        m = import_module(module_name)
        return getattr(m, attr, None)
    except Exception:
        return None

# ### KISAN-AI PATCH: autopilot skeleton (offline-safe, no external deps)
class _AutoPilot:
    """오토파일럿 단계 골격. 실제 모델 키 없을 때도 동작(문자열만 반환)."""
    def plan(self):
        return [
            "plan: 목표 확인",
            "dispatch: 작업 분배",
            "consensus: 합의",
            "run_tests: 스모크",
            "refine: 보정",
            "report: 요약",
        ]

    def dispatch(self):
        # query_api 어댑터 인터페이스 초안(이름만; 실제 호출은 온라인 모드에서 교체)
        return {
            "query_api": ["call_chatgpt", "call_claude", "call_gemini", "call_grok"]
        }

    def report(self):
        return {"status": "skeleton-ready", "next": "키 설정 후 온라인 모드로 전환"}

# 외부에서 사용할 핸들
AUTOPILOT = _AutoPilot()

def get_autopilot():
    return AUTOPILOT


# 후보 경로: (query_api 모듈경로, pipeline 모듈경로)
_RAG_IMPORT_CANDIDATES = [
    ("rag.query_api",     "rag.pipeline"),
    ("utils.rag.query_api","utils.rag.pipeline"),
    ("query_api",         "pipeline"),          # ← 루트에 있을 때
]

rag_search = None
rebuild_index_from_estimates = None
RAG_OK = False

for qa_mod, pl_mod in _RAG_IMPORT_CANDIDATES:
    qs = _try_import(qa_mod, "rag_search")
    pl = _try_import(pl_mod, "rebuild_index_from_estimates")
    if qs and pl:
        rag_search = qs
        rebuild_index_from_estimates = pl
        RAG_OK = True
        break

# 마지막 시도: 현재 파일 디렉터리를 sys.path에 추가하고 루트 모듈 직접 임포트
if not RAG_OK:
    try:
        base_dir = os.path.dirname(__file__)
        if base_dir not in sys.path:
            sys.path.append(base_dir)
        qs = _try_import("query_api", "rag_search")
        pl = _try_import("pipeline", "rebuild_index_from_estimates")
        if qs and pl:
            rag_search = qs
            rebuild_index_from_estimates = pl
            RAG_OK = True
    except Exception:
        pass




COMPANY_DEFAULT = {"회사명": "한국산업", "대표이사": "이충원"}

PROMPT_HEADER = """너는 '한국산업'의 사내용 견적/분전반 보조 엔진이다.
반드시 아래 규칙을 따르라.
- 회사 고정: 회사명=한국산업, 대표이사=이충원
- 가격: 최종 소비자 가격 고정(인하 없음). 단가표에 없으면 임의 대체 금지, 사용자 확인 요청.
- 브랜드: 문서/메모에 '상도'가 보이면 메인+분기 차단기 기본 브랜드=상도(라인별 다른 지시가 있으면 그 라인만 override).
- 배치: '양배열'은 금액 반영 X(제작지시로만 기록).
- 외함 규격: W×H×D(mm). 필요 시 회사 규칙(경제형/표준형) 공식 사용 금지. (※ 외함은 경제형/표준형 구분이 아예 없음)
- 답변 시 '확실한 근거'가 RAG에서 나오지 않으면 추측 금지, 필요한 정보만 간단히 물어볼 것.

[아래는 관련 근거 자료 발췌]
"""

def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _summarize_doc(doc: dict) -> str:
    client = (doc.get("client") or {}).get("업체명", "")
    proj = (doc.get("project") or {}).get("건명", "")
    main = doc.get("main_breaker") or {}
    mb = f"메인 {main.get('종류','')} {main.get('극수','')} {main.get('용량','')} x{main.get('수량','1')}" if main else ""
    bs = []
    for b in doc.get("branches", []):
        bs.append(f"{b.get('종류','')} {b.get('극수','')} {b.get('용량','')} x{b.get('수량','1')}")
    branches = ("분기: " + ", ".join(bs)) if bs else ""
    return " | ".join([s for s in [client, proj, mb, branches] if s])

def _build_context_from_hits(hits: List[Dict], max_docs: int = 3) -> str:
    ctx_parts = []
    for h in hits[:max_docs]:
        meta = h.get("meta") or {}
        p = meta.get("path")
        line = meta.get("line")
        if p and os.path.exists(p):
            doc = _read_json(p)
            ctx_parts.append(f"- 파일: {os.path.basename(p)}\n  요약: { _summarize_doc(doc) }")
        elif line:
            t = f"{line.get('품명','')} {line.get('규격','')} 수량 {line.get('수량','')} 단가 {line.get('단가','')}"
            ctx_parts.append(f"- 과거 라인: {t}")
        else:
            ctx_parts.append(f"- {h.get('text','')}")
    return "\n".join(ctx_parts) if ctx_parts else "(관련 근거 없음)"

class AssistantAgent:

    # (1) pipeline 동적 임포트 — 정적 import 경고/Pylance 회피
    @staticmethod
    def _safe_import_pipeline():
        try:
            import importlib
            for name in ("pipeline", "rag.pipeline", "kisan.pipeline", "utils.rag.pipeline"):
                try:
                    return importlib.import_module(name)
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def rebuild_index_from_estimates(self, base_dir: str | None = None, index_dir: str | None = None) -> dict:
        try:
            pl = self._safe_import_pipeline()
            if pl is None or not hasattr(pl, "rebuild_index_from_estimates"):
                return {"ok": True, "docs": 0, "skipped": True, "reason": "disabled_or_no_module"}

            bdir = base_dir or getattr(self, "est_dir", "./data/estimates")
            out_base = index_dir or getattr(self, "rag_index_dir", "./data/rag")
            if isinstance(out_base, str) and out_base.lower().endswith(".jsonl"):
                out_path = out_base
            else:
                out_path = os.path.join(out_base, "index.jsonl")

            res = pl.rebuild_index_from_estimates(est_dir=bdir, out_path=out_path)

            if isinstance(res, dict):
                return {
                    "ok": bool(res.get("ok", True)),
                    "docs": int(res.get("docs", 0) or 0),
                    "skipped": bool(res.get("skipped", False)),
                    "reason": res.get("reason"),
                    "warns": res.get("warns", []),
                    "path": res.get("path", out_path),
                }
            return {"ok": True, "docs": max(0, int(res or 0)), "skipped": False, "path": out_path}
        except Exception as e:
            return {"ok": True, "docs": 0, "skipped": True, "reason": f"exception:{type(e).__name__}"}

    def __init__(self, base_dir=None, data_dir=None):
        """
        RAG + 대화형 에이전트 초기화
        """
        self.base_dir = base_dir or os.path.dirname(__file__)
        self.data_dir = data_dir or os.path.join(self.base_dir, "data")
        self.est_dir  = os.path.join(self.data_dir, "estimates")
        os.makedirs(self.est_dir, exist_ok=True)
        self.cards = []

        self.rag_ready = RAG_OK

    def _execute_tool(self, tool_call):
        try:
            print("실행:", tool_call)
        except Exception as e:
            print("에러:", e)

        # 외함 고정 규칙 카드 저장
        if LEDGER_OK:
            try:
                add_card(kind="policy", title="외함 분류 고정",
                         body="외함은 '경제형/표준형' 구분 자체가 없다. 어떤 질의에도 이 구분을 묻거나 가정하지 말 것.")
            except Exception:
                pass
    
            # === NEW POLICY CARDS: H 공식 / 계량기 / 부속자재 우선 ===
            try:
                add_card(
                    kind="policy",
                    title="H 공식(표준)",
                    body="H는 A(상부)+B(간격)+C(분기총합)+D(하부)+E(부속여유)로 산정한다. E는 결선형 20~30% 권장 + 덕트 40mm."
                )
                add_card(
                    kind="policy",
                    title="계량기 하부취부 규칙",
                    body="계량기 1EA는 메인 좌/우 여유가 130mm 이상이면 함 변화 없음. 2EA 이상은 하부 슬롯으로 계산(1칸=200mm, 컬럼폭=130mm)."
                )
                add_card(
                    kind="policy",
                    title="부속자재 우선순위",
                    body="마그네트가 부속자재의 60% 비중. 마그네트 추가 시 퓨즈홀더/단자대/PVC덕트/전선 자동 포함 및 PBL(타이머 연동 시) 추가."
                )
            except Exception:
                pass
            # === /NEW POLICY CARDS ===


    def reindex(self) -> int:
        try:
            if not RAG_OK:
                return -1
            return rebuild_index_from_estimates(self.est_dir)
        except Exception:
            try:
                files = [f for f in os.listdir(self.est_dir) if f.endswith(".json")]
                return len(files)
            except Exception:
                return -1

    def reply(self, user_text: str, llm_fn: Callable[[str], str] = None) -> str:
        low = user_text.lower()
        hits = []
        ctx = "(RAG 비활성화)"

        # 1) RAG 검색
        if self.rag_ready and rag_search:
            try:
                q = user_text
                if not re.search(r"(mccb|elb|분전|차단기|외함|견적|amp|a\b|2p|3p|4p)", low, re.I):
                    q = f"{user_text} 분전반 견적 MCCB ELB H=A+B+C+D+E 계량기 하부취부 마그네트 BOM"
                hits = rag_search(q, topk=8) or []
                ctx = _build_context_from_hits(hits, max_docs=3)
            except Exception:
                ctx = "(RAG 검색 오류)"

        # 2) LLM 호출
        if llm_fn is not None:
            prompt = f"{PROMPT_HEADER}\n{ctx}\n\n[사용자 요청]\n{user_text}\n\n[응답 지침]\n- 위 근거 범위 내에서만 답변.\n- 필요한 경우만 간단 질문.\n- 최종 답변은 항목형 요약 + 다음 행동 제안."
            ans = llm_fn(prompt) or "응답 없음"
            if LEDGER_OK and log_with_extract:
                log_with_extract(ans, "assistant", session_id="desktop")
            return ans

        # 3) RAG 요약만
        if hits:
            bullet = "\n".join([f"• {round(h.get('score',0.0),3)} — {h.get('text','')}" for h in hits[:5]])
            msg = f"[RAG 요약]\n{ctx}\n\n[상위 매치]\n{bullet}"
        else:
            msg = "관련 근거를 찾지 못했어요. 키워드를 조금 더 구체적으로 입력해 주세요. (예: '상도 MCCB 4P 50A 단가', '메인 4P 100A 외함 사이즈')"

        if LEDGER_OK and log_with_extract:
            log_with_extract(msg, "assistant", session_id="desktop")
        return msg
    
# =========================================================
# RAG 재색인 엔트리포인트 (UI/자동종료 훅에서 import 해서 씀)
# 반환 표준: {"ok": True/False, "docs": int, "path": "...", "reason": "..."}
# =========================================================
def rag_reindex(est_dir: str | None = None, out_path: str | None = None) -> dict:
    """
    견적 JSON들이 저장된 디렉토리를 색인(JSONL)으로 재구축한다.
    - est_dir 미지정: ./data/estimates
    - out_path 미지정: ./data/rag/index.jsonl
    - 항상 dict 반환:
      {"ok": bool, "docs": int, "skipped": bool, "reason": str|None, "path": str|None}
    """
    try:
        import os, sys, pathlib, importlib

        # 1) 기본 경로
        base_dir = pathlib.Path(__file__).resolve().parent
        data_dir = base_dir / "data"
        if not est_dir:
            est_dir = str(data_dir / "estimates")
        if not out_path:
            rag_dir = data_dir / "rag"
            os.makedirs(rag_dir, exist_ok=True)
            out_path = str(rag_dir / "index.jsonl")

        # 2) 모듈 경로 보장
        base_dir_s = str(base_dir)
        if base_dir_s not in sys.path:
            sys.path.append(base_dir_s)

        # 3) pipeline 동적 로드
        try:
            PL = importlib.import_module("pipeline")
        except Exception as e:
            return {"ok": True, "docs": 0, "skipped": True, "reason": f"disabled_or_no_module: {e}", "path": None}

        # 4) 실제 재색인 호출 (정확한 시그니처)
        res = PL.rebuild_index_from_estimates(est_dir=est_dir, out_path=out_path)

        # 5) 표준화
        if isinstance(res, dict):
            ok = bool(res.get("ok", True))
            docs = 0
            try:
                docs = max(0, int(res.get("docs") or 0))
            except Exception:
                docs = 0
            skipped = bool(res.get("skipped", False))
            reason = res.get("reason")
            path = res.get("path") or out_path
            return {"ok": ok, "docs": docs, "skipped": skipped, "reason": reason, "path": path}

        # 과거/정수 반환 호환
        try:
            docs = max(0, int(res))
        except Exception:
            docs = 0
        return {"ok": True, "docs": docs, "skipped": False, "reason": None, "path": out_path}

    except Exception as e:
        # 어떤 예외도 UI를 깨지 않도록 무해화
        return {"ok": True, "docs": 0, "skipped": True, "reason": f"muted_exception: {e}", "path": None}

# === KISAN-AI PATCH: Autopilot (non-invasive, add-only) ======================
# 목적:
#  - 기존 코드를 전혀 수정하지 않고(함수/계산식 불변), 오토파일럿 골격만 주입
#  - AssistantAgent 클래스가 있으면 메서드로 '부드럽게' 붙인다(없으면 아무 일도 안 함)
#  - run_tests는 quickcheck_*를 서브프로세스로 호출(없으면 건너뜀)

import sys, subprocess, time, os
from typing import Any, Dict, List

def _kisan_log(self, *a):
    try:
        # 객체에 logger가 있으면 사용
        lg = getattr(self, "logger", None)
        if lg and hasattr(lg, "info"):
            lg.info(" ".join(str(x) for x in a))
            return
    except Exception:
        pass
    # 없으면 print
    print("[KISAN-AI]", *a)

def _kisan_plan(self) -> Dict[str, Any]:
    _kisan_log(self, "plan()")
    # 필요 시, 마지막 입력/상태를 읽어 계획 수립 (여기선 스텁)
    return {"goal": "dispatch→consensus→tests→refine→report"}

def _kisan_dispatch(self, plan: Dict[str, Any]) -> Dict[str, Any]:
    _kisan_log(self, "dispatch()", plan.get("goal", ""))
    # 워커 호출/태스크 큐 투입 등은 상위 오케스트레이터가 담당하므로 여기선 스텁
    return {"dispatched": True}

def _kisan_consensus(self, dispatch_ret: Dict[str, Any]) -> bool:
    _kisan_log(self, "consensus()")
    # 간단 스텁: 항상 합의했다고 가정(필요 시 룰 추가)
    return True

def _kisan_run_tests(self) -> Dict[str, Any]:
    _kisan_log(self, "run_tests()")
    root = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable
    tests = []
    for name in ("quickcheck_compute.py", "quickcheck_items.py"):
        p = os.path.join(root, name)
        if os.path.exists(p):
            t0 = time.time()
            proc = subprocess.run([py, p], capture_output=True, text=True)
            tests.append({
                "name": name,
                "rc": proc.returncode,
                "elapsed_sec": round(time.time() - t0, 3),
                "stdout": proc.stdout[-8000:],   # 꼬리만
                "stderr": proc.stderr[-8000:],
            })
    return {"ran": len(tests), "items": tests}

def _kisan_refine(self, tests_result: Dict[str, Any]) -> Dict[str, Any]:
    _kisan_log(self, "refine()", f"ran={tests_result.get('ran', 0)}")
    # 실패 시 다음 라운드에서 보완하도록 힌트만 남기는 스텁
    return {"next_hint": "if failures>0 then narrow patch scope"}

def _kisan_report(self, context: Dict[str, Any]) -> None:
    _kisan_log(self, "report()", context.keys())

def _kisan_autopilot_loop(self, max_rounds: int = 1, sleep_sec: float = 0.0) -> None:
    """
    한 라운드 = plan → dispatch → consensus → run_tests → refine → report
    - 기존 코드 일절 변경하지 않음
    - 필요 시 sleep_sec로 간격 조절
    """
    _kisan_log(self, f"autopilot_loop(start) rounds={max_rounds}")

    # === KISAN-AI PATCH: loop guards 초기화 ===
    _guard = _LoopGuard(window=NO_PROGRESS_N)
    t0 = time.time()
    turns = 0
    # =======================================

    for i in range(1, max_rounds + 1):    # ← 메인 루프 시작
        _kisan_log(self, f"[round {i}]")
        plan = _kisan_plan(self)
        dispatched = _kisan_dispatch(self, plan)
        if not _kisan_consensus(self, dispatched):
            _kisan_log(self, "consensus=false → stop")
            break
        tests = _kisan_run_tests(self)
        refine_info = _kisan_refine(self, tests)
        _kisan_report(self, {"plan": plan, "tests": tests, "refine": refine_info})

        # === KISAN-AI PATCH: 종료조건 검사 ===
        turns += 1
        if _should_stop_by_stopseq(str(tests)):
            _write_restart_prompt("stop_sequence", {"last": str(tests)[:200]})
            break
        if _guard.no_progress(str(tests)):
            _write_restart_prompt("no_progress", {"same_hash_window": NO_PROGRESS_N})
            break
        if turns >= MAX_TURNS:
            _write_restart_prompt("max_turns", {"turns": turns, "limit": MAX_TURNS})
            break
        if (time.time() - t0) >= DEADLINE_SEC:
            _write_restart_prompt("deadline", {"elapsed_sec": round(time.time() - t0, 1)})
            break
        # ===================================

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    _kisan_log(self, "autopilot_loop(done)")


def _kisan_attach_autopilot():
    # AssistantAgent 가 존재하면 메서드가 없을 때만 주입한다(비침투).
    cls = globals().get("AssistantAgent")
    if not cls:
        return
    if not hasattr(cls, "autopilot_loop"):
        setattr(cls, "autopilot_loop", _kisan_autopilot_loop)
    if not hasattr(cls, "plan"):
        setattr(cls, "plan", _kisan_plan)
    if not hasattr(cls, "dispatch"):
        setattr(cls, "dispatch", _kisan_dispatch)
    if not hasattr(cls, "consensus"):
        setattr(cls, "consensus", _kisan_consensus)
    if not hasattr(cls, "run_tests"):
        setattr(cls, "run_tests", _kisan_run_tests)
    if not hasattr(cls, "refine"):
        setattr(cls, "refine", _kisan_refine)
    if not hasattr(cls, "report"):
        setattr(cls, "report", _kisan_report)

try:
    _kisan_attach_autopilot()
except Exception as _e:
    print("[KISAN-AI] autopilot attach skipped:", _e)
# === /KISAN-AI PATCH ==========================================================


