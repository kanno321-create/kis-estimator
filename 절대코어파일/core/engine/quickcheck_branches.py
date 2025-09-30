# quickcheck_branches.py
# 목적: parse_branch_summary()로 요약 문자열을 branches로 만들고, 외함 H에 반영되는지 확인

from estimate_engine import parse_branch_summary, compute_enclosure_size, get_last_explain
from tests_util import normalize_explain, pick

def check(text, title):
    branches = parse_branch_summary(text)
    W, H, Dp = compute_enclosure_size(
        main_kind="MCCB", main_poles_text="4P", main_amp_text="150A",
        branches=branches, style="경제형",
        meter_count=1, single_meter_side_ok=True
    )
    print(f"\n=== {title} ===")
    print("입력 요약:", text)
    print("branches:", branches)
    print("W=..., H=..., D=...", ...)
    exp = normalize_explain(get_last_explain())
    print("explain:", pick(exp, ["A_top","B_gap","C_branch_total","D_bottom","E_accessory","policy"]))

def main():
    check("MCCB 4P 50A x 3, ELB 2P 20A x 4", "CASE 1: 명시 종류 포함")
    check("3P 30A * 2, 2P 20A 4개", "CASE 2: 종류 생략 → 기본 MCCB")
    check("ELB 4P 50A 3EA\n2P 20A 6", "CASE 3: 줄바꿈/혼합 표기")

if __name__ == "__main__":
    main()
