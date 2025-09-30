# kisan_mapping_v2.py
# 한국산업 견적서 맵핑 V2 — multipanel_scan_*.json → /data/estimates/*.json
from __future__ import annotations
import os, io, re, json, uuid, datetime as dt
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

ESTIMATES_DIR = os.path.join("data", "estimates")
SUBTOTAL_TOKENS = ("소계", "합계")

def _is_blank_row(row: Dict[str, Any]) -> bool:
    if not row: return True
    for v in row.values():
        if v is None: 
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        return False
    return True

@dataclass
class MappedLine:
    source_row_idx: int
    raw: Dict[str, Any]
    item_type: str
    model: Optional[str] = None
    spec: Dict[str, Any] = field(default_factory=dict)
    qty: float = 1.0
    unit: Optional[str] = None
    note: Optional[str] = None

@dataclass
class PanelEstimate:
    file_id: str
    sheet_index: int
    sheet_name: str
    panel_name: str
    block_index: int
    lines: List[MappedLine] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "sheet_index": self.sheet_index,
            "sheet_name": self.sheet_name,
            "panel_name": self.panel_name,
            "block_index": self.block_index,
            "lines": [
                {
                    "source_row_idx": ln.source_row_idx,
                    "item_type": ln.item_type,
                    "model": ln.model,
                    "spec": ln.spec,
                    "qty": ln.qty,
                    "unit": ln.unit,
                    "note": ln.note,
                    "raw": ln.raw,
                } for ln in self.lines
            ],
            "meta": self.meta,
        }

def _safe_float(x: Any, default: float = 1.0) -> float:
    if x is None: return default
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        try: return float(s)
        except: return default
    return default

def _norm_text(x: Any) -> str:
    if x is None: return ""
    return str(x).strip()

def _contains_any(s: str, tokens) -> bool:
    return any((t and (t in s)) for t in tokens)

# 컬럼 후보
CAND_ITEM = ("품목", "품명", "항목", "Item", "내역", "name", "품목명", "K1", "line", "text")
CAND_SPEC = ("규격", "사양", "Spec", "스펙", "description", "desc", "규격/사양", "K2")
CAND_QTY  = ("수량", "Qty", "QTY", "ea", "EA", "수 량", "수량(EA)")
CAND_UNIT = ("단위", "Unit")
CAND_NOTE = ("비고", "메모", "Remark", "Notes", "remark", "비 고", "K3")

# 타입 추정 키워드
BREAKER_TOKENS  = ("ELB", "MCCB", "NFB", "ELCB", "MCB", "EOCR", "RCD", "누전")
ENCLOSURE_TOKENS= ("외함", "함체", "분전반함", "배전함", "판넬", "Enclosure")
ACCESSORY_TOKENS= ("터미널", "단자대", "퓨즈홀더", "덕트", "레일", "컨넥터", "라벨", "케이블그랜드", "케이블 글랜드", "스페이서", "후레임")
LABOR_TOKENS    = ("인건비", "조립", "배선", "세척", "출하검사", "시운전")

def guess_item_type(name: str) -> str:
    s = _norm_text(name).upper()
    if _contains_any(s, BREAKER_TOKENS):   return "breaker"
    if _contains_any(s, ENCLOSURE_TOKENS): return "enclosure"
    if _contains_any(s, ACCESSORY_TOKENS): return "accessory"
    if _contains_any(s, LABOR_TOKENS):     return "labor"
    return "misc"

def _pick_first(row: Dict[str, Any], candidates) -> Optional[Any]:
    # 1) 정확 일치
    for k in row.keys():
        for c in candidates:
            if str(k).strip().lower() == str(c).strip().lower():
                return row.get(k)
    # 2) 느슨 포함
    low_keys = {str(k).lower(): k for k in row.keys()}
    for c in candidates:
        for lk, orig in low_keys.items():
            if c.lower() in lk:
                return row.get(orig)
    return None

