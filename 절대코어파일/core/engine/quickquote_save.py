# quickquote_save.py
# 목적: 콘솔 입력 → 총견적 JSON 생성 → 파일 저장
# 사용: py quickquote_save.py

import os, datetime
from estimate_engine import (
    build_quote_json, save_quote_json, parse_branch_summary
)

def ask(label, default=None):
    s = input(f"{label} [{default if default is not None else ''}]: ").strip()
    return s if s else (default if default is not None else "")

def ask_int(label, default=0):
    s = input(f"{label} [{default}]: ").strip()
    if s == "": return int(default)
    try:
        return int(s)
    except:
        print("숫자를 입력하세요. 기본값 사용:", default)
        return int(default)

def ask_yesno(label, default=True):
    d = "Y/n" if default else "y/N"
    s = input(f"{label} ({d}): ").strip().lower()
    if s == "": return default
    return s in ["y","yes","1","true","t"]

def main():
    print("\n=== 프로젝트/고객 정보 ===")
    project   = ask("프로젝트명", "샘플 프로젝트")
    customer  = ask("고객명", "홍길동 상사")
    requester = ask("요청자", "영업팀")
    notes     = ask("비고(선택)", "")

    print("\n=== 메인 차단기/스타일 ===")
    main_kind       = ask("메인 종류 (MCCB/ELB 등)", "MCCB")
    main_poles_text = ask("메인 극수 (2P/3P/4P)", "4P")
    main_amp_text   = ask("메인 정격 (예: 150A, 400A 등)", "150A")
    style           = ask("차단기 스타일 (경제형/표준형)", "경제형")

    print("\n=== 분기 요약 입력 ===")
    print("예) 'MCCB 4P 50A x 3, ELB 2P 20A x 4' 또는 '3P 30A * 2, 2P 20A 4개'")
    branch_summary  = ask("분기 요약(엔터=없음)", "")
    branches = parse_branch_summary(branch_summary)

    print("\n=== 계량기/부속 수량 ===")
    meter_count     = ask_int("계량기 개수", 1)
    meter_columns   = ask_int("계량기 하부 컬럼 수(2 또는 3, 1EA면 무시)", 2)
    magnet_count    = ask_int("마그네트 수량", 0)
    accessory_count = ask_int("부속자재 총수량(잡자재비 가산용)", 0)

    print("\n=== 기타 자재비 파라미터 ===")
    nt_qty          = ask_int("N.T 수량", 0)
    np_card_qty     = ask_int("N.P 카드홀더 수량(보통 분기총수량)", 0)
    np_card_unit    = ask("N.P 카드홀더 단가(엔터=미설정)", "")
    np_card_unit_price = int(np_card_unit) if np_card_unit.strip().isdigit() else None
    np_3t_qty       = ask_int("N.P / 3T*40*200 수량", 1)

    print("ELB 지지대 대상 모델 수량(없으면 0):")
    elb_SIE32  = ask_int(" - SIE-32", 0)
    elb_SIB32  = ask_int(" - SIB-32", 0)
    elb_32GRHS = ask_int(" - 32GRHS", 0)
    elb_BS32   = ask_int(" - BS32", 0)
    elb_support_models = {"SIE-32": elb_SIE32, "SIB-32": elb_SIB32, "32GRHS": elb_32GRHS, "BS32": elb_BS32}

    main_count      = ask_int("메인 차단기 대수(인슐레이터 계산용)", 1)
    include_coating = ask_yesno("코팅 포함할까요?", True)

    print("\n=== 부속여유(E) 비율 ===")
    E_ratio_raw     = ask("E 비율(예: 0.25, 엔터=정책기본)", "")
    E_ratio         = float(E_ratio_raw) if E_ratio_raw.strip() not in ["", None] else None

    # JSON payload 구성
    payload = build_quote_json(
        project=project, customer=customer, requester=requester, notes=notes,
        main_kind=main_kind, main_poles_text=main_poles_text, main_amp_text=main_amp_text,
        branches=branches, style=style,
        meter_count=meter_count, meter_columns=meter_columns, single_meter_side_ok=True, E_ratio=E_ratio,
        magnet_count=magnet_count, accessory_count=accessory_count,
        nt_qty=nt_qty, np_card_qty=np_card_qty, np_card_unit_price=np_card_unit_price, np_3t_qty=np_3t_qty,
        elb_support_models=elb_support_models, main_count=main_count, include_coating=include_coating,
        small_20a_majority=False
    )

    # 저장 경로
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(".", "quotes")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"quote_{ts}.json")

    saved = save_quote_json(out_path, payload)
    print("\n=== 저장 완료 ===")
    print("파일:", saved)

if __name__ == "__main__":
    main()
