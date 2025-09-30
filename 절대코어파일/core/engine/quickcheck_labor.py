# quickcheck_labor.py
# 목적: 조립 인건비(티어+H증가), E.T, 마그네트 인건비, 잡자재비를 간단 시나리오로 점검

from estimate_engine import (
    compute_enclosure_size, get_last_explain, map_amp_to_af,
    calc_labor_and_misc, calc_consumables_cost
)
from tests_util import normalize_explain, pick

def line():
    print("-" * 70)

def show_all(title, main_amp_text, branches, meter_count, meter_columns, magnet_count, accessory_count):
    print(f"\n=== {title} ===")
    main_kind = "MCCB"
    main_poles_text = "4P"
    style = "경제형"

    # 1) 외함 산출 (W,H,D)
    W, H, Dp = compute_enclosure_size(
        main_kind=main_kind,
        main_poles_text=main_poles_text,
        main_amp_text=main_amp_text,
        branches=branches,
        style=style,
        meter_count=meter_count,
        meter_columns=meter_columns,
        single_meter_side_ok=True,
        E_ratio=None
    )
    exp = normalize_explain(get_last_explain())
    print(f"W={W}, H={H}, D={Dp}")
    print("explain(policy/H parts):", pick(exp, ["policy","A_top","B_gap","C_branch_total","D_bottom","E_accessory","H_final"]))

    # 2) 메인 AF 도출 (인건비 계산용)
    main_amp_val = int(main_amp_text.replace("A",""))
    main_af = map_amp_to_af(main_amp_val, style)
    branch_count = len(branches)

    # 3) 인건비(조립+ET+마그네트)
    labor_sum, labor_meta = calc_labor_and_misc(
        main_af=main_af,
        H=H,
        branch_count=branch_count,
        magnet_count=magnet_count,
        small_20a_majority=False  # 필요시 True로 바꿔 테스트
    )
    print(f"인건비 합계(조립+ET+마그네트): {labor_sum}원")
    print("  - breakdown:", labor_meta)

    # 4) 잡자재비
    consumables, c_meta = calc_consumables_cost(W, H, accessory_count=accessory_count)
    print(f"잡자재비: {consumables}원")
    print("  - meta:", c_meta)

    # 5) 총합(참고)
    total_example = labor_sum + consumables
    print(f"예시 총합(인건비+잡자재비): {total_example}원")
    line()

def main():
    # CASE 1) 계량기 1EA(사이드 스페이스), 마그네트 3EA, 부속 3EA
    show_all(
        title="CASE 1: meter=1EA(side), magnet=3, accessories=3",
        main_amp_text="150A",
        branches=[],              # 간단 테스트라 빈 분기
        meter_count=1,
        meter_columns=None,       # 기본 정책(2칸) 안 쓰임(1EA는 사이드스페이스)
        magnet_count=3,
        accessory_count=3
    )

    # CASE 2) 계량기 2EA(하부 2컬럼), 마그네트 6EA, 부속 6EA
    show_all(
        title="CASE 2: meter=2EA(bottom, 2col), magnet=6, accessories=6",
        main_amp_text="150A",
        branches=[],
        meter_count=2,
        meter_columns=2,
        magnet_count=6,
        accessory_count=6
    )

if __name__ == "__main__":
    main()
