# quickcheck_grand.py
# 목적: calc_grand_total() 하나로 총 견적(인건비+기타자재+잡자재비) 스모크 테스트

from pprint import pprint
from estimate_engine import calc_grand_total
from estimate_engine import compute_enclosure_size, get_last_explain  # 외함 계산/트레이스 접근 (정식 경로)
from tests_util import normalize_explain, pick                         # explain 정규화 유틸 (테스트 전용)
import json

def line():
    print("-" * 80)

def run_case(
    title: str,
    *,
    main_amp_text: str,
    branches: list,
    meter_count: int,
    meter_columns: int | None,
    magnet_count: int,
    accessory_count: int,
    nt_qty: int,
    np_card_qty: int,
    np_card_unit_price: int | None,
    np_3t_qty: int,
    elb_support_models: dict | None,
    main_count: int,
    include_coating: bool = True,
    style: str = "경제형",
    main_kind: str = "MCCB",
    main_poles_text: str = "4P",
    E_ratio: float | None = None,
):
    print(f"\n=== {title} ===")
    grand, details = calc_grand_total(
        main_kind=main_kind,
        main_poles_text=main_poles_text,
        main_amp_text=main_amp_text,
        branches=branches,
        style=style,
        meter_count=meter_count,
        meter_columns=meter_columns,
        single_meter_side_ok=True,
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
        small_20a_majority=False
    )

    enc = compute_enclosure_size(...)
    costs = details["costs"]
    print(f"외함: W={enc['W']}, H={enc['H']}, D={enc['D']}")
    exp = normalize_explain(enc.get("explain"))
    print("explain:", pick(exp, ["A_top","B_gap","C_branch_total","D_bottom","E_accessory","policy"]))
    print(f"인건비 합계: {costs['labor_sum']}원")
    print(f"기타 자재비 합계: {costs['other_sum']}원")
    print(f"잡자재비: {costs['consumables_sum']}원")
    print(f"총견적(예시): {grand}원")
    line()
    # 필요 시 상세 확인
    # pprint(details)

def main():
    # CASE 1) 150A, 계량기 1EA(사이드), 마그네트 3EA, 부속 3EA
    run_case(
        "CASE 1: 150A / meter=1(side) / magnet=3 / accessories=3",
        main_amp_text="150A",
        branches=[],                     # 간단 스모크: 빈 분기
        meter_count=1,
        meter_columns=None,              # 사이드 스페이스 처리라 무시됨
        magnet_count=3,
        accessory_count=3,
        nt_qty=1,
        np_card_qty=12,                  # 예: 분기 12개라 가정
        np_card_unit_price=None,         # 미설정 → 0원 + note
        np_3t_qty=1,
        elb_support_models={"SIE-32":4, "SIB-32":2, "32GRHS":0, "BS32":1},
        main_count=1,
        include_coating=True
    )

    # CASE 2) 400A, 계량기 2EA(하부 2컬럼), 마그네트 6EA, 부속 6EA
    run_case(
        "CASE 2: 400A / meter=2(bottom-2col) / magnet=6 / accessories=6",
        main_amp_text="400A",
        branches=[],                     # 간단 스모크
        meter_count=2,
        meter_columns=2,
        magnet_count=6,
        accessory_count=6,
        nt_qty=2,
        np_card_qty=24,
        np_card_unit_price=800,          # 예시 단가
        np_3t_qty=1,
        elb_support_models={"SIE-32":1, "SIB-32":1, "32GRHS":2, "BS32":0},
        main_count=2,
        include_coating=True
    )

if __name__ == "__main__":
    main()
