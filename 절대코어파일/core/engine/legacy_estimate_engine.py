# estimate_engine.py
# (유지) 배치/외함 알고리즘 + 최소 프레임 매핑(60AF 포함)
# (유지) 2P 15/20/30A ELB는 SIE-32/32GRHS 고정 / 개당 높이 40mm
# (수정) 외함 H = ceil_100(A + B + C - 100)
# (수정) W = 메인/분기 중 가장 높은 스펙을 기준으로 결정

import math
from estimate_policy import load_policies
import json
from typing import TypedDict, Optional, Dict, Any, Mapping

# === [TRACE STORE] 엔진 계산 설명 저장/조회 유틸 (계산식/정책 변경 없음) ===
_LAST_EXPLAIN = None

def set_last_explain(d):
    """엔진 계산 설명을 저장. dict만 저장하고, 기본 골격을 채워 둔다."""
    global _LAST_EXPLAIN
    base = {
        "A_top": None,
        "B_gap": None,
        "C_branch_total": None,
        "D_bottom": None,
        "E_accessory": None,
        "policy": ""
    }
    try:
        if isinstance(d, dict):
            out = dict(base)
            out.update(d)
            _LAST_EXPLAIN = out
        else:
            _LAST_EXPLAIN = dict(base)
    except Exception:
        _LAST_EXPLAIN = dict(base)

def get_last_explain():
    """최근 계산 설명을 조회."""
    return _LAST_EXPLAIN
# === [/TRACE STORE] ===

# === Pricing constants (BUS-BAR) ===
MAIN_BUSBAR_UNIT_PRICE   = 20000   # 메인 BUS-BAR kg당 단가
BRANCH_BUSBAR_UNIT_PRICE = 20000   # 분기 BUS-BAR kg당 단가

# -------------------------
# 유틸
# -------------------------
def ceil_to_base(x, base):
    return int(math.ceil(x / base) * base)

def round_to_2(x):
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0

def parse_int_amp(a_text):
    try:
        return int(str(a_text).replace("A", "").strip())
    except:
        return 0

# -------------------------
# BUS-BAR / MAIN BUS-BAR 계수 함수
# -------------------------

def main_busbar_kg_factor(main_amp: int) -> float:
    """MAIN BUS-BAR KG 계수 반환"""
    if 20 <= main_amp <= 250:
        return 0.000007
    elif 300 <= main_amp <= 400:
        return 0.000013
    elif 500 <= main_amp <= 800:
        return 0.000015
    return 0.0

def branch_busbar_kg_factor(main_amp: int) -> float:
    """BUS-BAR KG 계수 반환"""
    if 20 <= main_amp <= 250:
        return 0.0000045
    elif 300 <= main_amp <= 400:
        return 0.000007
    elif 500 <= main_amp <= 800:
        return 0.000009
    return 0.0

def busbar_spec_by_main_amp(main_amp: int) -> str:
    """용량에 따른 BUS-BAR 규격 문자열"""
    if main_amp <= 100:
        return "3T*15"
    elif main_amp <= 250:
        return "5T*20"
    elif main_amp <= 400:
        return "6T*30"
    else:
        return "8T*40"

# === BUS-BAR 규격: 분기용 ===
def busbar_spec_by_branch_amp(amp: int) -> str:
    """
    분기차단기 용량(A)에 따른 BUS-BAR 규격
    정책: <=100A: 3T*15 / <=250A: 5T*20 / <=400A: 6T*30 / 그 이상: 8T*40
    """
    if amp <= 100:
        return "3T*15"
    elif amp <= 250:
        return "5T*20"
    elif amp <= 400:
        return "6T*30"
    else:
        return "8T*40"

# -------------------------
# 프레임별 극 길이(mm)
# -------------------------
POLE_LEN_BY_AF = {
    "30AF": 25,
    "50AF": 25,
    "60AF": 25,
    "100AF": 25,
    "125AF": 30,
    "200AF": 33,
    "250AF": 33,
    "400AF": 50,
    "600AF": 70,
    "800AF": 70,
}

# -------------------------
# 메인 상부 전선 공간 A(mm)
# -------------------------
MAIN_TOP_CLEARANCE = {
    "30AF": 130,
    "50AF": 130,
    "60AF": 130,
    "100AF": 170,
    "125AF": 170,
    "200AF": 200,
    "250AF": 200,
    "400AF": 400,
    "600AF": 500,
    "800AF": 600,
}

# -------------------------
# 메인차단기 높이 B(mm)
# -------------------------
MAIN_BODY_HEIGHT = {
    "30AF": 120,
    "50AF": 120,
    "60AF": 120,
    "100AF": 120,
    "125AF": 140,
    "200AF": 160,
    "250AF": 160,
    "400AF": 220,
    "600AF": 280,
    "800AF": 280,
}

# -------------------------
# 용량(A) → 최소 프레임(비용 최소)
# -------------------------
def map_amp_to_af(amp: int, style: str = "경제형") -> str:
    if amp <= 30:  return "30AF"
    if amp <= 50:  return "50AF"
    if amp == 60:  return "60AF"
    if amp <= 100: return "100AF"
    if amp == 125: return "125AF"
    if 150 <= amp <= 200: return "200AF"
    if amp == 225: return "250AF"
    if amp == 250: return "250AF"  # 특례 존재하지만 기본 250
    if 300 <= amp <= 400: return "400AF"
    if 500 <= amp <= 600: return "600AF"
    return "800AF"

# -------------------------
# 마주보기 가능 규칙
# -------------------------
def can_face_by_frame(af_left: str, af_right: str) -> bool:
    if af_left == af_right:
        return True
    small = {"50AF", "60AF", "100AF"}
    mid   = {"200AF", "250AF"}
    if af_left in small and af_right in small: return True
    if af_left in mid   and af_right in mid:   return True
    return False

# 30AF 2P ELB(15/20/30A)는 일괄 40mm 규칙
def is_small_30_elb(kind: str, poles_text: str, amp: int, af: str) -> bool:
    return (af == "30AF"
            and poles_text == "2P"
            and (kind == "ELB" or kind.startswith("ELB"))
            and amp in (15, 20, 30))

def unit_row_height(poles: int, af: str, kind: str, poles_text: str, amp: int) -> int:
    # 30AF 2P ELB 한 개 높이 40mm
    if is_small_30_elb(kind, poles_text, amp, af):
        return 40
    L = POLE_LEN_BY_AF.get(af, 25)
    if poles == 4:
        return 4 * L
    return poles * L

def row_height_for_pair(u, v) -> int:
    """
    u/v: {"poles","af","kind","poles_text","amp"}
    - 4P-4P: N상 불일치 → 5L
    - 나머지: 각 유닛 row 높이의 max
      (30AF 2P ELB끼리면 40mm가 유지됨)
    """
    Lu = POLE_LEN_BY_AF.get(u["af"], 25)
    Lv = POLE_LEN_BY_AF.get(v["af"], 25)
    if u["poles"] == 4 and v["poles"] == 4:
        return 5 * max(Lu, Lv)

    hu = unit_row_height(u["poles"], u["af"], u["kind"], u["poles_text"], u["amp"])
    hv = unit_row_height(v["poles"], v["af"], v["kind"], v["poles_text"], v["amp"])
    return max(hu, hv)

# -------------------------
# 분기 총 높이 C 계산
# -------------------------
def expand_branch_units(branches, style="경제형"):
    units = []
    for b in branches:
        qty = int(b.get("수량") or "0")
        if qty <= 0: continue
        amp = parse_int_amp(b["용량"])
        af  = map_amp_to_af(amp, style)
        poles_text = b["극수"]
        poles = int(poles_text.replace("P", ""))
        for _ in range(qty):
            units.append({
                "kind": b["종류"], "poles": poles, "amp": amp, "af": af, "poles_text": poles_text
            })
    return units

# === NEW: 분기 요약 → branches 리스트 생성 유틸 ===
import re
from collections import defaultdict

def build_branches(items):
    """
    items: [("MCCB","4P","50A",3), ("ELB","2P","20A",4), ...]
    반환: [{"종류":"MCCB","극수":"4P","용량":"50A","수량":3}, ...]
    같은 항목은 자동 합산.
    """
    acc = defaultdict(int)
    norm = lambda s: str(s).strip().upper()
    for kind, poles, amp, cnt in items:
        k = (norm(kind or "MCCB"), norm(poles), f"{int(re.sub('[^0-9]', '', str(amp)))}A")
        acc[k] += int(cnt)
    out = []
    for (kind, poles, amp), qty in acc.items():
        if qty <= 0: 
            continue
        out.append({"종류": kind, "극수": poles, "용량": amp, "수량": qty})
    return out

def parse_branch_summary(text: str, default_kind: str = "MCCB"):
    """
    한국어/영문 섞인 요약 문자열을 파싱하여 branches 리스트로 변환.
    허용 예시:
      - "MCCB 4P 50A x 3, ELB 2P 20A x 4"
      - "3P 30A * 2, 2P 20A 4개"           (종류 생략 시 default_kind 사용)
      - "ELB 4P 50A 3" / "ELB 4P 50A 3EA" / "ELB 4P 50A×3"
    반환: build_branches([...])와 동일 구조
    """
    if not text or not str(text).strip():
        return []
    s = text.replace("×", "x").replace("X", "x").replace("*", "x")
    # 쉼표/줄바꿈 기준으로 토큰 분리
    tokens = re.split(r"[,\n;/]+", s)
    items = []
    pat = re.compile(
        r"""(?ix)                             # ignorecase, verbose
        (?:(MCCB|ELB|ELCB|MCB|차단기)\s*)?    # 종류 (옵션, 없으면 default_kind)
        ([234]\s*P)\s*                        # 극수: 2P/3P/4P
        (\d+)\s*A\s*                          # 용량: 숫자A
        (?:x\s*|\s+)?                         # 곱하기 기호 또는 공백
        (\d+)?\s*(?:EA|개)?\s*$               # 수량(옵션, 없으면 1)
        """
    )
    for raw in tokens:
        raw = raw.strip()
        if not raw:
            continue
        m = pat.match(raw)
        if not m:
            # 형태가 다르면 스킵 (필요시 엄격 → 예외)
            continue
        kind, poles, amp, qty = m.groups()
        kind = (kind or default_kind).upper()
        # 일부 약어 정규화
        if kind in {"ELCB"}:
            kind = "ELB"
        if kind in {"MCB","차단기"}:
            kind = default_kind.upper()
        poles = re.sub(r"\s+", "", poles.upper())  # "4 P" → "4P"
        amp = f"{int(amp)}A"
        qty = int(qty) if qty and qty.isdigit() else 1
        items.append((kind, poles, amp, qty))
    return build_branches(items)
# === /NEW ===


def sort_units_for_layout(units):
    af_order = {"30AF":0, "50AF":1, "60AF":1, "100AF":1,
                "125AF":2, "200AF":3, "250AF":3, "400AF":4, "600AF":5, "800AF":6}
    return sorted(units, key=lambda u: (af_order.get(u["af"], 9), -u["poles"], -u["amp"]))

def compute_branch_total_height(branches, style="경제형") -> int:
    units = expand_branch_units(branches, style)
    if not units: return 0
    units = sort_units_for_layout(units)
    used  = [False]*len(units)
    total = 0
    for i, u in enumerate(units):
        if used[i]: continue
        partner = -1
        best_h = None
        for j in range(i+1, len(units)):
            if used[j]: continue
            v = units[j]
            if not can_face_by_frame(u["af"], v["af"]): continue
            rh = row_height_for_pair(u, v)
            if best_h is None or rh < best_h:
                best_h = rh
                partner = j
                # 동일 프레임/극수면 바로 확정
                if (u["af"] == v["af"] and u["poles"] == v["poles"]):
                    break
        if partner >= 0:
            total += best_h
            used[i] = used[partner] = True
        else:
            # 단독행
            total += unit_row_height(u["poles"], u["af"], u["kind"], u["poles_text"], u["amp"])
            used[i] = True
    return int(total)

# -------------------------
# 외함 W/H/D 계산 규칙
#  - W: 메인과 분기 중 "가장 높은 스펙" 기준으로 아래 테이블 적용
#  - D: 기존 규칙 유지
#  - H: ceil_100(A + B + C - 100)
# -------------------------

def max_branch_class(branches, style="경제형"):
    """
    branches 내 최고 스펙 클래스 반환
      return 값: "none" | "30" | "50_60_100" | "125" | "200_250" | "400" | "600_800"
    """
    units = expand_branch_units(branches, style)
    rank = "none"
    def up(x):
        order = ["none","30","50_60_100","125","200_250","400","600_800"]
        return order[max(order.index(rank), order.index(x))]
    for u in units:
        af = u["af"]
        if af == "30AF":         rank = up("30")
        elif af in {"50AF","60AF","100AF"}: rank = up("50_60_100")
        elif af == "125AF":      rank = up("125")
        elif af in {"200AF","250AF"}: rank = up("200_250")
        elif af == "400AF":      rank = up("400")
        elif af in {"600AF","800AF"}: rank = up("600_800")
    return rank