def _likely_unit(val: str) -> bool:
    s = _norm_text(val)
    if not s: return False
    CAND = ("EA","개","SET","세트","M","MM","EA.","PCS","Pcs","pc","PC")
    return any(s.upper()==c.upper() for c in CAND)

def _positional_guess(row_vals: List[Any]) -> Dict[str, Any]:
    """헤더가 없을 때 [이름,규격,수량,단위,비고] 대략 추정 (리스트/임의 dict 순서 보호)"""
    vals = [("" if v is None else v) for v in row_vals]
    name = vals[0] if len(vals)>0 else ""
    spec = vals[1] if len(vals)>1 else ""
    qty  = None
    unit = None
    note = None
    for v in vals[2:]:
        if isinstance(v, (int,float)) or (isinstance(v,str) and re.fullmatch(r"\s*\d+(\.\d+)?\s*", v or "")):
            qty = v; break
    for v in vals[2:]:
        if isinstance(v,str) and _likely_unit(v):
            unit = v; break
    for v in reversed(vals):
        if isinstance(v,str) and v and v != name and v != spec:
            note = v; break
    return {"name":name,"spec":spec,"qty":qty,"unit":unit,"note":note}

def _first_nonempty_text(d: Dict[str, Any]) -> Optional[str]:
    for v in d.values():
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _concat_text(d: Dict[str, Any]) -> str:
    parts = []
    for v in d.values():
        if v is None: 
            continue
        if isinstance(v, (int, float)):
            parts.append(str(v))
        elif isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return " ".join(parts).strip()

def _infer_qty_from_text(s: str) -> Optional[float]:
    # 텍스트 끝부분에서 12EA / x3 / 3개 / 3.5 등 숫자 추정
    if not s: return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(EA|개|SET|세트)?\s*$', s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except:
            return None
    return None

def map_row_to_line(row: Dict[str, Any], row_idx: int) -> Optional[MappedLine]:
    # 0) 값이 전부 비었으면 스킵
    if _is_blank_row(row):
        return None

    # 1) 후보 키에서 먼저 시도
    name = _pick_first(row, CAND_ITEM)
    spec_raw = _pick_first(row, CAND_SPEC)
    qty_raw  = _pick_first(row, CAND_QTY)
    unit_raw = _pick_first(row, CAND_UNIT)
    note_raw = _pick_first(row, CAND_NOTE)

    # 2) 포지셔널 추정 (키 후보가 하나도 안맞을 때)
    if name is None and all(not _pick_first(row, cands) for cands in (CAND_SPEC,CAND_QTY,CAND_UNIT,CAND_NOTE)):
        ordered_vals = list(row.values())
        pos = _positional_guess(ordered_vals)
        name = pos["name"]; spec_raw = pos["spec"]; qty_raw = pos["qty"]; unit_raw = pos["unit"]; note_raw = pos["note"]

    # 3) 그래도 name이 비면: 첫 비어있지 않은 텍스트 사용
    if (not name) or (isinstance(name,str) and name.strip()==""):
        n1 = _first_nonempty_text(row)
        if n1:
            name = n1

    # 4) 여전히 없으면: 전체 텍스트 합쳐서 첫 토큰을 name으로
    if (not name) or (isinstance(name,str) and name.strip()==""):
        alltxt = _concat_text(row)
        if "\t" in alltxt:
            name = alltxt.split("\t")[0].strip()
        elif "," in alltxt:
            name = alltxt.split(",")[0].strip()
        else:
            name = alltxt.strip()

    # name 최종 확인
    if not name or (isinstance(name,str) and name.strip()==""):
        return None

    # qty 보정: 텍스트에서 추정
    if qty_raw is None:
        q_guess = _infer_qty_from_text(_concat_text(row))
        if q_guess is not None:
            qty_raw = q_guess

    item_type = guess_item_type(str(name))
    qty = _safe_float(qty_raw, 1.0)
    unit = _norm_text(unit_raw) or None

    model = None
    m = re.search(r"([A-Z]{2,}[A-Z0-9\-_/]{1,})", str(name).upper())
    if m:
        model = m.group(1)

    spec = {}
    if spec_raw:
        spec["text"] = _norm_text(spec_raw)
    note = _norm_text(note_raw) or None

    return MappedLine(
        source_row_idx=row_idx,
        raw=row,
        item_type=item_type,
        model=model,
        spec=spec,
        qty=qty,
        unit=unit,
        note=note
    )

