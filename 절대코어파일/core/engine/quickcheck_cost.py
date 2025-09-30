# quickcheck_cost.py
# 목적: calc_consumables_cost()가 규칙대로 동작하는지 최소 확인
#       (필요시 compute_enclosure_size()와 연동해서 W/H를 받아 테스트)

from estimate_engine import calc_consumables_cost, compute_enclosure_size, get_last_explain

def show_cost(title, W, H, accessory_count):
    total, meta = calc_consumables_cost(W, H, accessory_count)
    print(f"\n=== {title} ===")
    print(f"W={W}, H={H}, accessory_count={accessory_count}")
    print(f"잡자재비 합계: {total}원")
    print("meta:", meta)

def main():
    # CASE 0) 기준 사이즈: 600x700, 부속 0개 → 7,000원
    show_cost("CASE 0: 기준 600x700, 부속 0", 600, 700, 0)

    # CASE 1) 이전 CASE 1과 동일: 계량기 1EA(사이드 스페이스) → W/H 변화 없음
    W1, H1, _ = compute_enclosure_size(
        main_kind="MCCB",
        main_poles_text="4P",
        main_amp_text="150A",
        branches=[],
        style="경제형",
        meter_count=1,
        single_meter_side_ok=True,
        E_ratio=None
    )
    print("\n[참고] ENC 결과 explain:", get_last_explain())
    # 예시: 마그네트 3개 → 부속 3개로 가정(시나리오 확인용)
    show_cost("CASE 1: ENC(계량기 1EA), 부속 3", W1, H1, accessory_count=3)

    # CASE 2) 이전 CASE 2와 동일: 계량기 2EA(하부 2컬럼) → W/H 증가
    W2, H2, _ = compute_enclosure_size(
        main_kind="MCCB",
        main_poles_text="4P",
        main_amp_text="150A",
        branches=[],
        style="경제형",
        meter_count=2,
        meter_columns=2,
        single_meter_side_ok=True,
        E_ratio=None
    )
    print("\n[참고] ENC 결과 explain:", get_last_explain())
    # 예시: 부속 6개로 가정(부속 많을 때 CAP(42,000) 확인 용도)
    show_cost("CASE 2: ENC(계량기 2EA), 부속 6", W2, H2, accessory_count=6)

if __name__ == "__main__":
    main()