def width_from_max_spec(main_poles:int, main_af:str, branches, style="경제형") -> int:
    """
    요구: W를 '분기 중 가장 높은 스펙'을 우선 반영.
    규칙:
      - 특례) 메인 2P 50AF + 분기 전부 2P 30AF → 400
      - 3P/4P 계열은 최고 스펙에 따라:
         최고=30            → 500
         최고=50/60/100     → 600
         최고=125           → 700
         최고=200/250       → 800  (단, 메인이 400AF면 900)
         최고=400           → 900~1300 (메인 600/800이면 1300, 그 외 900)
         최고=600/800       → 1000~1300 (기본 1000, 400 분기 있으면 1300)
    """
    # 특례 체크
    units = expand_branch_units(branches, style)
    if not units:
        return 500 if main_poles == 2 else 600

    only_2p30 = all(u["af"]=="30AF" and u["poles"]==2 for u in units)
    if main_poles == 2 and main_af == "50AF" and only_2p30:
        return 400

    top = max_branch_class(branches, style)

    if main_poles in (3,4):
        if top == "30":            return 500
        if top == "50_60_100":     return 600
        if top == "125":           return 700
        if top == "200_250":
            return 900 if main_af == "400AF" else 800
        if top == "400":
            if main_af in {"600AF","800AF"}: return 1300
            return 900
        if top == "600_800":
            # 고스펙 분기가 있으면 넓게
            if any(u["af"]=="400AF" for u in units):
                return 1300
            return 1000
    # 기본값
    return 800 if main_poles in (3,4) else 600

def compute_enclosure_D(main_af: str, branch_count: int, main_amp: int):
    if main_af in {"50AF","60AF","100AF","125AF","200AF"}:
        return 200 if main_amp >= 225 else 150
    if main_af == "250AF": return 200
    if main_af == "400AF": return 250
    if main_af == "600AF": return 400 if branch_count >= 25 else 350
    if main_af == "800AF": return 500 if branch_count >= 25 else 400
    return 150

# 마지막 계산 설명(사유)을 저장/조회하기 위한 전역
_LAST_EXPLAIN = {"explain": "", "raw": None}

def set_last_explain(text_or_obj):
    """
    text_or_obj가 str이면 그대로 저장,
    dict/list 등 구조화 데이터면 pretty JSON으로 저장 + 원본도 raw에 보관.
    """
    global _LAST_EXPLAIN
    try:
        if isinstance(text_or_obj, str):
            _LAST_EXPLAIN["explain"] = (text_or_obj or "").strip()
            _LAST_EXPLAIN["raw"] = None
        elif isinstance(text_or_obj, (dict, list, tuple)):
            _LAST_EXPLAIN["explain"] = json.dumps(text_or_obj, ensure_ascii=False, indent=2)
            _LAST_EXPLAIN["raw"] = text_or_obj
        else:
            # 그 외 타입은 문자열로 변환
            _LAST_EXPLAIN["explain"] = str(text_or_obj)
            _LAST_EXPLAIN["raw"] = None
    except Exception as e:
        _LAST_EXPLAIN["explain"] = f"[explain-save-failed] {e}"
        _LAST_EXPLAIN["raw"] = None

def get_last_explain(as_dict=False):
    """
    기본은 사람이 읽을 문자열을 반환.
    as_dict=True면 dict 형태(문자열+raw)를 반환.
    """
    return _LAST_EXPLAIN if as_dict else _LAST_EXPLAIN.get("explain", "")


def get_last_explain(*, as_dict: bool = False):
    """
    as_dict=False (기본): 마지막 설명 텍스트만 반환
    as_dict=True: {"text": ..., "data": ...} 그대로 반환
    """
    return _LAST_EXPLAIN if as_dict else (_LAST_EXPLAIN.get("text") or "")

class ExplainDict(TypedDict, total=False):
    # 필수(요구) 키 – 값은 텍스트(단위 포함 문자열)로 합의
    A_top: str          # 상단 여유/상판 관련 사유
    B_gap: str          # 부스바/상간 간격 또는 레일 간격 등
    C_branch_total: str # 분기관로/분기 합산 공간
    D_bottom: str       # 하부 여유/바닥부 철물
    E_accessory: str    # 부속자재/미터류/덕트 등
    H_final: str        # 최종 의사결정 한 줄 요약 ("최종: 600x1000x150")
    policy: str         # 적용 정책/룰 설명

    # 선택 키 – 있을 경우 표시
    width: str
    height: str
    depth: str

def normalize_explain(ex: Any) -> ExplainDict:
    """
    Explain 폴리필:
    - None → 빈 dict
    - str  → {'H_final': ex} 로 승격
    - dict → 그대로(단, 키 문자열 강제)
    항상 dict(ExplainDict 근사)로 반환.
    """
    if ex is None:
        return ExplainDict()
    if isinstance(ex, str):
        return ExplainDict(H_final=str(ex))
    if isinstance(ex, Mapping):
        # 키를 문자열로 강제
        out: Dict[str, Any] = {}
        for k, v in ex.items():
            out[str(k)] = v if isinstance(v, str) else ("" if v is None else str(v))
        return ExplainDict(**out)
    # 그 외 타입은 문자열로 요약
    return ExplainDict(H_final=str(ex))

def _kv(label: str, value: Optional[str]) -> Optional[str]:
    """값이 있으면 '• label: value' 포맷을 만들어 주고, 없으면 None."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    return f"• {label}: {v}"

def explain_to_mini_report(explain: Any) -> str:
    """
    고객 전달용/내부 검수용 '미니 리포트'를 생성.
    입력: raw explain(any) → normalize_explain()로 흡수 → 카드형 텍스트 반환.
    포맷: 전체 평문(복붙/메신저 전송/로그 남기기 용이)
    공식/산출식에는 개입하지 않음(설명만 생성).
    """
    ex = normalize_explain(explain)

    lines = []
    lines.append("===== 외함 사이즈 선정 사유 (Mini Report) =====")
    # 요약(최상단)
    # H_final이 있으면 1줄 요약, 없으면 width/height/depth 조합으로 보여줌
    summary = ex.get("H_final")
    if not summary:
        whd = "x".join([s for s in [ex.get("width"), ex.get("height"), ex.get("depth")] if s])
        summary = f"최종: {whd}" if whd else ""
    if summary:
        lines.append(f"{summary}")

    # 구성 A~E, 정책
    sec = [
        _kv("A(상단 여유)", ex.get("A_top")),
        _kv("B(간격/버스/레일)", ex.get("B_gap")),
        _kv("C(분기 합산)", ex.get("C_branch_total")),
        _kv("D(하부 여유)", ex.get("D_bottom")),
        _kv("E(부속/계기/배선덕트)", ex.get("E_accessory")),
        _kv("정책/룰", ex.get("policy")),
    ]
    sec = [s for s in sec if s]
    if sec:
        lines.append("")
        lines.extend(sec)

    # 부가 표기(W/H/D가 텍스트로 전달되는 경우)
    whd_items = [
        _kv("W", ex.get("width")),
        _kv("H", ex.get("height")),
        _kv("D", ex.get("depth")),
    ]
    whd_items = [s for s in whd_items if s]
    if whd_items:
        lines.append("")
        lines.append("치수:")
        lines.extend(whd_items)

    # 비어있을 경우의 안전장치
    if len(lines) <= 1:
        lines.append("(참고: explain 정보가 비어있거나 레거시 포맷입니다.)")

    return "\n".join(lines)

# (선택) 마지막 explain을 안전하게 뽑는 래퍼 — 프로젝트에 get_last_explain()이 이미 있으면 사용 안 해도 됨.
def get_last_explain_safe() -> ExplainDict:
    """
    기존 코드에 get_last_explain()이 있으면 그걸 호출하고,
    없으면 빈 explain을 반환.
    """
    try:
        # 기존 구현이 있다면 그대로 사용
        if 'get_last_explain' in globals():
            return normalize_explain(get_last_explain())
    except Exception:
        pass
    return ExplainDict()

# ========================= Explain 스키마 & 미니 리포트 생성기 (BEGIN) =========================

class ExplainDict(TypedDict, total=False):
    # 필수(요구) 키 – 값은 텍스트(단위 포함 문자열)로 합의
    A_top: str          # 상단 여유/상판 관련 사유
    B_gap: str          # 부스바/상간 간격 또는 레일 간격 등
    C_branch_total: str # 분기관로/분기 합산 공간
    D_bottom: str       # 하부 여유/바닥부 철물
    E_accessory: str    # 부속자재/미터류/덕트 등
    H_final: str        # 최종 의사결정 한 줄 요약 ("최종: 600x1000x150")
    policy: str         # 적용 정책/룰 설명

    # 선택 키 – 있을 경우 표시
    width: str
    height: str
    depth: str

def normalize_explain(ex: Any) -> ExplainDict:
    """
    Explain 폴리필:
    - None → 빈 dict
    - str  → {'H_final': ex} 로 승격
    - dict → 그대로(단, 키 문자열 강제)
    항상 dict(ExplainDict 근사)로 반환.
    """
    if ex is None:
        return ExplainDict()
    if isinstance(ex, str):
        return ExplainDict(H_final=str(ex))
    if isinstance(ex, Mapping):
        # 키를 문자열로 강제
        out: Dict[str, Any] = {}
        for k, v in ex.items():
            out[str(k)] = v if isinstance(v, str) else ("" if v is None else str(v))
        return ExplainDict(**out)
    # 그 외 타입은 문자열로 요약
    return ExplainDict(H_final=str(ex))

def _kv(label: str, value: Optional[str]) -> Optional[str]:
    """값이 있으면 '• label: value' 포맷을 만들어 주고, 없으면 None."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    return f"• {label}: {v}"

def explain_to_mini_report(explain: Any) -> str:
    """
    고객 전달용/내부 검수용 '미니 리포트'를 생성.
    입력: raw explain(any) → normalize_explain()로 흡수 → 카드형 텍스트 반환.
    포맷: 전체 평문(복붙/메신저 전송/로그 남기기 용이)
    공식/산출식에는 개입하지 않음(설명만 생성).
    """
    ex = normalize_explain(explain)

    lines = []
    lines.append("===== 외함 사이즈 선정 사유 (Mini Report) =====")
    # 요약(최상단)
    # H_final이 있으면 1줄 요약, 없으면 width/height/depth 조합으로 보여줌
    summary = ex.get("H_final")
    if not summary:
        whd = "x".join([s for s in [ex.get("width"), ex.get("height"), ex.get("depth")] if s])
        summary = f"최종: {whd}" if whd else ""
    if summary:
        lines.append(f"{summary}")

    # 구성 A~E, 정책
    sec = [
        _kv("A(상단 여유)", ex.get("A_top")),
        _kv("B(간격/버스/레일)", ex.get("B_gap")),
        _kv("C(분기 합산)", ex.get("C_branch_total")),
        _kv("D(하부 여유)", ex.get("D_bottom")),
        _kv("E(부속/계기/배선덕트)", ex.get("E_accessory")),
        _kv("정책/룰", ex.get("policy")),
    ]
    sec = [s for s in sec if s]
    if sec:
        lines.append("")
        lines.extend(sec)

    # 부가 표기(W/H/D가 텍스트로 전달되는 경우)
    whd_items = [
        _kv("W", ex.get("width")),
        _kv("H", ex.get("height")),
        _kv("D", ex.get("depth")),
    ]
    whd_items = [s for s in whd_items if s]
    if whd_items:
        lines.append("")
        lines.append("치수:")
        lines.extend(whd_items)

    # 비어있을 경우의 안전장치
    if len(lines) <= 1:
        lines.append("(참고: explain 정보가 비어있거나 레거시 포맷입니다.)")

    return "\n".join(lines)


# === /NEW ===


# === NEW UTILS: 외함 하부여유/부속여유/계량기 하부취부 계산 ===
from estimate_policy import load_policies  # (STEP 2에서 추가한 임포트와 동일하면 중복 삽입 금지)

def bottom_clearance_mm(main_amp: int) -> int:
    """
    하부 여유 D(mm)
    규칙: 20~225A=150 / 300~400A=200 / 500A=250
    """
    if main_amp <= 225:
        return 150
    elif main_amp <= 400:
        return 200
    else:
        return 250

def accessory_allowance_mm(C_branch_total: int, E_ratio: float = None, duct_mm: int = 40) -> int:
    """
    부속 여유 E(mm) = C(분기총합)*비율 + 덕트여유(기본 40mm)
    비율 디폴트는 정책(E_ratio_default, 기본 0.25=25%)
    """
    pol, _ = load_policies()
    ratio = E_ratio if E_ratio is not None else pol.get("E_ratio_default", 0.25)
    return int(round(C_branch_total * ratio)) + int(duct_mm)

def meter_layout_effect(meter_count: int, columns: int = None, single_meter_side_ok: bool = True):
    """
    계량기 하부취부가 W/H에 주는 영향 계산
    - 1EA이고 single_meter_side_ok=True면: 메인 좌/우 빈공간 사용 → W/H 변화 없음
    - 2EA 이상이면: 하부 슬롯 방식
        * 1칸 높이(slot_h) = 200mm (130 본체 + 70 배선)
        * 컬럼 폭(col_w) = 130mm
        * rows = ceil(meter_count / columns)
        * W증가 = columns * col_w
        * H증가 = rows * slot_h
    반환: (w_add:int, h_add:int, meta:dict)
    """
    import math
    pol, _ = load_policies()
    slot_h = int(pol["meter_bottom_slot"]["h_mm"])            # 200
    col_w  = int(pol["meter_bottom_slot"]["w_per_column_mm"]) # 130
    columns = int(columns or pol.get("meter_columns_default", 2))

    if meter_count <= 1 and single_meter_side_ok:
        return 0, 0, {"mode": "side-space", "columns": 0, "rows": 0}

    rows = int(math.ceil(meter_count / float(columns)))
    w_add = columns * col_w
    h_add = rows * slot_h
    return w_add, h_add, {
        "mode": "bottom-mount",
        "columns": columns,
        "rows": rows,
        "slot_h": slot_h,
        "col_w": col_w
    }
