# quickquote_export.py
# 목적: quotes/ 폴더의 "가장 최근" quote_*.json 을 읽어
#       exports/ 폴더에 요약 CSV + 상세(비용 브레이크다운) CSV로 내보냄.
# 사용: py quickquote_export.py
#      (또는: py quickquote_export.py quotes\quote_20250826_001736.json)

import os, sys, glob, json, csv, datetime

def find_latest_quote(quotes_dir="quotes"):
    paths = sorted(glob.glob(os.path.join(quotes_dir, "quote_*.json")))
    return paths[-1] if paths else None

def load_payload(path=None):
    if path is None:
        path = find_latest_quote()
        if not path:
            raise FileNotFoundError("quotes\\quote_*.json 파일이 없습니다.")
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return path, payload

def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def export_summary_csv(payload, out_csv):
    meta = payload.get("meta", {})
    enc  = payload.get("enclosure", {})
    main = payload.get("main", {})
    costs= payload.get("costs", {})
    inp  = payload.get("inputs", {})

    fields = [
        ("project",            meta.get("project")),
        ("customer",           meta.get("customer")),
        ("requester",          meta.get("requester")),
        ("created_at",         meta.get("created_at")),
        ("notes",              meta.get("notes")),

        ("main_kind",          safe_get(inp, "main_kind") or safe_get(main, "kind")),
        ("main_poles_text",    safe_get(inp, "main_poles_text") or "4P"),
        ("main_amp",           safe_get(main, "amp")),
        ("main_af",            safe_get(main, "af")),
        ("style",              safe_get(main, "style") or safe_get(inp, "style")),
        ("branch_count",       safe_get(main, "branch_count")),

        ("W",                  enc.get("W")),
        ("H",                  enc.get("H")),
        ("D",                  enc.get("D")),
        ("H_formula",          enc.get("H_formula")),
        ("A_top",              safe_get(enc, "explain", "A_top")),
        ("B_gap",              safe_get(enc, "explain", "B_gap")),
        ("C_branch_total",     safe_get(enc, "explain", "C_branch_total")),
        ("D_bottom",           safe_get(enc, "explain", "D_bottom")),
        ("E_accessory",        safe_get(enc, "explain", "E_accessory")),

        ("meter_count",        safe_get(inp, "meter_count")),
        ("meter_columns",      safe_get(inp, "meter_columns")),
        ("single_meter_side_ok", safe_get(inp, "single_meter_side_ok")),
        ("E_ratio",            safe_get(inp, "E_ratio")),

        ("magnet_count",       safe_get(inp, "magnet_count")),
        ("accessory_count",    safe_get(inp, "accessory_count")),
        ("nt_qty",             safe_get(inp, "nt_qty")),
        ("np_card_qty",        safe_get(inp, "np_card_qty")),
        ("np_card_unit_price", safe_get(inp, "np_card_unit_price")),
        ("np_3t_qty",          safe_get(inp, "np_3t_qty")),
        ("main_count",         safe_get(inp, "main_count")),
        ("include_coating",    safe_get(inp, "include_coating")),

        ("labor_sum",          safe_get(costs, "labor_sum")),
        ("other_sum",          safe_get(costs, "other_sum")),
        ("consumables_sum",    safe_get(costs, "consumables_sum")),
        ("grand_total",        payload.get("grand_total")),
        ("currency",           payload.get("currency", "KRW")),
    ]

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "value"])
        for k, v in fields:
            w.writerow([k, v])

def export_breakdown_csv(payload, out_csv):
    """
    상세 비용 라인아이템 CSV:
      - assembly / ET / magnet_labor (labor_meta)
      - NT / NP_3T_40_200 / NP_CARD_HOLDER / COATING / ELB_SUPPORT / INSULATOR (other_meta)
      - Consumables 및 총합
    """
    costs = payload.get("costs", {})
    labor_meta = safe_get(costs, "breakdown", "labor_meta") or costs.get("labor_meta") or {}
    other_meta = safe_get(costs, "breakdown", "other_meta") or costs.get("other_meta") or {}
    cons_meta  = safe_get(costs, "breakdown", "consumables_meta") or costs.get("consumables_meta") or {}

    rows = []
    # Labor breakdown
    if isinstance(labor_meta, dict):
        rows.append(["assembly", safe_get(costs, "labor_sum"), labor_meta.get("assembly", {}).get("meta")])
        # 위 구조에 따라 키를 직접 나열
        asm  = labor_meta.get("assembly", {})
        et   = labor_meta.get("ET", {})
        mag  = labor_meta.get("magnet_labor", {})

        if asm:
            rows.append(["assembly.detail", asm.get("cost"), asm.get("meta")])
        if et:
            rows.append(["ET", et.get("cost"), et.get("meta")])
        if mag:
            rows.append(["magnet_labor", mag.get("cost"), mag.get("meta")])

    # Other materials breakdown
    if isinstance(other_meta, dict):
        for key in ["NT","NP_3T_40_200","NP_CARD_HOLDER","COATING","ELB_SUPPORT","INSULATOR"]:
            item = other_meta.get(key)
            if item:
                rows.append([key, item.get("cost"), item.get("meta")])
        ctx = other_meta.get("context")
        if ctx:
            rows.append(["context", "", ctx])

    # Consumables
    rows.append(["consumables", safe_get(costs, "consumables_sum"), cons_meta])

    # Totals
    rows.append(["TOTALS.labor_sum",  safe_get(costs, "labor_sum"),  ""])
    rows.append(["TOTALS.other_sum",  safe_get(costs, "other_sum"),  ""])
    rows.append(["TOTALS.consumables_sum", safe_get(costs, "consumables_sum"), ""])
    rows.append(["GRAND_TOTAL",       payload.get("grand_total"),    payload.get("currency", "KRW")])

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "amount", "meta"])
        for r in rows:
            # meta를 문자열로
            r2 = r[:2] + [json.dumps(r[2], ensure_ascii=False) if isinstance(r[2], dict) else (r[2] or "")]
            w.writerow(r2)

def main():
    # 인자: 특정 파일 지정 가능
    in_path = sys.argv[1] if len(sys.argv) > 1 else None
    path, payload = load_payload(in_path)

    # 파일명 베이스
    base = os.path.splitext(os.path.basename(path))[0]  # quote_YYYYMMDD_HHMMSS
    out_dir = os.path.join(".", "exports")
    os.makedirs(out_dir, exist_ok=True)
    summary_csv   = os.path.join(out_dir, f"{base}_summary.csv")
    breakdown_csv = os.path.join(out_dir, f"{base}_breakdown.csv")

    export_summary_csv(payload, summary_csv)
    export_breakdown_csv(payload, breakdown_csv)

    print("=== Export 완료 ===")
    print("입력 JSON :", os.path.abspath(path))
    print("요약 CSV  :", os.path.abspath(summary_csv))
    print("상세 CSV  :", os.path.abspath(breakdown_csv))

if __name__ == "__main__":
    main()
