# quickcheck_items.py
# 목적: N.T / N.P-3T*40*200 / N.P 카드홀더 / 코팅 / ELB 지지대 / 인슐레이터
#       → calc_other_materials_cost() 계산 로직 검증

from estimate_engine import map_amp_to_af, calc_other_materials_cost

def line():
    print("-" * 70)

def show_case(title, main_amp, style, branch_count,
              nt_qty, np_card_qty, np_card_unit_price,
              np_3t_qty, elb_support_models, main_count,
              include_coating=True):
    print(f"\n=== {title} ===")
    print(f"main_amp={main_amp}, style={style}, branch_count={branch_count}")
    main_af = map_amp_to_af(int(main_amp), style)

    total, breakdown = calc_other_materials_cost(
        main_af=main_af,
        branch_count=branch_count,
        nt_qty=nt_qty,
        np_card_qty=np_card_qty,
        np_card_unit_price=np_card_unit_price,  # None이면 0원 처리 + note
        np_3t_qty=np_3t_qty,
        elb_support_models=elb_support_models,
        main_count=main_count,
        include_coating=include_coating
    )

    print(f"기타 자재비 합계: {total}원")
    for k, v in breakdown.items():
        print(f"  - {k}: {v}")
    line()

def main():
    # CASE 1) 150A(경제형), 분기 12개
    #  - N.T 1EA, N.P 카드홀더 = 분기총수량(12)로 가정 (단가 미설정)
    #  - NP_3T 기본 1EA, ELB 지지대: 소형 일부, 메인 수량 1
    show_case(
        title="CASE 1: 150A / branch 12 / 기본코팅 포함",
        main_amp=150, style="경제형", branch_count=12,
        nt_qty=1,
        np_card_qty=12, np_card_unit_price=None,   # 단가 미설정 → 0원 + note
        np_3t_qty=1,
        elb_support_models={"SIE-32": 4, "SIB-32": 2, "32GRHS": 0, "BS32": 1},
        main_count=1,
        include_coating=True
    )

    # CASE 2) 400A(경제형), 분기 24개
    #  - 코팅 10,000원 구간, 메인 2대라고 가정 → 인슐레이터 증가 확인
    #  - N.P 카드홀더 단가를 예시로 800원/EA 가정(있으면 반영됨)
    show_case(
        title="CASE 2: 400A / branch 24 / 메인 2대 / 카드홀더 단가 800원",
        main_amp=400, style="경제형", branch_count=24,
        nt_qty=2,
        np_card_qty=24, np_card_unit_price=800,   # 예시 단가
        np_3t_qty=1,
        elb_support_models={"SIE-32": 1, "SIB-32": 1, "32GRHS": 2, "BS32": 0},
        main_count=2,
        include_coating=True
    )

if __name__ == "__main__":
    main()