# === /NEW UTILS ===

# === NEW: AF 값 정규화 헬퍼 ===
def _af_to_int(val) -> int:
    """
    '200AF' 같은 문자열을 안전하게 정수 200으로 변환.
    이미 int면 그대로 반환.
    숫자가 없으면 0 반환.
    """
    try:
        return int(val)
    except Exception:
        s = "".join(ch for ch in str(val) if ch.isdigit())
        return int(s) if s else 0
# === /NEW ===


# === NEW: 인건비/기타비용 계산 (조립티어 + E.T + 마그네트 인건비) ===

def _assembly_tier_by_af(main_af: int):
    """
    조립 기본 인건비 티어 테이블을 AF로 매핑.
    - base_WH: 기준 외함(W,H)
    - base_krw: 기준 인건비
    - per_100H_add_krw: H가 100mm 늘 때마다 추가
    """
    if main_af <= 100:
        return {"base_WH": (600, 700),  "base_krw":  50000, "per_100H_add_krw": 15000}
    elif main_af <= 250:
        return {"base_WH": (700, 800),  "base_krw":  60000, "per_100H_add_krw": 15000}
    elif main_af == 400:
        return {"base_WH": (800, 1200), "base_krw": 130000, "per_100H_add_krw": 20000}
    else:  # 600~800AF
        return {"base_WH": (900, 1600), "base_krw": 250000, "per_100H_add_krw": 40000}

def calc_assembly_labor(main_af: int, H: int, small_20a_majority: bool = False):
    """
    조립 기본 인건비 계산:
      - 티어 기준 H보다 크면, (ΔH/100) 올림 × per_100H_add_krw 가산
      - 소형 20A(SIE-32/32GRHS) 다수 케이스 예외 증액(간소화): +10,000 또는 +15,000
        (정밀 로직은 추후 branch 모델 분석로 확장)
    반환: (labor:int, meta:dict)
    """
    import math
    af_int = _af_to_int(main_af)
    tier = _assembly_tier_by_af(af_int)
    base_W, base_H = tier["base_WH"]
    base_labor = tier["base_krw"]
    per_100_add = tier["per_100H_add_krw"]

    delta_h_steps = max(0, math.ceil(max(0, H - base_H) / 100.0))
    add_labor = delta_h_steps * per_100_add

    # 예외 간소화: 티어별 예외 증액치
    if small_20a_majority:
        if af_int <= 250:
            add_labor = max(add_labor, 10000)
        elif af_int == 400:
            add_labor = max(add_labor, 15000)
        else:
            add_labor = max(add_labor, 15000)


    total = base_labor + add_labor
    meta = {
        "tier_base_WH": (base_W, base_H),
        "tier_base_krw": base_labor,
        "per_100H_add_krw": per_100_add,
        "delta_h_steps": delta_h_steps,
        "add_labor": add_labor,
        "small_20a_majority": small_20a_majority
    }
    return int(total), meta

def _et_unit_price_by_af(main_af: int) -> int:
    """
    E.T 단가(메인 AF 기준)
      - 50~250AF: 4,500
      - 400AF: 12,000
      - 600~800AF: 18,000
    """
    if main_af <= 250:
        return 4500
    elif main_af == 400:
        return 12000
    else:
        return 18000

def calc_et_cost(main_af: int, branch_count: int):
    """
    E.T 수량 규칙: 분기차단기 12개마다 1개씩(올림)
    반환: (et_cost:int, meta:dict)
    """
    import math
    unit = _et_unit_price_by_af(_af_to_int(main_af))
    qty = max(1, math.ceil(max(0, int(branch_count)) / 12.0))  # 최소 1개 가정(필요시 0 허용으로 변경 가능)
    total = unit * qty
    meta = {"unit_price": unit, "qty": qty}
    return int(total), meta

def calc_magnet_labor(magnet_count: int):
    """
    마그네트 1EA 당 인건비 = 20,000원 (정책에서 읽음, 기본 2만원)
    반환: (labor:int, meta:dict)
    """
    pol, _ = load_policies()
    per = int(pol.get("magnet_labor_per_unit_krw", 20000))
    count = max(0, int(magnet_count or 0))
    total = per * count
    return int(total), {"per_unit": per, "count": count}

def calc_labor_and_misc(main_af: int, H: int, branch_count: int, magnet_count: int,
                        small_20a_majority: bool = False):
    """
    종합 계산(현 단계 핵심 3종):
      - 조립 기본 인건비(티어 + H 증분)
      - E.T
      - 마그네트 인건비
    반환: (sum:int, breakdown:dict)
    """
    asm, asm_meta = calc_assembly_labor(main_af, H, small_20a_majority=small_20a_majority)
    et, et_meta = calc_et_cost(main_af, branch_count)
    mag, mag_meta = calc_magnet_labor(magnet_count)

    total = asm + et + mag
    return int(total), {
        "assembly": {"cost": asm, "meta": asm_meta},
        "ET": {"cost": et, "meta": et_meta},
        "magnet_labor": {"cost": mag, "meta": mag_meta}
    }
# === /NEW ===

# === NEW: 기타 자재비 (N.T / N.P-3T*40*200 / 코팅 / ELB 지지대 / 인슐레이터) ===

def calc_nt_cost(qty: int):
    """
    N.T: 1EA = 3,000원
    """
    unit = 3000
    q = max(0, int(qty or 0))
    total = unit * q
    return int(total), {"unit_price": unit, "qty": q}

def calc_np_card_holder_cost(qty: int, unit_price: int | None = None):
    """
    N.P CARD HOLDER: '분기총수량'이 수량 규칙. 단가 미정(문서 기준).
    - unit_price를 넘기지 않으면 0원 처리하고 메모 남김.
    """
    q = max(0, int(qty or 0))
    if unit_price is None:
        return 0, {"unit_price": None, "qty": q, "note": "N.P CARD HOLDER 단가 미설정"}
    total = int(unit_price) * q
    return int(total), {"unit_price": int(unit_price), "qty": q}

def calc_np_3t_40_200_cost(qty: int = 1):
    """
    N.P / 3T*40*200: 1EA = 4,000원 (기본 1개 가정)
    """
    unit = 4000
    q = max(0, int(qty or 0))
    total = unit * q
    return int(total), {"unit_price": unit, "qty": q}

def calc_coating_cost(main_af):
    """
    코팅: 50~250AF = 5,000원 / 400~800AF = 10,000원
    """
    af_int = _af_to_int(main_af)
    if af_int <= 250:
        unit = 5000
    else:
        unit = 10000
    return int(unit), {"unit_by_af": unit, "af": af_int}

def calc_elb_support_cost(model_counts: dict | None):
    """
    ELB 지지대: (SIE-32, SIB-32, 32GRHS, BS32) 대상 모델 총수량 × 500원
    model_counts 예:
      {"SIE-32": 4, "SIB-32": 2, "32GRHS": 0, "BS32": 1}
    """
    unit = 500
    keys = ["SIE-32", "SIB-32", "32GRHS", "BS32"]
    mc = model_counts or {}
    qty = sum(int(mc.get(k, 0) or 0) for k in keys)
    total = unit * qty
    return int(total), {"unit_price": unit, "qty": qty, "models": {k: int(mc.get(k, 0) or 0) for k in keys}}

def calc_insulator_cost(main_af, main_count: int = 1):
    """
    인슐레이터: 메인당 4EA
      - 50~250AF: 개당 1,100원
      - 400~800AF: 개당 4,400원
    """
    af_int = _af_to_int(main_af)
    per_main_qty = 4
    if af_int <= 250:
        unit = 1100
    else:
        unit = 4400
    total_qty = per_main_qty * max(1, int(main_count or 1))
    total = unit * total_qty
    return int(total), {"unit_price": unit, "per_main_qty": per_main_qty, "main_count": int(max(1, int(main_count or 1))), "total_qty": total_qty}

def calc_other_materials_cost(
    *,
    main_af,
    branch_count: int,
    nt_qty: int = 0,
    np_card_qty: int = 0,
    np_card_unit_price: int | None = None,
    np_3t_qty: int = 1,
    elb_support_models: dict | None = None,
    main_count: int = 1,
    include_coating: bool = True
):
    """
    기타 자재비 총합 및 상세:
      - N.T (qty * 3,000)
      - N.P / 3T*40*200 (qty * 4,000, 기본 1EA)
      - N.P CARD HOLDER (qty * 단가; 단가 미설정 시 0원 + 노트)
      - 코팅 (AF별 5,000 / 10,000; include_coating=True일 때만)
      - ELB 지지대 (대상모델 총수량 * 500)
      - 인슐레이터 (메인당 4EA; AF 50~250=1,100 / 400~800=4,400)

    반환: (sum:int, breakdown:dict)
    """
    total = 0
    breakdown = {}

    nt, nt_meta = calc_nt_cost(nt_qty)
    total += nt
    breakdown["NT"] = {"cost": nt, "meta": nt_meta}

    np3t, np3t_meta = calc_np_3t_40_200_cost(np_3t_qty)
    total += np3t
    breakdown["NP_3T_40_200"] = {"cost": np3t, "meta": np3t_meta}

    npcard, npcard_meta = calc_np_card_holder_cost(np_card_qty, unit_price=np_card_unit_price)
    total += npcard
    breakdown["NP_CARD_HOLDER"] = {"cost": npcard, "meta": npcard_meta}

    if include_coating:
        coat, coat_meta = calc_coating_cost(main_af)
        total += coat
        breakdown["COATING"] = {"cost": coat, "meta": coat_meta}

    elb, elb_meta = calc_elb_support_cost(elb_support_models)
    total += elb
    breakdown["ELB_SUPPORT"] = {"cost": elb, "meta": elb_meta}

    ins, ins_meta = calc_insulator_cost(main_af, main_count=main_count)
    total += ins
    breakdown["INSULATOR"] = {"cost": ins, "meta": ins_meta}

    # 참고: 분기총수량(branch_count)은 NP_CARD_HOLDER 수량 산정 근거로 사용 가능(지금은 qty를 직접 받음)
    breakdown["context"] = {"branch_count": int(branch_count)}

    return int(total), breakdown
# === /NEW ===

# === NEW: GRAND TOTAL (외함 + 인건비 + 기타자재 + 잡자재비) ===

def calc_grand_total(
    *,
    main_kind: str,
    main_poles_text: str,
    main_amp_text: str,
    branches: list,
    style: str = "경제형",
    # 외함 옵션
    meter_count: int = 0,
    meter_columns: int | None = None,
    single_meter_side_ok: bool = True,
    E_ratio: float | None = None,
    # 비용 요소
    magnet_count: int = 0,
    accessory_count: int = 0,
    # 기타 자재비 입력
    nt_qty: int = 0,
    np_card_qty: int = 0,
    np_card_unit_price: int | None = None,
    np_3t_qty: int = 1,
    elb_support_models: dict | None = None,
    main_count: int = 1,
    include_coating: bool = True,
    # 조립 인건비 옵션
    small_20a_majority: bool = False
):
    """
    1) 외함 산출(W,H,D)
    2) 인건비(조립티어 + H증가 + E.T + 마그네트)
    3) 기타 자재비(N.T / N.P / 코팅 / ELB 지지대 / 인슐레이터)
    4) 잡자재비(규모 + 부속개수 CAP)

    반환: (grand_total:int, details:dict)
    """
    # 1) 외함
    W, H, Dp = compute_enclosure_size(
        main_kind=main_kind,
        main_poles_text=main_poles_text,
        main_amp_text=main_amp_text,
        branches=branches,
        style=style,
        meter_count=meter_count,
        meter_columns=meter_columns,
        single_meter_side_ok=single_meter_side_ok,
        E_ratio=E_ratio
    )
    enc_explain = get_last_explain()

    # 2) 메인 AF 도출
    main_amp_val = parse_int_amp(main_amp_text)
    main_af = map_amp_to_af(main_amp_val, style)
    branch_count = len(branches)

    # 3) 인건비(조립+ET+마그네트)
    labor_sum, labor_meta = calc_labor_and_misc(
        main_af=main_af,
        H=H,
        branch_count=branch_count,
        magnet_count=magnet_count,
        small_20a_majority=small_20a_majority
    )

    # 4) 기타 자재비
    other_sum, other_meta = calc_other_materials_cost(
        main_af=main_af,
        branch_count=branch_count,
        nt_qty=nt_qty,
        np_card_qty=np_card_qty,
        np_card_unit_price=np_card_unit_price,
        np_3t_qty=np_3t_qty,
        elb_support_models=elb_support_models,
        main_count=main_count,
        include_coating=include_coating
    )

    # 5) 잡자재비
    cons_sum, cons_meta = calc_consumables_cost(W, H, accessory_count=accessory_count)

    # 6) 합계
    grand = labor_sum + other_sum + cons_sum

    details = {
        "enclosure": {"W": W, "H": H, "D": Dp, "explain": enc_explain},
        "main": {"amp": main_amp_val, "af": main_af, "style": style, "branch_count": branch_count},
        "costs": {
            "labor_sum": labor_sum, "labor_meta": labor_meta,
            "other_sum": other_sum, "other_meta": other_meta,
            "consumables_sum": cons_sum, "consumables_meta": cons_meta
        },
        "inputs": {
            "magnet_count": magnet_count,
            "accessory_count": accessory_count,
            "nt_qty": nt_qty,
            "np_card_qty": np_card_qty,
            "np_card_unit_price": np_card_unit_price,
            "np_3t_qty": np_3t_qty,
            "elb_support_models": elb_support_models,
            "main_count": main_count,
            "include_coating": include_coating,
            "meter_count": meter_count,
            "meter_columns": meter_columns,
            "single_meter_side_ok": single_meter_side_ok,
            "E_ratio": E_ratio
        }
    }
    return int(grand), details
