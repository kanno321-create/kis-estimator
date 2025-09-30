# quickcheck_compute.py
# 목적: compute_enclosure_size() 가 새 H공식과 계량기 하부취부 규칙대로 동작하는지 최소 확인

from estimate_engine import compute_enclosure_size, get_last_explain

def show(title, result):
    W, H, Dp = result
    print(f"\n=== {title} ===")
    print(f"W={W}, H={H}, D={Dp}")
    print("explain:", get_last_explain())

def main():
    # 공통 입력(샘플): 메인 4P 150A, 분기 없음(빈 리스트)
    main_kind = "MCCB"         # 예시
    main_poles_text = "4P"
    main_amp_text = "150A"
    branches = []              # 지금은 빈 분기로 최소 동작만 확인

    # CASE 1) 계량기 1EA: 좌/우 여유로 처리 → W/H 변화 없음
    res1 = compute_enclosure_size(
        main_kind, main_poles_text, main_amp_text, branches,
        style="경제형",
        meter_count=1,              # 1EA
        single_meter_side_ok=True,  # 좌/우 여유 활용 허용
        E_ratio=None                # 정책 기본(25%) 사용
    )
    show("CASE 1: meter=1EA (side space, no change)", res1)

    # CASE 2) 계량기 2EA: 하부 취부 → W는 columns*130, H는 rows*200 증가
    res2 = compute_enclosure_size(
        main_kind, main_poles_text, main_amp_text, branches,
        style="경제형",
        meter_count=2,              # 2EA 이상 → 하부 슬롯 방식
        meter_columns=2,            # 기본 2칸(=W + 260mm)
        single_meter_side_ok=True,  # 2EA라 하부 처리로 계산
        E_ratio=None
    )
    show("CASE 2: meter=2EA (bottom mount, 2 columns)", res2)

if __name__ == "__main__":
    main()