def pick_sheets(sheet_count: int) -> List[int]:
    # 정책: 탭 2개면 0,1 / 3개 이상이면 0,2 (1=고압반 무시)
    if sheet_count <= 0: return []
    if sheet_count == 1: return [0]
    if sheet_count == 2: return [0, 1]
    return [i for i in (0, 2) if i < sheet_count]

def split_blocks(rows: List[Dict[str, Any]], row_start_idx: int = 0) -> List[Tuple[int, int]]:
    blocks: List[Tuple[int, int]] = []
    start = row_start_idx
    i = row_start_idx
    N = len(rows)
    end = None
    def row_has_subtotal_marker(r: Dict[str, Any]) -> bool:
        text_cells = [str(v) for v in r.values() if isinstance(v, (str, int, float))]
        joined = " ".join(map(str, text_cells))
        return _contains_any(joined, SUBTOTAL_TOKENS)
    while i < N:
        r = rows[i]
        if row_has_subtotal_marker(r):
            end = i
            if start <= end:
                blocks.append((start, end))
            j = i + 1
            blank_pass = 0
            while j < N and blank_pass < 3:
                if _is_blank_row(rows[j]):
                    blank_pass += 1
                    j += 1
                else:
                    break
            start = j
            i = j
            end = None
        else:
            i += 1
    if end is None and start < N:
        blocks.append((start, N - 1))
    return blocks

# -------- 재귀 탐색으로 행 후보 찾기 --------
def _as_row_dicts(seq: List[Any]) -> Optional[List[Dict[str, Any]]]:
    """시퀀스를 '행(dict) 리스트'로 정규화. dict리스트면 그대로, list리스트면 K1.. 키로 변환, 문자열이면 {"K1":str}"""
    if not isinstance(seq, list) or not seq:
        return None
    if all(isinstance(r, dict) for r in seq):
        return seq
    if all(isinstance(r, list) for r in seq):
        norm = []
        for r in seq:
            d = {f"K{i+1}": v for i, v in enumerate(r)}
            norm.append(d)
        return norm
    if all(isinstance(r, str) for r in seq):
        return [ {"K1": r} for r in seq ]
    return None