# === /NEW ===

# === NEW: 총견적 JSON 생성/저장 유틸 ===
import json, datetime, os

def build_quote_json(
    *,
    project: str,
    customer: str,
    requester: str | None = None,
    notes: str | None = None,
    # calc_grand_total과 동일한 인자들 ↓↓↓
    main_kind: str,
    main_poles_text: str,
    main_amp_text: str,
    branches: list,
    style: str = "경제형",
    meter_count: int = 0,
    meter_columns: int | None = None,
    single_meter_side_ok: bool = True,
    E_ratio: float | None = None,
    magnet_count: int = 0,
    accessory_count: int = 0,
    nt_qty: int = 0,
    np_card_qty: int = 0,
    np_card_unit_price: int | None = None,
    np_3t_qty: int = 1,
    elb_support_models: dict | None = None,
    main_count: int = 1,
    include_coating: bool = True,
    small_20a_majority: bool = False
) -> dict:
    """
    총견적(인건비+기타자재+잡자재비)과 근거를 JSON payload로 구성해서 반환.
    """
    grand, details = calc_grand_total(
        main_kind=main_kind,
        main_poles_text=main_poles_text,
        main_amp_text=main_amp_text,
        branches=branches,
        style=style,
        meter_count=meter_count,
        meter_columns=meter_columns,
        single_meter_side_ok=single_meter_side_ok,
        E_ratio=E_ratio,
        magnet_count=magnet_count,
        accessory_count=accessory_count,
        nt_qty=nt_qty,
        np_card_qty=np_card_qty,
        np_card_unit_price=np_card_unit_price,
        np_3t_qty=np_3t_qty,
        elb_support_models=elb_support_models,
        main_count=main_count,
        include_coating=include_coating,
        small_20a_majority=small_20a_majority
    )

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enc = details["enclosure"]
    costs = details["costs"]

    payload = {
        "meta": {
            "project": project,
            "customer": customer,
            "requester": requester,
            "notes": notes,
            "created_at": now
        },
        "inputs": details["inputs"],
        "enclosure": {
            "W": enc["W"], "H": enc["H"], "D": enc["D"],
            "H_formula": "H = A + B + C + D + E",
            "explain": {
                "A_top": enc["explain"].get("A_top"),
                "B_gap": enc["explain"].get("B_gap"),
                "C_branch_total": enc["explain"].get("C_branch_total"),
                "D_bottom": enc["explain"].get("D_bottom"),
                "E_accessory": enc["explain"].get("E_accessory")
            }
        },
        "main": details["main"],
        "costs": {
            "labor_sum": costs["labor_sum"],
            "other_sum": costs["other_sum"],
            "consumables_sum": costs["consumables_sum"],
            "subtotal": costs["labor_sum"] + costs["other_sum"] + costs["consumables_sum"],
            "breakdown": {
                "labor_meta": costs["labor_meta"],
                "other_meta": costs["other_meta"],
                "consumables_meta": costs["consumables_meta"]
            }
        },
        "grand_total": grand,
        "currency": "KRW"
    }
    return payload

def save_quote_json(filepath: str, payload: dict) -> str:
    """
    payload를 JSON 파일로 저장. 저장된 파일 경로를 반환.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return os.path.abspath(filepath)
# === /NEW ===


# === NEW: 잡자재비(소모품비) 자동 계산 ===
def calc_consumables_cost(W: int, H: int, accessory_count: int = 0):
    """
    규칙:
      - 기준: W600 x H700 = 7,000원
      - W/H가 기준에서 100mm 증가할 때마다 +1,000원 (각 축 합산)
      - 부속자재 1EA당 +12,000원
      - 총액 CAP(상한): 정책(consumables_cap_krw, 기본 42,000원)

    반환: (total_cost:int, meta:dict)
    """
    import math
    pol, _ = load_policies()
    base_W, base_H = 600, 700
    base = 7000
    per_step_add = 1000
    per_accessory_add = 12000
    cap = int(pol.get("consumables_cap_krw", 42000))

    w_steps = max(0, math.ceil((W - base_W) / 100.0))
    h_steps = max(0, math.ceil((H - base_H) / 100.0))
    size_add = (w_steps + h_steps) * per_step_add
    accessory_add = max(0, int(accessory_count)) * per_accessory_add

    total = base + size_add + accessory_add
    if total > cap:
        total = cap

    meta = {
        "base": base,
        "base_WH": (base_W, base_H),
        "w_steps": w_steps,
        "h_steps": h_steps,
        "size_add": size_add,
        "accessory_count": accessory_count,
        "accessory_add": accessory_add,
        "cap": cap
    }
    return int(total), meta
# === /NEW ===


# ===================== compute_enclosure_size 교체 시작 =====================
def compute_enclosure_size(
    main_kind,
    main_poles_text,
    main_amp_text,
    branches,
    style="경제형",
    # --- NEW: 추가 옵션 (기존 호출과 호환) ---
    accessories: dict = None,             # {"magnet": n, ...} 선택
    meter_count: int = 0,                 # 계량기 개수
    meter_columns: int = None,            # None이면 정책 기본(2칸)
    single_meter_side_ok: bool = True,    # 1EA는 메인 좌/우 여유로 처리 가능?
    E_ratio: float = None                 # E(부속 여유) 비율(없으면 정책 기본 0.25)
):
    """
    NEW 표준식: H = A + B + C + D + E
      A: 상부 인입 여유 + 메인 높이
      B: 메인-첫 분기 간격(기본 30mm)
      C: 분기 총합(마주보기 R+S+T+N 통일)  -> 기존 compute_branch_total_height 재사용
      D: 하부 여유 (20~225A=150 / 300~400A=200 / 500A=250)
      E: 부속 여유 (C*비율[기본 25%] + 덕트 40mm)

    W: 기존 width_from_max_spec + (계량기 하부취부: columns*130 추가)
    D(depth): 기존 규칙 유지
    """

    # 0) 입력 정규화
    main_amp = parse_int_amp(main_amp_text)
    main_af  = map_amp_to_af(main_amp, style)
    main_poles = int(str(main_poles_text).replace("P", ""))

    # 1) A, B, C (기존 테이블/로직 재사용)
    A = MAIN_TOP_CLEARANCE.get(main_af, 130) + MAIN_BODY_HEIGHT.get(main_af, 120)
    B = 30  # 메인과 첫 분기간 최소 30mm
    C = compute_branch_total_height(branches, style)

    # 2) NEW: D, E
    D_bottom = bottom_clearance_mm(main_amp)
    E_allow  = accessory_allowance_mm(C, E_ratio=E_ratio, duct_mm=40)

    # 3) H 산출 (100단위 반올림 유지)
    total_H = A + B + C + D_bottom + E_allow
    H = ceil_to_base(total_H, 100)

    # 4) W 산출 + 계량기 하부취부 시 H 가산
    W0 = width_from_max_spec(main_poles, main_af, branches, style)
    w_add, h_add_meter, meter_meta = meter_layout_effect(
        meter_count, columns=meter_columns, single_meter_side_ok=single_meter_side_ok
    )
    W = int(W0 + w_add)
    if h_add_meter:
        H = ceil_to_base(H + h_add_meter, 100)

    # 5) D(depth) 유지
    Dp = compute_enclosure_D(main_af, len(branches), main_amp)

    # 6) 근거 저장(UI/로그용)
    explain = {
        "policy": "H = A + B + C + D + E",
        "A_top": A,
        "B_gap": B,
        "C_branch_total": C,
        "D_bottom": D_bottom,
        "E_accessory": E_allow,
        "H_total_before_round": total_H,
        "H_final": H,
        "W_base": W0,
        "W_final": W,
        "Depth_D": Dp,
        "meter": {
            "count": meter_count,
            "mode": meter_meta.get("mode"),
            "columns": meter_meta.get("columns"),
            "rows": meter_meta.get("rows"),
            "slot_h": meter_meta.get("slot_h"),
            "col_w": meter_meta.get("col_w"),
            "h_add": h_add_meter,
            "w_add": w_add,
            "single_meter_side_ok": single_meter_side_ok
        },
        "E_ratio_used": (E_ratio if E_ratio is not None else load_policies()[0].get("E_ratio_default", 0.25))
    }
    # === [TRACE SAVE] 최소 설명 저장 (수치/정책 건드리지 않음) ===
    try:
        # 이미 함수 안에서 계산된 값/문구가 있으면 여기 채워 넣으세요.
        # 지금은 우선 최소 정보만 저장하여 raw_explain이 비지 않게 함.
        set_last_explain({
            "A_top": None,             # 다음 단계에서 실제 값 연결
            "B_gap": None,
            "C_branch_total": None,
            "D_bottom": None,
            "E_accessory": None,
            "policy": "compute_enclosure_size: trace-init"
        })
    except Exception:
        # 트레이스 저장은 계산에 영향 주지 않도록 무시
        pass
    # === [/TRACE SAVE] ===


    set_last_explain(explain)

    return int(W), int(H), int(Dp)

# ===================== compute_enclosure_size 교체 끝 =====================


# -------------------------
# 견적 부자재/단가 계산(요약)  (기존 규칙 유지)
# -------------------------
def main_breaker_af_for_cost(amp):
    if amp <= 100: return 100
    if amp <= 225: return 225
    if amp <= 400: return 400
    if amp <= 600: return 600
    return 800

def busbar_spec_by_main_amp(amp):
    if amp <= 100: return "3T*15"
    if amp <= 250: return "5T*20"
    if amp <= 400: return "6T*30"
    return "8T*40"

def main_busbar_kg_factor(amp):
    if amp <= 250: return 0.000007
    if amp <= 400: return 0.000013
    return 0.000015

def busbar_kg_factor_by_main(amp):
    if amp <= 250: return 0.0000045
    if amp <= 400: return 0.000007
    return 0.000009

def assembly_charge_base_and_add(main_amp, total_branch):
    base = 50000
    if main_amp <= 100:
        return base + max(0, total_branch - 16) * 2000
    elif main_amp <= 250:
        return base + max(0, total_branch - 14) * 2000
    elif main_amp <= 400:
        return base + 50000 + max(0, total_branch - 14) * 4000
    else:
        return base + 150000 + max(0, total_branch - 13) * 4000

def misc_material_fee(main_af_cost, branch_cnt):
    if main_af_cost <= 100: fee = 7000
    elif main_af_cost <= 225: fee = 9000
    elif main_af_cost <= 400: fee = 32000
    else: fee = 38000
    if branch_cnt > 20:
        extra_sets = math.ceil((branch_cnt - 20) / 5)
        fee += extra_sets * 2300
    return fee

def et_quantity(total_breakers):
    if total_breakers <= 0: return 0
    if total_breakers <= 11: return 1
    if total_breakers <= 23: return 2
    if total_breakers <= 33: return 3
    return math.ceil(total_breakers / 11)

def et_unit_price(main_amp):
    if main_amp <= 250: return 4500
    if main_amp <= 400: return 12000
    return 18000

def coating_price(main_amp):
    return 5000 if main_amp <= 250 else 10000

def pcover_price(main_af_cost, w, h, d):
    if main_af_cost <= 100:
        base = 15000; base_h = 600
        if h > base_h: base += math.ceil((h - base_h)/100.0)*1000
        return base
    elif main_af_cost <= 225:
        base = 25000; base_h = 800
        if h > base_h: base += math.ceil((h - base_h)/100.0)*1000
        return base
    elif main_af_cost <= 400:
        return 45000
    else:
        return 50000

# -------------------------
# SIE-32 집계 (ELB 2P 15/20/30A)
# -------------------------
def count_sie32(branch_list):
    cnt = 0
    for b in branch_list:
        if b["종류"] in ("ELB","ELB (누전)","누전","ELB(누전)","ELB( 배선)") or b["종류"] == "ELB":
            if b["극수"] == "2P" and b["용량"] in ["15A","20A","30A"]:
                cnt += int(b["수량"] or "0")
    return cnt

# -------------------------
# 모델명 매핑 (금지 코드 치환 포함)
# -------------------------
def model_name(brand, kind, poles, amp, is_branch=False):
    A = parse_int_amp(amp)
    poles_num = int(poles.replace("P", ""))

    # ELB 2P 15/20/30A 기본 고정
    if (kind.startswith("ELB") or kind == "ELB") and poles == "2P" and A in (15,20,30):
        if brand and ("LS" in brand or brand.upper()=="LS"):
            return "32GRHS"
        return "SIE-32"

    # MCCB 15/20/30A
    if A <= 30 and not (kind.startswith("ELB") or kind == "ELB"):
        return "SIB-32"

    base = "SBE" if (kind.startswith("ELB") or kind == "ELB") else "SBS"
    af_cost = main_breaker_af_for_cost(A)
    suffix = {100:"04", 225:"24", 400:"44", 600:"64", 800:"84"}[af_cost]
    code = f"{base}-{poles_num}{suffix}"
    if code in ("SBS-104","SBS-103"):
        code = code.replace("-104","-105").replace("-103","-105")
    return code

# -------------------------
# 견적 라인 생성 (기존 규칙 유지)
# -------------------------
def build_estimate_lines(enclosure, client, main_breaker, branches, accessories, spd_checked, style="경제형"):
    """
    외함 표기 개선:
      - 견적 표의 '외함' 규격을 사람이 읽기 좋게 표현
      - 형식:  [설치] [재질], ([기성함일 때 모델명 / 주문제작함일 때 '제작함']), WxHxD
      - 예:  옥내 STEEL 1.6T, (HDS 60 90 15), 800x1200x300
             옥내 STEEL 1.6T, (제작함), 800x1200x300
    """
    lines = []
    base_yes = enclosure.get("베이스 유무", "없음") == "있음"

    # 메인
    main_kind  = main_breaker["종류"]       # "MCCB" or "ELB"
    main_poles = main_breaker["극수"]       # "2P/3P/4P"
    main_amp   = main_breaker["용량"]       # "125A"
    main_qty   = int(main_breaker["수량"] or "1")

    # 분기 정규화
    branch_list = []
    for b in branches:
        if not b: continue
        branch_list.append({"종류": b["종류"], "극수": b["극수"], "용량": b["용량"], "수량": b["수량"]})

    # 외함 사이즈 계산 (W/H/D)
    W, H, D = compute_enclosure_size(main_kind, main_poles, main_amp, branch_list, style=style)

    # ----- 외함 규격 문구 구성 (사람 읽기형) -----
    install = enclosure.get("설치", "").strip()                  # 예: 옥내
    material = enclosure.get("외함 재질", "").strip()            # 예: STEEL 1.6T
    enc_kind = enclosure.get("함종류", "").strip()                # 예: 기성함 / 주문제작함 등
    model = enclosure.get("모델명", "").strip()                   # 기성함이면 모델명(있으면)

    # 기성함이면 모델명 우선, 없으면 "모델명 미지정"
    if enc_kind == "기성함":
        model_text = model if model else "모델명 미지정"
    elif enc_kind == "주문제작함":
        model_text = "제작함"
    else:
        # 기타(계량기함, FRP박스 등)는 종류 그대로 노출
        model_text = enc_kind or "기종 미지정"

    # 베이스 포함 표시는 뒤에 (+베이스)로 간단 표기
    base_tag = " (+베이스)" if base_yes else ""
    enclosure_spec_text = f"{install} {material}, ({model_text}){base_tag}, {W}x{H}x{D}"

    # 1) 외함
    lines.append({"no": 1, "품명": "외함", "규격": enclosure_spec_text, "단위": "면", "수량": 1, "단가": 0, "금액": 0})

    no = 2
    total_branch_count = 0
    total_breaker_count = main_qty

    # 2) 메인 차단기
    main_amp_int = parse_int_amp(main_amp)
    main_af_cost = main_breaker_af_for_cost(main_amp_int)
    mkind_label = "MCCB" if "MCCB" in main_kind else "ELB"
    main_model = model_name("상도", mkind_label, main_poles, main_amp)
    lines.append({"no": no, "품명": mkind_label, "규격": f"{main_poles} {main_amp} ({main_model})", "단위": "EA", "수량": main_qty, "단가": 0, "금액": 0}); no += 1

    # SPD 보조 MCCB
    if spd_checked:
        lines.append({"no": no, "품명": "MCCB", "규격": "4P 40A (SPD 보조)", "단위": "EA", "수량": 1, "단가": 0, "금액": 0}); no += 1
        total_breaker_count += 1

    # 3) 분기 — 결정적 정렬(항상 같은 순서: 종류→극수(desc:4P>3P>2P)→용량(desc))
    def _pole_rank(p):  # 4P>3P>2P
        return {"4P": 3, "3P": 2, "2P": 1}.get(str(p).upper(), 0)
    def _amp_i(a):  # "60A" -> 60
        try:
            return int(str(a).replace("A","").strip())
        except:
            return 0

    branch_list_sorted = sorted(
        branch_list,
        key=lambda b: (
            str(b.get("종류","")),           # MCCB/ELB 사전식
            -_pole_rank(b.get("극수","")),  # 4P>3P>2P
            -_amp_i(b.get("용량","0A")),    # 큰 용량 우선
            str(b.get("극수","")),
            str(b.get("용량",""))
        )
    )

    for b in branch_list_sorted:
        qty = int(b["수량"] or "0")
        if qty <= 0:
            continue
        kind_label = "MCCB" if b["종류"] == "MCCB" else "ELB"
        model = model_name("상도", kind_label, b["극수"], b["용량"], is_branch=True)
        spec  = f"{b['극수']} {b['용량']} ({model})"
        lines.append({"no": no, "품명": kind_label, "규격": spec, "단위": "EA", "수량": qty, "단가": 0, "금액": 0})
        no += 1
        total_branch_count += qty
        total_breaker_count += qty


    # SPD 직결형 + CABLE/WIRE
    if spd_checked:
        lines.append({"no": no, "품명": "SPD 직결형", "규격": "4P 40kA", "단위": "EA", "수량": 1, "단가": 50000, "금액": 50000}); no += 1
        lines.append({"no": no, "품명": "CABLE/WIRE", "규격": "", "단위": "식", "수량": 1, "단가": 15000, "금액": 15000}); no += 1

    # N+1 ~ N+12 고정 항목
    et_qty = et_quantity(total_breaker_count)
    et_price = et_unit_price(main_amp_int)
    lines.append({"no": no, "품명": "E.T", "규격": "", "단위": "EA", "수량": et_qty, "단가": et_price, "금액": et_qty * et_price}); no += 1
    lines.append({"no": no, "품명": "N.T", "규격": "", "단위": "EA", "수량": 1, "단가": 3000, "금액": 3000}); no += 1
    lines.append({"no": no, "품명": "N.P", "규격": "", "단위": "EA", "수량": 1, "단가": 4000, "금액": 4000}); no += 1
    lines.append({"no": no, "품명": "CARDHOLDER", "규격": "", "단위": "EA", "수량": total_branch_count, "단가": 800, "금액": total_branch_count * 800}); no += 1

    # MAIN BUS-BAR
    main_bus_spec = busbar_spec_by_main_amp(main_amp_int)
    main_bus_kg   = round_to_2((W * H) * main_busbar_kg_factor(main_amp_int))
    main_bus_amt  = round_to_2(main_bus_kg * MAIN_BUSBAR_UNIT_PRICE)
    lines.append({
        "no": no, "품명": "MAIN BUS-BAR", "규격": main_bus_spec,
        "단위": "KG", "수량": main_bus_kg, "단가": MAIN_BUSBAR_UNIT_PRICE,
        "금액": main_bus_amt
    }); no += 1

    # BUS-BAR (분기)
    bus_spec = busbar_spec_by_branch_amp(main_amp_int)
    bus_kg    = round_to_2((W * H) * branch_busbar_kg_factor(main_amp_int))
    bus_amt   = round_to_2(bus_kg * BRANCH_BUSBAR_UNIT_PRICE)
    lines.append({
        "no": no, "품명": "BUS-BAR", "규격": bus_spec,
        "단위": "KG", "수량": bus_kg, "단가": BRANCH_BUSBAR_UNIT_PRICE,
        "금액": bus_amt
    }); no += 1

    # 부속자재(입력 리스트 그대로 표기)
    # 8) 부속자재 (※ 위치 이동: BUS-BAR 뒤, COATING 앞)
    # 규칙:
    #  - MAG.CONTACTOR(마그네트)가 하나라도 있으면 자동 번들 생성
    #  - 일괄소등(ON/OFF 스위치 없음): MAG, FUSEHOLDER(1), TERMINAL BLOCK(2/마그), PVC DUCT(2/마그), CABLE/WIRE(1)
    #  - ON/OFF가 있으면: MAG, FUSEHOLDER(1), TERMINAL BLOCK(2/마그), PBL(1), PVC DUCT(2/마그), CABLE/WIRE(1)
    #  - 24H 타이머가 있으면: MAG, FUSEHOLDER(1), TERMINAL BLOCK(2/마그), PBL /SS(1), TIMER 24H(1), PVC DUCT(2/마그), CABLE/WIRE(1)
    #
    # 입력 accessories에 이미 동일 품목이 있으면 중복 추가하지 않음(이름 기준 대소문자 무시, 공백/슬래시 그대로 둠)

    def _norm_name(s: str) -> str:
        return (s or "").strip().lower()

    def _has(items, name):
        n = _norm_name(name)
        return any(_norm_name(x.get("name","")) == n for x in items)

    def _qty_of(items, name):
        n = _norm_name(name)
        return sum(int(str(x.get("qty","1")) or "1") for x in items if _norm_name(x.get("name","")) == n)

    # 입력 부속 원본 보존
    acc_in = [{"name": str(a.get("name","")).strip(), "qty": int(str(a.get("qty","1")) or "1")} for a in accessories or []]

    # 마그네트/플래그 감지
    mag_qty   = _qty_of(acc_in, "MAG.CONTACTOR") or _qty_of(acc_in, "MAGNETIC CONTACTOR") or _qty_of(acc_in, "MAG")
    has_onoff = any(k in _norm_name(a["name"]) for a in acc_in for k in ("on/off", "온/오프", "onoff", "pbl"))
    has_24h   = any(k in _norm_name(a["name"]) for a in acc_in for k in ("24h", "timer", "타이머"))

    # 자동 번들 구성
    acc_auto = []
    if mag_qty > 0:
        # 공통
        if not _has(acc_in, "FUSEHOLDER"):
            acc_auto.append({"name": "FUSEHOLDER", "qty": 1})
        if not _has(acc_in, "TERMINAL BLOCK"):
            acc_auto.append({"name": "TERMINAL BLOCK", "qty": 2 * mag_qty})
        if not _has(acc_in, "PVC DUCT"):
            acc_auto.append({"name": "PVC DUCT", "qty": 2 * mag_qty})
        if not _has(acc_in, "CABLE/WIRE"):
            acc_auto.append({"name": "CABLE/WIRE", "qty": 1})

        # 분기(ON/OFF / 24H)
        if has_24h:
            if not _has(acc_in, "PBL /SS"):
                acc_auto.append({"name": "PBL /SS", "qty": 1})
            if not _has(acc_in, "TIMER 24H"):
                acc_auto.append({"name": "TIMER 24H", "qty": 1})
        elif has_onoff:
            if not _has(acc_in, "PBL"):
                acc_auto.append({"name": "PBL", "qty": 1})
        else:
            # 일괄소등: ON/OFF 스위치 없음 → 추가 없음(공통만)
            pass

    # 출력 순서: (원본 부속 중 MAG.CONTACTOR 등 사용자가 넣은 항목) → 자동 번들(중복 제외)
    # 주: MAG.CONTACTOR 자체는 사용자가 넣은 대로 acc_in에 있을 것이므로 여기서 따로 생성하지 않음
    for a in acc_in:
        lines.append({"no": no, "품명": "부속자재", "규격": a["name"], "단위": "EA",
                      "수량": int(a.get("qty","1")), "단가": 0, "금액": 0}); no += 1
    for a in acc_auto:
        lines.append({"no": no, "품명": "부속자재", "규격": a["name"], "단위": "EA",
                      "수량": int(a.get("qty","1")), "단가": 0, "금액": 0}); no += 1
                    


    # COATING
    coat_price = coating_price(main_amp_int)
    lines.append({"no": no, "품명": "COATING", "규격": "PVC", "단위": "EA", "수량": 1, "단가": coat_price, "금액": coat_price}); no += 1

    # P-COVER
    pc_price = pcover_price(main_af_cost, W, H, D)
    lines.append({"no": no, "품명": "P-COVER", "규격": "아크릴(PC)", "단위": "EA", "수량": 1, "단가": pc_price, "금액": pc_price}); no += 1

    # ELB지지대 (모든 SIE-32 분기 수량)
    sie_cnt = count_sie32(branch_list)
    lines.append({"no": no, "품명": "ELB지지대", "규격": "", "단위": "EA", "수량": sie_cnt, "단가": 500, "금액": sie_cnt * 500}); no += 1

    # INSULATOR
    lines.append({"no": no, "품명": "INSULATOR", "규격": "EPOXY 40*40", "단위": "EA", "수량": 4, "단가": 1100, "금액": 4400}); no += 1

    # 잡자재비
    misc_fee = misc_material_fee(main_af_cost, total_branch_count)
    lines.append({"no": no, "품명": "잡자재비", "규격": "", "단위": "식", "수량": 1, "단가": misc_fee, "금액": misc_fee}); no += 1

    # ASSEMBLY CHARGE
    assembly = assembly_charge_base_and_add(main_amp_int, total_branch_count)
    lines.append({"no": no, "품명": "ASSEMBLY CHARGE", "규격": "", "단위": "식", "수량": 1, "단가": assembly, "금액": assembly}); no += 1
    
    # 정렬 고정값 & 그룹 태깅 (후처리)
    def _infer_group(name: str) -> str:
        n = (name or "").upper()
        if n in ("MCCB", "ELB"):
            return "BRANCH" if n == "ELB" else "MAIN" if len([r for r in lines if r.get("품명") in ("MCCB","ELB")]) == 1 else "BRANCH"
        if "BUS-BAR" in n:
            return "BUSBAR"
        if n in ("COATING", "P-COVER", "ELB지지대", "INSULATOR"):
            return "ACCESSORY2"
        if n in ("E.T","N.T","N.P","CARDHOLDER"):
            return "FIXED"
        if n in ("잡자재비","ASSEMBLY CHARGE"):
            return "LABOR"
        if n in ("외함",):
            return "ENCLOSURE"
        # 부속자재 및 그 외
        return "ACCESSORY"

    for idx, row in enumerate(lines, 1):
        # 결정적 정렬 키(0001, 0002, ...)
        row.setdefault("sort_key", f"{idx:04d}")
        # 그룹 태그(없으면 추론)
        if "group" not in row:
            row["group"] = _infer_group(str(row.get("품명","")))

    # 번호 연속성 가드 (개발/검증용)
    _nos = [int(row.get("no", 0)) for row in lines]
    assert _nos == list(range(1, len(lines) + 1)), f"줄번호 비연속 감지: {_nos}"

    return lines, (W, H, D)

# ============================ KISAN — PRICE MATCH & AMOUNT (SELF-CONTAINED) ============================
# 이 블록은 자체적으로 import/헬퍼/매칭/빌더/테스트를 모두 포함합니다.
# 기존 파일 끝의 패치 영역을 전부 삭제하고 이 블록 하나만 붙여넣으세요.

import os, io, json, re, glob, inspect
from typing import List, Dict, Any, Optional
from functools import lru_cache

try:
    import pandas as pd
except Exception:
    pd = None  # pandas 없으면 엑셀 로딩 생략

# ----- 경로/프로젝트 루트 -----
def _project_root() -> str:
    # 이 파일이 프로젝트 루트 바로 아래에 있다고 가정 (현재 구조에 맞춤)
    return os.path.abspath(os.path.dirname(__file__))

# ----- 가격표 로딩 -----
PRICEBOOK_FILENAMES = [
    "중요ai단가표.xlsx",
    os.path.join("data", "중요ai단가표.xlsx"),
    os.path.join("data", "prices", "중요ai단가표.xlsx"),
]

def _find_pricebook() -> Optional[str]:
    root = _project_root()
    # 1) 대표 경로 탐색
    for rel in PRICEBOOK_FILENAMES:
        cand = os.path.join(root, rel) if not os.path.isabs(rel) else rel
        if os.path.exists(cand):
            return cand
    # 2) 루트 이하 얕은 탐색
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn == "중요ai단가표.xlsx":
                return os.path.join(dirpath, fn)
    return None

@lru_cache(maxsize=1)
def load_pricebook() -> Dict[str, List[Dict[str, Any]]]:
    """
    중요ai단가표.xlsx → {sheet_name(lower): [row-dicts...]}
    권장 컬럼: item_type, model, name, spec, unit_price (대소문자 무시)
    """
    pb_path = _find_pricebook()
    if not pb_path or pd is None:
        return {}

    def _norm_sheet(df) -> List[Dict[str, Any]]:
        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]
        out = []
        for _, r in df.iterrows():
            d = {k: (None if pd.isna(v) else v) for k, v in r.items()}
            out.append(d)
        return out

    book: Dict[str, List[Dict[str, Any]]] = {}
    try:
        x = pd.ExcelFile(pb_path)
        for sn in x.sheet_names:
            df = x.parse(sn)
            book[sn.strip().lower()] = _norm_sheet(df)
    except Exception:
        return {}
    return book

# ----- 매칭 헬퍼 -----
def _s(val) -> str:
    return "" if val is None else str(val).strip()

def _uprice(v) -> Optional[float]:
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).replace(",", "").strip()
        return float(s) if s else None
    except Exception:
        return None

def _normalize_model(m: Any) -> str:
    s = _s(m).upper()
    s = re.sub(r"\s+", "", s)
    return s

def _text_contains(a: Any, b: Any) -> bool:
    A, B = _s(a).upper(), _s(b).upper()
    return (B in A) if B else False

def _best_candidate(cands: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not cands: return None
    with_price = [c for c in cands if _uprice(c.get("unit_price")) is not None]
    pool = with_price if with_price else cands
    pool.sort(key=lambda d: (len(_s(d.get("spec"))), len(_s(d.get("name")))), reverse=True)
    return pool[0] if pool else None

def _match_price_in_sheet(rows: List[Dict[str, Any]], line: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = _s(line.get("name") or (line.get("raw") or {}).get("품목") or (line.get("raw") or {}).get("K1"))
    model = _normalize_model(line.get("model") or (line.get("raw") or {}).get("model"))
    spec  = _s((line.get("spec") or {}).get("text"))

    # 1) 모델 정확
    exact = [r for r in rows if _normalize_model(r.get("model")) == model and model]
    if exact:
        return _best_candidate(exact)
    # 2) 이름 유사/포함
    part = [r for r in rows if _text_contains(name, r.get("name")) or _text_contains(r.get("name"), name)]
    if part:
        return _best_candidate(part)
    # 3) 스펙 유사
    if spec:
        sp = [r for r in rows if _text_contains(spec, r.get("spec")) or _text_contains(r.get("spec"), spec)]
        if sp:
            return _best_candidate(sp)
    # 4) 모델 접두 유사
    if model:
        prefix = [r for r in rows if _normalize_model(r.get("model")).startswith(model[:4])]
        if prefix:
            return _best_candidate(prefix)
    return None

def _guess_item_type(line: Dict[str, Any]) -> str:
    t = _s(line.get("item_type"))
    nm = _s(line.get("name") or (line.get("raw") or {}).get("품목") or (line.get("raw") or {}).get("K1"))
    U = nm.upper()
    if t: return t
    if any(k in U for k in ("MCCB","ELCB","ELB","MCB","EOCR","RCD","NFB")): return "breaker"
    if any(k in U for k in ("외함","함체","ENCLOSURE","분전반함","배전함","판넬")): return "enclosure"
    if any(k in U for k in ("단자대","터미널","퓨즈","덕트","레일","라벨","그랜드","GLAND")): return "accessory"
    if any(k in U for k in ("인건비","조립","배선","검사","시운전")): return "labor"
    return "misc"

def match_price(line: Dict[str, Any], pricebook: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
    if pricebook is None:
        pricebook = load_pricebook()
    if not pricebook:
        return {"unit_price": None, "match": None, "reason": "no_pricebook"}

    itype = _guess_item_type(line).lower()
    sheet_order = {
        "breaker":   ["breaker","차단기","mccb","elb","nfb"],
        "enclosure": ["enclosure","외함","함체"],
        "accessory": ["accessory","부속","자재","acc"],
        "labor":     ["labor","인건비"],
        "misc":      ["accessory","labor","breaker","enclosure"],
    }.get(itype, ["accessory","labor","breaker","enclosure"])

    for sn in sheet_order:
        rows = pricebook.get(sn) or pricebook.get(sn.lower()) or pricebook.get(sn.upper())
        if not rows:
            for k in pricebook.keys():
                if sn in k:
                    rows = pricebook[k]; break
        if not rows:
            continue
        hit = _match_price_in_sheet(rows, line)
        if hit:
            up = _uprice(hit.get("unit_price"))
            return {"unit_price": up, "match": {"sheet": sn, "row": hit}, "reason": "matched"}

    return {"unit_price": None, "match": None, "reason": "not_found"}

# ----- JSON 안전 로더 / 라인 추출 -----
def _load_estimate_json_safe(path: str):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _extract_lines_from_obj(obj) -> List[Dict[str, Any]]:
    """
    - dict & 'lines' → 그대로
    - dict & 'panels' 배열 내 각 panel.lines 합침
    - list 내 원소들이 dict & 'lines' → 전부 합침
    - 아니면 []
    """
    if isinstance(obj, dict):
        if isinstance(obj.get("lines"), list):
            return obj["lines"]
        if isinstance(obj.get("panels"), list):
            agg: List[Dict[str, Any]] = []
            for p in obj["panels"]:
                if isinstance(p, dict) and isinstance(p.get("lines"), list):
                    agg.extend(p["lines"])
            return agg
        return []
    if isinstance(obj, list):
        agg: List[Dict[str, Any]] = []
        for it in obj:
            if isinstance(it, dict) and isinstance(it.get("lines"), list):
                agg.extend(it["lines"])
        return agg
    return []

# ----- 기존 엔진 안전 호출 시도 -----
def _try_existing_builder(estimate_json_path: str) -> Optional[List[Dict[str, Any]]]:
    fn = globals().get("build_estimate_lines")
    if not callable(fn):
        return None
    try:
        sig = inspect.signature(fn)
    except Exception:
        return None

    params = list(sig.parameters.values())
    required = [p for p in params if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    if len(required) <= 1:
        try:
            return fn(estimate_json_path) or []
        except Exception:
            return None
    return None

# ----- 이름/수량 보정 -----
def _coalesce_name(line: Dict[str, Any]) -> str:
    n = _s(line.get("name"))
    if n: return n
    raw = line.get("raw") or {}
    for k in ("품목","K1","name","item","항목"):
        if _s(raw.get(k)): return _s(raw.get(k))
    return _s(line.get("model")) or "ITEM"

def _ensure_qty(line: Dict[str, Any]) -> float:
    q = line.get("qty")
    try:
        return float(q) if q is not None else 1.0
    except Exception:
        return 1.0

# ----- 메인: 경로 기반 빌더 + 가격 매칭 -----
def build_estimate_lines_with_prices(*args, **kwargs):
    """
    유연 시그니처:
      - build_estimate_lines_with_prices(estimate_json_path)
      - build_estimate_lines_with_prices(estimate_json_path=...)
      - (과거 시그니처와의 호환을 위해 *args/**kwargs 허용)
    반환:
      {"lines": [ { ..., "unit_price": float|None, "amount": float } ... ], "sum": float }
    """
    import os, json, re

    # ---------- 내부 유틸 ----------
    def _proj_root() -> str:
        return os.path.dirname(os.path.abspath(__file__))

    def _coalesce(d, keys, default=None):
        for k in keys:
            if isinstance(d, dict) and k in d and d[k] not in (None, ""):
                return d[k]
        return default

    def _ensure_qty(v) -> float:
        try:
            if v in (None, ""):
                return 1.0
            f = float(str(v).replace(",", ""))
            return f if f > 0 else 1.0
        except Exception:
            return 1.0

    def _amp_key(spec):
        if not spec:
            return None
        s = str(spec).upper().replace(" ", "")
        m = re.search(r"(\d+)\s*A", s)
        if not m:
            m = re.search(r"(\d+)\s*AMP", s)
        return (m.group(1) + "A") if m else None

    def _iter_lines_from_estimate_json(path: str):
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        # 허용 스키마:
        # (a) {"lines":[...]}
        # (b) [{"...":...}, ...]
        # (c) {"blocks":[{"lines":[...]}, ...]}
        # (d) 기타 키(items/records/rows/results)
        if isinstance(j, dict):
            if isinstance(j.get("lines"), list):
                return j["lines"]
            if isinstance(j.get("blocks"), list):
                acc = []
                for b in j["blocks"]:
                    if isinstance(b, dict) and isinstance(b.get("lines"), list):
                        acc.extend(b["lines"])
                if acc:
                    return acc
            for k in ("items", "records", "rows", "results"):
                if isinstance(j.get(k), list):
                    return j[k]
            return [j]  # 폴백
        elif isinstance(j, list):
            return j
        else:
            return []

    # ---------- pricebook ----------
    # load_pricebook() 는 파일 상단에 이미 정의되어 있다고 가정 (직전 단계에서 확인됨)
    book = load_pricebook() or {}
    # 우선순위: breaker 시트 -> '외함 및 차단기 모델명_단가' 시트
    price_rows = book.get("breaker") or book.get("외함 및 차단기 모델명_단가") or []

    def _match_price(model, spec):
        """모델/전류 매칭 우선 규칙으로 단가 탐색"""
        if not price_rows:
            return None
        model_s = (str(model).strip().upper() if model else "")
        spec_key = _amp_key(spec)

        # 1) 모델 완전일치 + 전류일치
        for r in price_rows:
            r_model = str(r.get("model") or "").strip().upper()
            r_speck = _amp_key(r.get("spec"))
            if model_s and r_model == model_s and (not spec_key or r_speck == spec_key):
                return r.get("unit_price")
        # 2) 모델 부분포함 + 전류일치
        if model_s:
            for r in price_rows:
                r_model = str(r.get("model") or "").strip().upper()
                r_speck = _amp_key(r.get("spec"))
                if (model_s in r_model) and (not spec_key or r_speck == spec_key):
                    return r.get("unit_price")
        # 3) 전류만 일치(모델 미지정 시)
        if spec_key:
            for r in price_rows:
                r_speck = _amp_key(r.get("spec"))
                if r_speck == spec_key:
                    return r.get("unit_price")
        return None

    # ---------- 입력 경로 파라미터 추출 ----------
    estimate_json_path = None
    if args:
        estimate_json_path = args[0]
    if estimate_json_path is None:
        estimate_json_path = kwargs.get("estimate_json_path")
    if not estimate_json_path:
        # 과거 시그니처 대응: kwargs에 dict 전체가 온 경우 등
        # 안전하게 프로젝트 기본 샘플로 폴백하지 않고 예외
        raise ValueError("estimate_json_path is required")

    # ---------- 라인 로딩 ----------
    lines = _iter_lines_from_estimate_json(estimate_json_path)

    # ---------- 라인별 가격 매칭 ----------
    enriched = []
    total_sum = 0.0
    dbg = (os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1") or (os.environ.get("KISAN_ESTIMATE_ENGINE_TEST") == "1")

    for ln in lines:
        # 다양한 키 케이스 흡수
        model = _coalesce(ln, ["model", "모델", "모델명", "형식"])
        spec  = _coalesce(ln, ["spec", "규격", "규격/전류", "정격", "정격전류", "용량"])
        qty   = _ensure_qty(_coalesce(ln, ["qty", "수량", "수량(개)", "수량(SET)"], 1))

        unit_price = _match_price(model, spec)
        amount = float(unit_price) * float(qty) if unit_price is not None else 0.0

        # 원본 필드 보존 + 금액 필드 주입
        new_ln = dict(ln)
        new_ln["unit_price"] = unit_price
        new_ln["amount"] = amount
        new_ln["qty"] = qty  # 정규화 반영
        enriched.append(new_ln)
        total_sum += amount

        if dbg:
            name_or_model = _coalesce(ln, ["name", "품명", "항목", "item", "desc", "description", "model", "모델명"], "")
            print(f"[PRICE-MATCH] {str(name_or_model)[:30]} | model={model} spec={spec} qty={qty} -> unit={unit_price} amt={int(amount)}")

    return {"lines": enriched, "sum": float(total_sum)}


# ===================== PRICEBOOK v2 (alias-aware, debug-ready) =====================
# 기존 load_pricebook()를 덮어쓰는 버전입니다. 시트/컬럼 한국어 별칭 자동 인식 + 디버그 출력.

import os, io, json, re
from typing import List, Dict, Any, Optional
from functools import lru_cache

# 시트 이름 정규화 (한국어/영문 모두 매핑)
def _canon_sheet_name(sn: str) -> str:
    s = (sn or "").strip().lower()
    if any(k in s for k in ["차단", "mccb", "breaker", "nfb", "elb", "rcd"]): return "breaker"
    if any(k in s for k in ["외함", "함체", "enclosure", "판넬"]): return "enclosure"
    if any(k in s for k in ["부속", "자재", "acc", "accessory", "accessories"]): return "accessory"
    if any(k in s for k in ["인건비", "labor"]): return "labor"
    return s  # 기타는 원명 소문자로

# 컬럼 별칭 (우선순위 순)
_ALIAS = {
    "item_type": ["item_type", "type", "category", "구분", "종류", "타입", "품목군"],
    "name":      ["name", "품명", "품목", "항목", "item", "description", "desc"],
    "model":     ["model", "모델", "모델명", "형식", "기종", "type_no", "catalog", "cat", "cat_no"],
    "spec":      ["spec", "규격", "사양", "정격", "스펙"],
    "unit_price":["unit_price", "단가", "가격", "price", "unit", "unit price", "unit_cost", "원가", "매입단가"],
}

def _pick_alias(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = d[k]
            if isinstance(v, str) and not v.strip():
                continue
            return v
    return None

def _as_float(v) -> Optional[float]:
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).replace(",", "").strip()
        return float(s) if s else None
    except Exception:
        return None

def _normalize_pricebook_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # 원본 키는 전부 소문자 키로 있다고 가정(load 시 처리). 별칭 매핑으로 표준키 생성.
    norm = dict(row)  # 원본 유지
    norm["item_type"] = _pick_alias(row, _ALIAS["item_type"])
    norm["name"]      = _pick_alias(row, _ALIAS["name"])
    norm["model"]     = _pick_alias(row, _ALIAS["model"])
    norm["spec"]      = _pick_alias(row, _ALIAS["spec"])
    norm["unit_price"]= _as_float(_pick_alias(row, _ALIAS["unit_price"]))
    return norm

try:
    import pandas as pd
except Exception:
    pd = None

PRICEBOOK_FILENAMES = [
    "중요ai단가표.xlsx",
    os.path.join("data", "중요ai단가표.xlsx"),
    os.path.join("data", "prices", "중요ai단가표.xlsx"),
]

def _project_root() -> str:
    return os.path.abspath(os.path.dirname(__file__))

def _find_pricebook() -> Optional[str]:
    root = _project_root()
    # 우선 경로
    for rel in PRICEBOOK_FILENAMES:
        cand = os.path.join(root, rel) if not os.path.isabs(rel) else rel
        if os.path.exists(cand):
            return cand
    # 얕은 전체 탐색
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn == "중요ai단가표.xlsx":
                return os.path.join(dirpath, fn)
    return None

@lru_cache(maxsize=1)
def load_pricebook() -> Dict[str, List[Dict[str, Any]]]:  # 기존 함수명 유지 (override)
    book: Dict[str, List[Dict[str, Any]]] = {}
    if pd is None:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pandas not available; cannot read Excel.")
        return book

    pb_path = _find_pricebook()
    if not pb_path:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pricebook not found.")
        return book

    try:
        x = pd.ExcelFile(pb_path)
    except Exception as e:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print(f"[PRICEBOOK][ERR] open failed: {e}")
        return book

    # 시트별 파싱 + 표준키 정규화
    for sn in x.sheet_names:
        try:
            df = x.parse(sn)
        except Exception:
            continue
        # 컬럼 소문자화
        df.columns = [str(c).strip().lower() for c in df.columns]
        rows: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            d = {k: (None if (pd.isna(v) if pd is not None else v is None) else v) for k, v in r.items()}
            nr = _normalize_pricebook_row(d)
            # 한 행도 유효 컬럼이 없으면 스킵
            if not any(nr.get(k) for k in ("name", "model", "spec", "unit_price")):
                continue
            rows.append(nr)
        if not rows:
            continue

        raw_key = sn.strip().lower()
        can_key = _canon_sheet_name(sn)  # breaker/enclosure/accessory/labor 등
        # 원래 시트명과 정규화 시트명 둘 다 인덱싱(중복 시 원래키 유지, 정규키는 없을 때만)
        book[raw_key] = rows
        if can_key not in book:
            book[can_key] = rows

    if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
        sample_keys = list(book.keys())[:8]
        print(f"[PRICEBOOK] path={pb_path}")
        print(f"[PRICEBOOK] sheets={sample_keys} (+{max(0, len(book)-len(sample_keys))} more)")
        # 임의 샘플 1행 출력
        for k in sample_keys[:3]:
            if book.get(k):
                print(f"[PRICEBOOK] sample[{k}]: { {kk:book[k][0].get(kk) for kk in ('name','model','spec','unit_price')} }")
                break
    return book
# ===================== /PRICEBOOK v2 =====================

# ===================== PRICEBOOK v2.1 — alias & number parsing reinforced =====================
# 기존 PRICEBOOK v2를 덮어쓰는 보강 버전입니다. (별칭 확장, 숫자 파싱 강화, 디버그에 컬럼 목록 출력)

import re
from typing import List, Dict, Any, Optional
from functools import lru_cache

# 컬럼 별칭(우선순위 순) — 한국어/영문 다양한 표기 대응
_ALIAS = {
    "item_type": ["item_type","type","category","구분","종류","타입","품목군"],
    "name": [
        "name","품명","품목","항목","item","description","desc",
        "제품명","항목명","품목명","세부품명","품목내역","내역"
    ],
    "model": [
        "model","모델","모델명","형식","기종","type_no","catalog","cat","cat_no",
        "모델no","형번","모델번호"
    ],
    "spec": [
        "spec","규격","사양","정격","스펙","정격전류","용량","size","규격(㎟)","규격(mm)","규격(원)"
    ],
    "unit_price": [
        "unit_price","단가","가격","price","unit","unit price","unit_cost","원가","매입단가",
        "단가(원)","공급가","공급단가","판매가","소비자가","금액","금액(원)","가격(원)","단가원"
    ],
}

def _pick_alias(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = d[k]
            if isinstance(v, str) and not v.strip():
                continue
            return v
    return None

def _as_float(v) -> Optional[float]:
    """모든 비숫자 문자를 제거하고 실수 변환 (예: '12,345원' → 12345.0)."""
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v)
        # 소수점/부호/숫자만 남기고 제거
        s = re.sub(r"[^\d.\-]", "", s)
        s = s.strip(".")  # '원'만 제거된 경우 남은 점 처리
        return float(s) if s else None
    except Exception:
        return None

def _normalize_pricebook_row(row: Dict[str, Any]) -> Dict[str, Any]:
    norm = dict(row)
    norm["item_type"] = _pick_alias(row, _ALIAS["item_type"])
    norm["name"]      = _pick_alias(row, _ALIAS["name"])
    norm["model"]     = _pick_alias(row, _ALIAS["model"])
    norm["spec"]      = _pick_alias(row, _ALIAS["spec"])
    norm["unit_price"]= _as_float(_pick_alias(row, _ALIAS["unit_price"]))
    return norm

@lru_cache(maxsize=1)
def load_pricebook() -> Dict[str, List[Dict[str, Any]]]:  # 기존 이름 유지(override)
    book: Dict[str, List[Dict[str, Any]]] = {}
    if pd is None:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pandas not available; cannot read Excel.")
        return book

    pb_path = _find_pricebook()
    if not pb_path:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pricebook not found.")
        return book

    try:
        x = pd.ExcelFile(pb_path)
    except Exception as e:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print(f"[PRICEBOOK][ERR] open failed: {e}")
        return book

    print_debug = os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1"
    if print_debug:
        print(f"[PRICEBOOK] path={pb_path}")

    def _canon_sheet_name(sn: str) -> str:
        s = (sn or "").strip().lower()
        if any(k in s for k in ["차단", "mccb", "breaker", "nfb", "elb", "rcd"]): return "breaker"
        if any(k in s for k in ["외함", "함체", "enclosure", "판넬"]): return "enclosure"
        if any(k in s for k in ["부속", "자재", "acc", "accessory", "accessories"]): return "accessory"
        if any(k in s for k in ["인건비", "labor"]): return "labor"
        return s

    # 시트별 파싱
    for sn in x.sheet_names:
        try:
            df = x.parse(sn)
        except Exception:
            continue
        df.columns = [str(c).strip().lower() for c in df.columns]
        if print_debug:
            print(f"[PRICEBOOK] cols[{sn}]={list(df.columns)}")  # 컬럼 헤더 확인용

        rows: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            d = {k: (None if (pd.isna(v) if pd is not None else v is None) else v) for k, v in r.items()}
            nr = _normalize_pricebook_row(d)
            if not any(nr.get(k) for k in ("name","model","spec","unit_price")):
                continue
            rows.append(nr)
        if not rows:
            continue

        raw_key = sn.strip().lower()
        can_key = _canon_sheet_name(sn)
        book[raw_key] = rows
        if can_key not in book:
            book[can_key] = rows

    if print_debug:
        sk = list(book.keys())
        print(f"[PRICEBOOK] sheets={sk[:8]} (+{max(0, len(sk)-8)} more)")
        # 표본 1행
        for k in sk:
            if book.get(k):
                smp = book[k][0]
                print(f"[PRICEBOOK] sample[{k}]: {{'name': {smp.get('name')}, 'model': {smp.get('model')}, 'spec': {smp.get('spec')}, 'unit_price': {smp.get('unit_price')} }}")
                break
    return book
# ===================== /PRICEBOOK v2.1 =====================

# ===================== PRICEBOOK ALIAS HOTFIX (for 한국어 헤더) =====================
# 단가표 시트 컬럼: ['브랜드','카테고리','시리즈/형식','모델명','재질/극수','규격/전류','차단용량(ka)','견적가']
# 아래 별칭은 load_pricebook() 내부에서 사용하는 _ALIAS를 덮어씁니다.

try:
    _ALIAS  # noqa: F821
except NameError:
    _ALIAS = {}

_ALIAS.update({
    "item_type": list(dict.fromkeys(
        (_ALIAS.get("item_type") or [])
        + ["카테고리","item_type","type","category","구분","종류","타입","품목군"]
    )),
    "name": list(dict.fromkeys(
        (_ALIAS.get("name") or [])
        + ["시리즈/형식","name","품명","품목","항목","item","description","desc","제품명","항목명","품목명","세부품명","품목내역","내역"]
    )),
    "model": list(dict.fromkeys(
        (_ALIAS.get("model") or [])
        + ["모델명","model","모델","형식","기종","type_no","catalog","cat","cat_no","모델no","형번","모델번호"]
    )),
    "spec": list(dict.fromkeys(
        (_ALIAS.get("spec") or [])
        + ["규격/전류","차단용량(ka)","spec","규격","사양","정격","스펙","정격전류","용량","size","규격(㎟)","규격(mm)","규격(원)"]
    )),
    "unit_price": list(dict.fromkeys(
        (_ALIAS.get("unit_price") or [])
        + ["견적가","unit_price","단가","가격","price","unit","unit price","unit_cost","원가","매입단가","단가(원)","공급가","공급단가","판매가","소비자가","금액","금액(원)","가격(원)","단가원"]
    )),
})

# name이 비어 있으면 브랜드/시리즈로 보간 (선택적 보강)
def _postprocess_pricebook_row_for_name(nr: dict) -> dict:
    if not nr.get("name"):
        brand = nr.get("브랜드") or nr.get("brand")
        series = nr.get("시리즈/형식") or nr.get("형식") or nr.get("series")
        if series and brand:
            nr["name"] = f"{brand} {series}"
        elif series:
            nr["name"] = str(series)
        elif brand:
            nr["name"] = str(brand)
    return nr

# load_pricebook() 결과 조립 단계에서 호출되도록 살짝 후킹
try:
    _normalize_pricebook_row  # noqa: F821
    _orig__normalize_pricebook_row = _normalize_pricebook_row
    def _normalize_pricebook_row(row):
        nr = _orig__normalize_pricebook_row(row)
        try:
            return _postprocess_pricebook_row_for_name(nr)
        except Exception:
            return nr
except NameError:
    pass
# ===================== /HOTFIX =====================

# ===================== PRICEBOOK v2.2 — header fallback + deep debug =====================
import re, os
from functools import lru_cache
from typing import List, Dict, Any, Optional

def _pb__as_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v)
        s = re.sub(r"[^\d.\-]", "", s)
        s = s.strip(".")
        return float(s) if s else None
    except Exception:
        return None

# 별칭 테이블 보강: '견적가','모델명','규격/전류' 등 한국어 헤더
try:
    _ALIAS  # noqa
except NameError:
    _ALIAS = {}
def _pb_merge_alias(key: str, extras: List[str]):
    cur = _ALIAS.get(key) or []
    # 순서 유지 + 중복 제거
    merged = list(dict.fromkeys(cur + extras))
    _ALIAS[key] = merged

_pb_merge_alias("item_type", ["카테고리","item_type","type","category","구분","종류","타입","품목군"])
_pb_merge_alias("name",      ["시리즈/형식","name","품명","품목","항목","item","description","desc","제품명","항목명","품목명","세부품명","품목내역","내역"])
_pb_merge_alias("model",     ["모델명","model","모델","형식","기종","type_no","catalog","cat","cat_no","모델no","형번","모델번호"])
_pb_merge_alias("spec",      ["규격/전류","차단용량(ka)","spec","규격","사양","정격","스펙","정격전류","용량","size","규격(㎟)","규격(mm)","규격(원)"])
_pb_merge_alias("unit_price",["견적가","unit_price","단가","가격","price","unit","unit price","unit_cost","원가","매입단가","단가(원)","공급가","공급단가","판매가","소비자가","금액","금액(원)","가격(원)","단가원"])

def _pb_pick(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = d[k]
            if isinstance(v, str) and not v.strip():
                continue
            return v
    return None

def _pb_normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    nr = dict(row)
    nr["item_type"] = _pb_pick(row, _ALIAS["item_type"])
    nr["name"]      = _pb_pick(row, _ALIAS["name"])
    nr["model"]     = _pb_pick(row, _ALIAS["model"])
    nr["spec"]      = _pb_pick(row, _ALIAS["spec"])
    nr["unit_price"]= _pb__as_float(_pb_pick(row, _ALIAS["unit_price"]))
    # name 보간
    if not nr.get("name"):
        brand  = row.get("브랜드") or row.get("brand")
        series = row.get("시리즈/형식") or row.get("형식") or row.get("series")
        if series and brand:
            nr["name"] = f"{brand} {series}"
        elif series:
            nr["name"] = str(series)
        elif brand:
            nr["name"] = str(brand)
    return nr

@lru_cache(maxsize=1)
def load_pricebook():  # 기존 함수를 덮어씀
    book: Dict[str, List[Dict[str, Any]]] = {}
    if pd is None:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pandas not available; cannot read Excel.")
        return book

    pb_path = _find_pricebook()
    if not pb_path:
        if os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1":
            print("[PRICEBOOK][WARN] pricebook not found.")
        return book

    print_debug = os.environ.get("KISAN_PRICEBOOK_DEBUG") == "1"
    if print_debug:
        print(f"[PRICEBOOK] path={pb_path}")

    try:
        x = pd.ExcelFile(pb_path)
    except Exception as e:
        if print_debug:
            print(f"[PRICEBOOK][ERR] open failed: {e}")
        return book

    def _canon(sn: str) -> str:
        s = (sn or "").strip().lower()
        if any(k in s for k in ["차단", "mccb", "breaker", "nfb", "elb", "rcd"]): return "breaker"
        if any(k in s for k in ["외함", "함체", "enclosure", "판넬"]): return "enclosure"
        if any(k in s for k in ["부속", "자재", "acc", "accessory", "accessories"]): return "accessory"
        if any(k in s for k in ["인건비", "labor"]): return "labor"
        return s

    for sn in x.sheet_names:
        df = None
        # 1) header=0 시도
        try:
            df = x.parse(sn, header=0)
            df.columns = [str(c).strip() for c in df.columns]
            if print_debug:
                print(f"[PRICEBOOK] cols[{sn}]=[{', '.join(map(str, df.columns))}]")
        except Exception:
            df = None

        # 2) 데이터가 전무하면 header=1 시도로 폴백
        if df is not None and df.dropna(how="all").shape[0] == 0:
            df = None
        if df is None:
            try:
                df = x.parse(sn, header=1)
                df.columns = [str(c).strip() for c in df.columns]
                if print_debug:
                    print(f"[PRICEBOOK] cols(fallback header=1)[{sn}]=[{', '.join(map(str, df.columns))}]")
            except Exception:
                df = None
        if df is None:
            continue

        # 소문자화는 한국어엔 영향없지만 키 일관성 위해 유지
        low_cols = [c.lower() for c in df.columns]
        df.columns = low_cols

        # 디버그: 상위 10행 모델/규격/견적가 그대로 보기
        if print_debug:
            cols_show = [c for c in df.columns if c in ("모델명","규격/전류","견적가","model","spec","unit_price")]
            try:
                print(f"[PRICEBOOK] peek[{sn}] top10 =>")
                print(df[cols_show].head(10).to_string(index=False))
            except Exception:
                pass

        rows: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            d = {}
            for k, v in r.items():
                if pd.isna(v):
                    d[k] = None
                else:
                    d[k] = v
            nr = _pb_normalize_row(d)
            # name/model/spec/unit_price 중 하나라도 있으면 수용 (너무 빡세게 걸러서 0행이 되는 케이스 방지)
            if any(nr.get(k) for k in ("name","model","spec","unit_price")):
                rows.append(nr)

        if print_debug:
            filled = sum(1 for r in rows if r.get("unit_price") not in (None, ""))
            print(f"[PRICEBOOK] mapped_rows[{sn}]={len(rows)} (unit_price_filled={filled})")

        if not rows:
            continue

        raw_key = sn.strip().lower()
        can_key = _canon(sn)
        book[raw_key] = rows
        if can_key not in book:
            book[can_key] = rows

    if print_debug:
        sk = list(book.keys())
        print(f"[PRICEBOOK] sheets={sk[:8]} (+{max(0, len(sk)-8)} more)")
        for k in sk:
            if book[k]:
                smp = book[k][0]
                print(f"[PRICEBOOK] sample[{k}]: {{'name': {smp.get('name')}, 'model': {smp.get('model')}, 'spec': {smp.get('spec')}, 'unit_price': {smp.get('unit_price')} }}")
                break
    return book
# ===================== /PRICEBOOK v2.2 =====================

# ===================== TEST v2: price matching & sum =====================
import os, json, glob, re
from typing import List, Dict, Any, Optional

def _proj_root_v2() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def _amp_key_v2(spec: Optional[str]) -> Optional[str]:
    if not spec:
        return None
    m = re.search(r"(\d+)\s*A", str(spec).replace(" ", "").upper())
    if not m:
        m = re.search(r"(\d+)\s*AMP", str(spec).replace(" ", "").upper())
    return (m.group(1) + "A") if m else None

def _price_match_v2(model: Optional[str], spec: Optional[str]) -> Optional[float]:
    """pricebook['breaker'] 기준으로 모델/스펙 매칭하여 단가 반환."""
    book = load_pricebook() or {}
    rows = book.get("breaker") or book.get("외함 및 차단기 모델명_단가") or []
    if not rows:
        return None

    model_s = (str(model).strip().upper() if model else "")
    spec_key = _amp_key_v2(spec)

    best = None
    # 1) 모델 완전일치 + 전류일치 우선
    for r in rows:
        r_model = str(r.get("model") or "").strip().upper()
        r_speck = _amp_key_v2(r.get("spec"))
        if model_s and r_model == model_s and (not spec_key or r_speck == spec_key):
            best = r
            break
    # 2) 모델 부분포함 + 전류일치
    if best is None and model_s:
        for r in rows:
            r_model = str(r.get("model") or "").strip().upper()
            r_speck = _amp_key_v2(r.get("spec"))
            if model_s in r_model and (not spec_key or r_speck == spec_key):
                best = r
                break
    # 3) 전류만 일치(모델 미지정인 경우)
    if best is None and spec_key:
        for r in rows:
            r_speck = _amp_key_v2(r.get("spec"))
            if r_speck == spec_key:
                best = r
                break

    return best.get("unit_price") if best else None

def _coalesce_v2(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

def _ensure_qty_v2(v) -> float:
    try:
        if v in (None, ""):
            return 1.0
        f = float(str(v).replace(",", ""))
        return f if f > 0 else 1.0
    except Exception:
        return 1.0

def _iter_lines_from_estimate_json_v2(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    # 허용 스키마:
    #  (a) {"lines":[{...}, ...]}
    #  (b) [{...}, ...]
    #  (c) {"sheet":...,"blocks":[{"lines":[...]}, ...]}
    if isinstance(j, dict):
        if isinstance(j.get("lines"), list):
            return j["lines"]
        if isinstance(j.get("blocks"), list) and j["blocks"] and isinstance(j["blocks"][0].get("lines"), list):
            acc = []
            for b in j["blocks"]:
                if isinstance(b.get("lines"), list):
                    acc.extend(b["lines"])
            return acc
        # multipanel mapper의 단순 레코드 배열이 다른 키로 들어온 경우
        for k in ("items", "records", "rows", "results"):
            if isinstance(j.get(k), list):
                return j[k]
        # 마지막 폴백: dict를 하나의 라인으로 해석
        return [j]
    elif isinstance(j, list):
        return j
    else:
        return []

def _pretty_name_v2(line: Dict[str, Any]) -> str:
    return str(_coalesce_v2(line, ["name","품명","항목","item","desc","description"], "")) or str(_coalesce_v2(line, ["model","모델","모델명","형식"], ""))

def run_test_v2_sum():
    root = _proj_root_v2()
    est_dir = os.path.join(root, "data", "estimates")
    patterns = [
        os.path.join(est_dir, "*.json"),
    ]
    # 제외 패턴(룰/스캔/번들 등)
    skip_names = {
        "accessories_v1.0.0.json",
        "breaker_rules_v1.00.json",
        "breaker_selection_guide_v1.00.json",
        "costing_rules_v1.0.0.json",
        "enclosure_rules_v1.00.json",
        "estimate_rag_bundle_v1.0.0.json",
    }

    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files.sort()

    for f in files:
        name = os.path.basename(f)
        if name in skip_names or name.startswith("multipanel_scan_"):
            print(f"[TESTv2] {name} :: skipped")
            continue
        lines = _iter_lines_from_estimate_json_v2(f)
        total = 0.0
        matched = 0
        for ln in lines:
            model = _coalesce_v2(ln, ["model","모델","모델명","형식"])
            spec  = _coalesce_v2(ln, ["spec","규격","규격/전류","정격","정격전류","용량"])
            qty   = _ensure_qty_v2(_coalesce_v2(ln, ["qty","수량","수량(개)","수량(SET)"], 1))
            up    = _price_match_v2(model, spec)
            if up is not None:
                matched += 1
                total += float(up) * qty
        print(f"[TESTv2] {name} :: lines={len(lines)} matched={matched} sum={int(total)}")

# 메인에서 v2 테스트 트리거 (기존 테스트와 공존)
if os.environ.get("KISAN_ESTIMATE_ENGINE_TEST") == "1":
    try:
        run_test_v2_sum()
    except Exception as e:
        print(f"[TESTv2][ERR] {e}")
# ===================== /TEST v2 =====================


# ----- 간단 테스트 (PowerShell: $env:KISAN_ESTIMATE_ENGINE_TEST='1') -----
if __name__ == "__main__" and os.environ.get("KISAN_ESTIMATE_ENGINE_TEST") == "1":
    root = _project_root()
    est_dir = os.path.join(root, "data", "estimates")
    files = sorted(glob.glob(os.path.join(est_dir, "*.json")))
    if not files:
        print("[TEST] no estimates found.")
    else:
        for f in files:
            try:
                lines = build_estimate_lines_with_prices(f)
            except Exception as e:
                print(f"[TEST][ERR] {os.path.basename(f)} :: {e}")
                continue
            if not lines:
                print(f"[TEST] {os.path.basename(f)} :: lines=0 (skipped)")
                continue
            s = sum((ln.get("amount") or 0.0) for ln in lines)
            print(f"[TEST] {os.path.basename(f)} :: lines={len(lines)} sum={int(s) if s else 0}")
# ============================ /END ============================