def _iter_row_candidates(node: Any, path: str = "$") -> List[Tuple[str, List[Dict[str, Any]]]]:
    """dict/list 내부를 재귀 탐색하며 '행 리스트 후보'를 모두 수집 (경로, 정규화된 rows)"""
    cands: List[Tuple[str, List[Dict[str, Any]]]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            if isinstance(v, list):
                rows = _as_row_dicts(v)
                if rows:
                    cands.append((p, rows))
                for i, it in enumerate(v):
                    cands.extend(_iter_row_candidates(it, f"{p}[{i}]"))
            else:
                cands.extend(_iter_row_candidates(v, p))
    elif isinstance(node, list):
        for i, it in enumerate(node):
            cands.extend(_iter_row_candidates(it, f"{path}[{i}]"))
    return cands

def _best_rows_anywhere(node: Any) -> Tuple[str, List[Dict[str, Any]]]:
    cands = _iter_row_candidates(node, "$")
    if not cands:
        return "$", []
    cands.sort(key=lambda x: len(x[1]), reverse=True)
    return cands[0]

def _best_rows_from_sheet_anywhere(sh: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    sheet_name = sh.get("name") or sh.get("sheet_name") or sh.get("title") or "Sheet"
    path, rows = _best_rows_anywhere(sh)
    if path == "$":
        return sheet_name, rows
    return f"{sheet_name}::{path}", rows

# -------- 응급 파서 (강화) --------
def _explode_single_container_to_rows(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    best_path, best_rows = _best_rows_anywhere(container)
    if best_rows:
        return best_rows
    rows: List[Dict[str, Any]] = []
    for k, v in container.items():
        if isinstance(v, list) and v:
            sub = _as_row_dicts(v)
            if sub:
                rows.extend(sub)
    if rows:
        return rows
    for k, v in container.items():
        if isinstance(v, str):
            sv = v.strip()
            if (sv.startswith("{") and sv.endswith("}")) or (sv.startswith("[") and sv.endswith("]")):
                try:
                    parsed = json.loads(sv)
                    bp, br = _best_rows_anywhere(parsed)
                    if br:
                        return br
                except Exception:
                    pass
            lines = [ln for ln in re.split(r"\r?\n+", sv) if ln.strip()]
            if len(lines) >= 2:
                sep = "\t" if any("\t" in ln for ln in lines) else ","
                def split_line(ln: str) -> List[str]:
                    return [p.strip() for p in ln.split(sep)]
                head = split_line(lines[0])
                body = [split_line(ln) for ln in lines[1:]]
                for r in body:
                    d = { (head[i] if i < len(head) else f"K{i+1}") : (r[i] if i < len(r) else "") for i in range(max(len(head), len(r))) }
                    rows.append(d)
                if rows:
                    return rows
    if container:
        rows.append({k: v for k, v in container.items()})
    return rows

class MappingV2:
    def __init__(self, debug: bool = False):
        os.makedirs(ESTIMATES_DIR, exist_ok=True)
        self.debug = debug

    def _normalize_scan_root(self, scan_root: Any) -> tuple[str, List[Dict[str, Any]]]:
        if isinstance(scan_root, dict):
            file_id = scan_root.get("file_id") or str(uuid.uuid4())
            sheets = scan_root.get("sheets") or []
            if not sheets and "workbook" in scan_root:
                wb = scan_root.get("workbook") or {}
                sheets = wb.get("sheets") or []
            if not isinstance(sheets, list):
                sheets = []
            return file_id, sheets
        if isinstance(scan_root, list):
            return str(uuid.uuid4()), scan_root
        raise ValueError("지원하지 않는 스캔 JSON 포맷입니다. (dict 또는 list 필요)")

    def _dump_candidates(self, scan_root: Any):
        cands = _iter_row_candidates(scan_root, "$")
        cands.sort(key=lambda x: len(x[1]), reverse=True)
        print(f"[CANDIDATES] total={len(cands)}")
        for path, rows in cands[:50]:
            print(f" - {path} : rows={len(rows)}")

    def convert_scan_to_estimates(self, scan_json_path: str) -> List[str]:
        with io.open(scan_json_path, "r", encoding="utf-8") as f:
            scan = json.load(f)

        file_id, sheets = self._normalize_scan_root(scan)
        sheet_count = len(sheets)
        targets = pick_sheets(sheet_count)

        out_paths: List[str] = []
        now = dt.datetime.now().strftime("%Y%m%d-%H%M%S")

        if self.debug:
            print(f"[DEBUG] file_id={file_id} sheet_count={sheet_count} targets={targets}")

        for si in targets:
            if si >= len(sheets): 
                if self.debug: print(f"[DEBUG] skip sheet index {si} (out of range)")
                continue
            sh = sheets[si] or {}

            sheet_name, norm_rows = _best_rows_from_sheet_anywhere(sh)
            if self.debug:
                print(f"[DEBUG] Sheet#{si} '{sheet_name}': rows={len(norm_rows)}")

            if len(norm_rows) <= 1 and isinstance(sh, dict) and "results" in sh and isinstance(sh["results"], list) and len(sh["results"]) == 1 and isinstance(sh["results"][0], dict):
                best_path, best_rows = _best_rows_anywhere(sh["results"][0])
                if self.debug:
                    print(f"[DEBUG]  -> emergency deep-scan {best_path} rows={len(best_rows)} from $.results[0]")
                if best_rows:
                    norm_rows = best_rows
                    sheet_name = sheet_name.split("::")[0] + f"::{best_path}(deep)"

            blocks = split_blocks(norm_rows, 0)
            if self.debug:
                print(f"[DEBUG]  -> blocks detected: {len(blocks)} {blocks}")

            mapped_any_block = False
            iterable_blocks = blocks if blocks else ([(0, len(norm_rows)-1)] if norm_rows else [])

            for bi, (s_idx, e_idx) in enumerate(iterable_blocks):
                block_rows = norm_rows[s_idx:e_idx+1] if norm_rows else []
                panel_name = self._guess_panel_name(block_rows, sheet_name.split("::")[0], bi)

                panel = PanelEstimate(
                    file_id=file_id,
                    sheet_index=si,
                    sheet_name=sheet_name.split("::")[0],
                    panel_name=panel_name,
                    block_index=bi,
                    lines=[],
                    meta={"generated_at": now, "source_path": sheet_name.split("::")[1] if "::" in sheet_name else None}
                )

                mapped_count = 0
                for local_i, r in enumerate(block_rows):
                    row_idx = s_idx + local_i
                    ln = map_row_to_line(r, row_idx)
                    if ln:
                        panel.lines.append(ln)
                        mapped_count += 1

                if self.debug:
                    print(f"[DEBUG]   Block#{bi} rows={len(block_rows)} mapped_lines={mapped_count}")

                if not panel.lines:
                    continue

                mapped_any_block = True
                out = panel.to_dict()
                out_name = f"{now}_{file_id}_S{si}_B{bi}_{self._safe_slug(panel_name)}.json"
                out_path = os.path.join(ESTIMATES_DIR, out_name)
                with io.open(out_path, "w", encoding="utf-8") as wf:
                    json.dump(out, wf, ensure_ascii=False, indent=2)
                out_paths.append(out_path)

            if self.debug and not mapped_any_block:
                print(f"[DEBUG][WARN] Sheet#{si} '{sheet_name}' had no mappable lines. "
                      f"헤더/열구조가 비표준일 수 있음. 포맷 확인 필요.")

        return out_paths

    def _guess_panel_name(self, block_rows: List[Dict[str, Any]], sheet_name: str, block_index: int) -> str:
        NAME_HINT = ("분전반", "배전반", "판넬", "판넬명", "반명", "Panel", "MCC", "SUB", "MDB", "LP", "LP-")
        scan_range = block_rows[:min(5, len(block_rows))]
        best = None
        for r in scan_range:
            texts = [str(v) for v in r.values() if isinstance(v, (str, int, float))]
            for t in texts:
                s = str(t)
                if _contains_any(s, NAME_HINT):
                    best = s.strip()
                    break
            if best: break
        if best:
            return best
        return f"{sheet_name}-B{block_index+1}"

    def _safe_slug(self, name: str) -> str:
        s = re.sub(r"[\s/\\:;|]+", "_", name.strip())
        s = re.sub(r"[^0-9A-Za-z가-힣_\-]+", "", s)
        return s[:40] if len(s) > 40 else s

def main():
    import argparse
    ap = argparse.ArgumentParser(description="KISAN mapping v2 — scan JSON → estimates JSON")
    ap.add_argument("scan_json", help="multipanel_scan_*.json 경로")
    ap.add_argument("--debug", action="store_true", help="진단 로그 출력")
    ap.add_argument("--dump-candidates", action="store_true", help="후보 경로/행수 덤프")
    args = ap.parse_args()

    if args.dump_candidates:
        with io.open(args.scan_json, "r", encoding="utf-8") as f:
            scan = json.load(f)
        mapper = MappingV2(debug=True)
        mapper._dump_candidates(scan)
        return

    mapper = MappingV2(debug=args.debug)
    out_paths = mapper.convert_scan_to_estimates(args.scan_json)
    print("[kisan_mapping_v2] generated:")
    for p in out_paths:
        print(" -", p)

if __name__ == "__main__":
    main()
